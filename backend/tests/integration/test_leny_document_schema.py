"""Document-library DDL/invariants; requires the fail-closed isolated launcher.

Every DDL/DML change is enclosed in a rollback-only migration-role transaction.
No settings, URLs, engines or production defaults are loaded by this module.
"""
from contextlib import contextmanager
import importlib.util
from pathlib import Path
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


def _migration(filename="20261019_0019_leny_documents.py"):
    path = Path(__file__).resolve().parents[2] / "alembic/versions" / filename
    spec = importlib.util.spec_from_file_location("leny_document_migration_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def _library(pg_cluster):
    with pg_cluster.migration_engine.connect() as connection:
        transaction = connection.begin()
        try:
            pg_cluster.assert_identity(connection, pg_cluster.manifest, migrator=True)
            if connection.execute(text("SELECT to_regclass('leny.carpetas')")).scalar_one() is None:
                with Operations.context(MigrationContext.configure(connection)):
                    _migration().upgrade()
            yield connection
        finally:
            transaction.rollback()


def _public_snapshot(connection):
    definitions = connection.execute(text("""
        SELECT 'column',table_name||'.'||column_name,
               concat_ws('|',data_type,udt_name,is_nullable,column_default,numeric_precision,numeric_scale)
        FROM information_schema.columns WHERE table_schema='public'
        UNION ALL
        SELECT 'constraint',c.conrelid::regclass::text||'.'||c.conname,pg_get_constraintdef(c.oid)
        FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='public'
        UNION ALL
        SELECT 'index',indexname,indexdef FROM pg_indexes WHERE schemaname='public'
        ORDER BY 1,2,3
    """)).all()
    names = connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")).scalars()
    quote = connection.dialect.identifier_preparer.quote
    digests = {}
    for name in names:
        digests[name] = connection.execute(text(
            "SELECT md5(coalesce(string_agg(row_to_json(t)::text,'' ORDER BY row_to_json(t)::text),'')) "
            f"FROM public.{quote(name)} t"
        )).scalar_one()
    return definitions, digests


def _folder(connection, user, name=None, parent=None):
    identifier = uuid4()
    label = name or identifier.hex
    connection.execute(text("""
        INSERT INTO leny.carpetas(id,parent_id,name,name_key,created_by)
        VALUES(:id,:parent,:name,:key,:user)
    """), {"id": identifier, "parent": parent, "name": label, "key": label.casefold(), "user": user})
    return identifier


def _document(connection, folder, user):
    identifier = uuid4()
    connection.execute(text("""
        INSERT INTO leny.documentos(id,folder_id,title,created_by)
        VALUES(:id,:folder,'QA DOCUMENT',:user)
    """), {"id": identifier, "folder": folder, "user": user})
    return identifier


def _version(connection, document, user, number=1, **overrides):
    values = {"id": uuid4(), "document": document, "user": user, "number": number,
              "storage": uuid4().hex, "hash": "a" * 64, "bytes": 100,
              "type": "application/pdf", "status": "pending_contextualization"}
    values.update(overrides)
    connection.execute(text("""
        INSERT INTO leny.documento_versiones
            (id,document_id,number,storage_key,sha256,size_bytes,media_type,original_name,status,created_by)
        VALUES(:id,:document,:number,:storage,:hash,:bytes,:type,'QA.pdf',:status,:user)
    """), values)
    return values["id"]


def test_document_migration_roundtrip_preserves_existing_objects_and_public(pg_cluster):
    migration = _migration()
    rag_migration = _migration("20261019_0020_leny_contextualization.py")
    with pg_cluster.migration_engine.connect() as connection:
        transaction = connection.begin()
        try:
            pg_cluster.assert_identity(connection, pg_cluster.manifest, migrator=True)
            before = _public_snapshot(connection)
            old_leny = connection.execute(text("""
                SELECT table_name,column_name,data_type,is_nullable,column_default
                FROM information_schema.columns WHERE table_schema='leny'
                AND table_name IN ('conversaciones','mensajes','rate_users','admissions')
                ORDER BY table_name,ordinal_position
            """)).all()
            with Operations.context(MigrationContext.configure(connection)):
                _migration('20261020_0021_leny_publication_sources.py').downgrade()
                if connection.execute(text("SELECT to_regclass('leny.rag_trabajos')")).scalar_one():
                    rag_migration.downgrade()
                if connection.execute(text("SELECT to_regclass('leny.carpetas')")).scalar_one():
                    migration.downgrade()
                migration.upgrade()
                assert _public_snapshot(connection) == before
                assert connection.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname='leny' AND tablename IN ('carpetas','carpeta_roles_lectura','documentos','documento_roles_lectura','documento_versiones','documento_operaciones')")).scalar_one() == 6
                migration.downgrade()
                assert _public_snapshot(connection) == before
                assert connection.execute(text("SELECT to_regclass('leny.carpetas')")).scalar_one() is None
                assert connection.execute(text("""
                    SELECT table_name,column_name,data_type,is_nullable,column_default
                    FROM information_schema.columns WHERE table_schema='leny'
                    AND table_name IN ('conversaciones','mensajes','rate_users','admissions')
                    ORDER BY table_name,ordinal_position
                """)).all() == old_leny
        finally:
            transaction.rollback()


def test_runtime_role_has_required_library_access_without_superuser(pg_cluster):
    with pg_cluster.engine.connect() as connection:
        pg_cluster.assert_identity(connection, pg_cluster.manifest)
        assert connection.execute(text("SELECT has_schema_privilege(current_user,'leny','USAGE')")).scalar_one()
        for name in ('carpetas', 'carpeta_roles_lectura', 'documentos', 'documento_roles_lectura',
                     'documento_versiones', 'documento_operaciones'):
            assert connection.execute(text("SELECT has_table_privilege(current_user,:table,'SELECT,INSERT,UPDATE,DELETE')"),
                                      {"table": 'leny.' + name}).scalar_one()
        assert connection.execute(text("SELECT rolsuper FROM pg_roles WHERE rolname=current_user")).scalar_one() is False


def test_folder_root_sibling_unique_and_restrict_children(pg_cluster, synthetic_recipient):
    with _library(pg_cluster) as connection:
        user = synthetic_recipient.user_id
        root = _folder(connection, user)
        label = uuid4().hex
        _folder(connection, user, label)
        with pytest.raises(IntegrityError), connection.begin_nested():
            _folder(connection, user, label.upper())
        child = _folder(connection, user, label, root)
        with pytest.raises(IntegrityError), connection.begin_nested():
            _folder(connection, user, label.upper(), root)
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(text("UPDATE leny.carpetas SET parent_id=id WHERE id=:id"), {"id": child})
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(text("DELETE FROM leny.carpetas WHERE id=:id"), {"id": root})


def test_document_state_revision_and_stage01_publication(pg_cluster, synthetic_recipient):
    with _library(pg_cluster) as connection:
        user = synthetic_recipient.user_id
        folder = _folder(connection, user)
        document = _document(connection, folder, user)
        version = _version(connection, document, user)
        for assignment, values in [
            ("state='trash'", {}), ("revision=0", {}),
            ("published_version_id=:version", {"version": version}),
        ]:
            with pytest.raises(IntegrityError), connection.begin_nested():
                # Assignments are fixed test constants, never user-provided SQL.
                connection.execute(text(f"UPDATE leny.documentos SET {assignment} WHERE id=:id"), {"id": document, **values})
        connection.execute(text("""
            UPDATE leny.documentos SET state='trash',deleted_at=clock_timestamp(),
                purge_after=clock_timestamp()+interval '10 days',deleted_by=:user WHERE id=:id
        """), {"id": document, "user": user})
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(text("UPDATE leny.documentos SET state='active' WHERE id=:id"), {"id": document})


@pytest.mark.parametrize("override", [
    {"number": 0}, {"hash": "not-a-hash"}, {"bytes": 0}, {"bytes": 10485761},
    {"type": "image/png", "bytes": 5242881}, {"type": "text/html"}, {"status": "ready"},
])
def test_version_rejects_invalid_limits_and_fake_processing(pg_cluster, synthetic_recipient, override):
    with _library(pg_cluster) as connection:
        user = synthetic_recipient.user_id
        document = _document(connection, _folder(connection, user), user)
        with pytest.raises(IntegrityError), connection.begin_nested():
            _version(connection, document, user, **override)


def test_version_uniqueness_explicit_purge_and_durable_request_tombstone(pg_cluster, synthetic_recipient):
    with _library(pg_cluster) as connection:
        user = synthetic_recipient.user_id
        document = _document(connection, _folder(connection, user), user)
        version = _version(connection, document, user)
        with pytest.raises(IntegrityError), connection.begin_nested():
            _version(connection, document, user)
        request = uuid4()
        connection.execute(text("""
            INSERT INTO leny.documento_operaciones(id,account_id,user_id,kind,fingerprint,status,document_id,version_id)
            VALUES(:id,:account,:user,'upload',:hash,'completed',:document,:version)
        """), {"id": request, "account": synthetic_recipient.account_id, "user": user,
               "hash": "b" * 64, "document": document, "version": version})
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(text("DELETE FROM leny.documentos WHERE id=:id"), {"id": document})
        connection.execute(text("DELETE FROM leny.documento_versiones WHERE id=:id"), {"id": version})
        connection.execute(text("DELETE FROM leny.documentos WHERE id=:id"), {"id": document})
        assert connection.execute(text("SELECT document_id FROM leny.documento_operaciones WHERE id=:id"), {"id": request}).scalar_one() == document


def test_acl_duplicate_foreign_role_and_preview_consistency(pg_cluster, synthetic_recipient):
    with _library(pg_cluster) as connection:
        user = synthetic_recipient.user_id
        folder = _folder(connection, user)
        document = _document(connection, folder, user)
        values = {"document": document, "role": synthetic_recipient.role_id}
        connection.execute(text("INSERT INTO leny.documento_roles_lectura VALUES(:document,:role)"), values)
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(text("INSERT INTO leny.documento_roles_lectura VALUES(:document,:role)"), values)
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(text("INSERT INTO leny.documento_roles_lectura VALUES(:document,-1)"), values)
        version = _version(connection, document, user)
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(text("UPDATE leny.documento_versiones SET preview_key='orphan' WHERE id=:id"), {"id": version})


def test_published_version_composite_fk_preserves_ownership_after_future_stage_lift(pg_cluster, synthetic_recipient):
    with _library(pg_cluster) as connection:
        with Operations.context(MigrationContext.configure(connection)):
            _migration('20261020_0021_leny_publication_sources.py').downgrade()
        user = synthetic_recipient.user_id
        folder = _folder(connection, user)
        first = _document(connection, folder, user)
        second = _document(connection, folder, user)
        version = _version(connection, first, user)
        # Only in this rollback-only isolated DDL transaction: separately verify
        # the ownership FK, normally masked by the stricter stage01 NULL check.
        connection.execute(text("ALTER TABLE leny.documentos DROP CONSTRAINT ck_leny_document_unpublished_stage01"))
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(text("UPDATE leny.documentos SET published_version_id=:version WHERE id=:id"), {"version": version, "id": second})
        connection.execute(text("UPDATE leny.documentos SET published_version_id=:version WHERE id=:id"), {"version": version, "id": first})


def test_operation_request_identity_and_reconciliation_contract(pg_cluster, synthetic_recipient):
    with _library(pg_cluster) as connection:
        statement = text("""
            INSERT INTO leny.documento_operaciones(id,account_id,user_id,kind,fingerprint,status,payload)
            VALUES(:id,:account,:user,:kind,:hash,:status,CAST(:payload AS jsonb))
        """)
        values = {"id": uuid4(), "account": synthetic_recipient.account_id,
                  "user": synthetic_recipient.user_id, "kind": "upload",
                  "hash": "c" * 64, "status": "failed", "payload": '{}'}
        connection.execute(statement, values)
        # Failure does not release an idempotency identity for a second insert.
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(statement, values)
        for change in ({"status": "published"}, {"kind": ""}, {"payload": '[]'}):
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(statement, {**values, "id": uuid4(), **change})
