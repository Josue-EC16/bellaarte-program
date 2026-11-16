"""RAG invariants, only through the fail-closed isolated PostgreSQL launcher.

Each test's writes/DDL are rollback-only; no settings or business URLs load at
collection. The parent operator owns provisioning and migration execution.
"""
from contextlib import contextmanager
import importlib.util
from pathlib import Path
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError


def _migration(filename='20261019_0020_leny_contextualization.py'):
    path = Path(__file__).resolve().parents[2] / "alembic/versions" / filename
    spec = importlib.util.spec_from_file_location("leny_rag_migration_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def _rag(pg_cluster):
    with pg_cluster.migration_engine.connect() as connection:
        transaction = connection.begin()
        try:
            pg_cluster.assert_identity(connection, pg_cluster.manifest, migrator=True)
            assert connection.execute(text("SELECT to_regclass('leny.rag_trabajos')")).scalar_one()
            yield connection
        finally:
            transaction.rollback()


def _source(connection, recipient):
    folder, document, version = uuid4(), uuid4(), uuid4()
    values = {"folder": folder, "document": document, "version": version,
              "user": recipient.user_id, "name": folder.hex, "hash": "a" * 64}
    connection.execute(text("INSERT INTO leny.carpetas(id,name,name_key,created_by) VALUES(:folder,:name,:name,:user)"), values)
    connection.execute(text("INSERT INTO leny.documentos(id,folder_id,title,created_by) VALUES(:document,:folder,'QA RAG',:user)"), values)
    connection.execute(text("""
        INSERT INTO leny.documento_versiones(id,document_id,number,storage_key,sha256,size_bytes,media_type,original_name,created_by)
        VALUES(:version,:document,1,:name,:hash,100,'application/pdf','QA.pdf',:user)
    """), values)
    return document, version


def _indexation(connection, version, **changes):
    values = {"id": uuid4(), "version": version, "dimension": 1024, "status": "staging",
              "count": 0, "digest": "b" * 64}
    values.update(changes)
    connection.execute(text("""
        INSERT INTO leny.rag_indexaciones(id,version_id,model,model_digest,dimension,pipeline_version,chunking_version,ocr_version,status,chunk_count)
        VALUES(:id,:version,'qwen3-embedding:0.6b',:digest,:dimension,'v1','v1','v1',:status,:count)
    """), values)
    return values["id"]


def _job(connection, recipient, document, version, **changes):
    values = {"id": uuid4(), "account": recipient.account_id, "user": recipient.user_id,
              "document": document, "version": version, "hash": "a" * 64,
              "fingerprint": "c" * 64, "pipeline": "d" * 64, "status": "queued"}
    values.update(changes)
    connection.execute(text("""
        INSERT INTO leny.rag_trabajos(id,account_id,user_id,document_id,version_id,source_document_id,
            source_version_id,sha256,action,fingerprint,pipeline_fingerprint,status)
        VALUES(:id,:account,:user,:document,:version,:document,:version,:hash,'contextualize',:fingerprint,:pipeline,:status)
    """), values)
    return values["id"]


def _fragment(connection, indexation, **changes):
    values = {"id": uuid4(), "indexation": indexation, "ordinal": 0, "text": "Precio Bs 125,50; descuento 10%.",
              "hash": "e" * 64}
    values.update(changes)
    values.setdefault("chars", len(values["text"]))
    values.setdefault("bytes", len(values["text"].encode("utf-8")))
    connection.execute(text("""
        INSERT INTO leny.rag_fragmentos(id,indexation_id,ordinal,text,sha256,source_type,char_count,byte_count)
        VALUES(:id,:indexation,:ordinal,:text,:hash,'PDF_TEXT',:chars,:bytes)
    """), values)
    return values["id"]


def _embedding(connection, fragment, indexation, vector=None):
    vector = vector if vector is not None else "[1," + ",".join(["0"] * 1023) + "]"
    connection.execute(text("""
        INSERT INTO leny.rag_embeddings(fragment_id,indexation_id,embedding)
        VALUES(:fragment,:indexation,CAST(:vector AS leny.vector(1024)))
    """), {"fragment": fragment, "indexation": indexation, "vector": vector})


def _public_structure(connection):
    return connection.execute(text("""
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


def test_rag_migration_roundtrip_preserves_public_extension_and_originals(pg_cluster, synthetic_recipient):
    with _rag(pg_cluster) as connection:
        document, version = _source(connection, synthetic_recipient)
        original = connection.execute(text("SELECT id,document_id,number,sha256,storage_key FROM leny.documento_versiones WHERE id=:id"), {"id": version}).one()
        before = _public_structure(connection)
        extension = connection.execute(text("SELECT e.oid,e.extversion,n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE extname='vector'")).one()
        migration = _migration()
        with Operations.context(MigrationContext.configure(connection)):
            _migration('20261020_0021_leny_publication_sources.py').downgrade()
            migration.downgrade()
            assert connection.execute(text("SELECT to_regclass('leny.rag_trabajos')")).scalar_one() is None
            assert _public_structure(connection) == before
            migration.upgrade()
        assert _public_structure(connection) == before
        assert connection.execute(text("SELECT id,document_id,number,sha256,storage_key FROM leny.documento_versiones WHERE id=:id"), {"id": version}).one() == original
        assert connection.execute(text("SELECT e.oid,e.extversion,n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE extname='vector'")).one() == extension
        assert connection.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname='leny' AND tablename LIKE 'rag_%'")).scalar_one() == 5


def test_rag_runtime_dml_and_no_superuser(pg_cluster):
    with pg_cluster.engine.connect() as connection:
        pg_cluster.assert_identity(connection, pg_cluster.manifest)
        assert connection.execute(text("SELECT rolsuper FROM pg_roles WHERE rolname=current_user")).scalar_one() is False
        for table in ("rag_trabajos", "rag_indexaciones", "rag_fragmentos", "rag_embeddings", "rag_workers"):
            assert connection.execute(text("SELECT has_table_privilege(current_user,:table,'SELECT,INSERT,UPDATE,DELETE')"), {"table": "leny." + table}).scalar_one()


def test_rag_vector_1024_roundtrip_and_exact_distance_with_public_search_path(pg_cluster, synthetic_recipient):
    with _rag(pg_cluster) as connection:
        connection.execute(text("SET LOCAL search_path=public"))
        _, version = _source(connection, synthetic_recipient)
        indexation = _indexation(connection, version)
        fragment = _fragment(connection, indexation)
        _embedding(connection, fragment, indexation)
        row = connection.execute(text("""
            SELECT leny.vector_dims(embedding), embedding OPERATOR(leny.<=>) embedding,
                   pg_typeof(embedding)::text
            FROM leny.rag_embeddings WHERE fragment_id=:id
        """), {"id": fragment}).one()
        assert row[0] == 1024 and row[1] == pytest.approx(0) and row[2] == "leny.vector"
        with pytest.raises(DBAPIError), connection.begin_nested():
            _embedding(connection, _fragment(connection, indexation, ordinal=1), indexation, "[1,0,0]")


def test_rag_active_equivalence_and_global_request_identity(pg_cluster, synthetic_recipient):
    with _rag(pg_cluster) as connection:
        document, version = _source(connection, synthetic_recipient)
        job = _job(connection, synthetic_recipient, document, version)
        with pytest.raises(IntegrityError), connection.begin_nested():
            _job(connection, synthetic_recipient, document, version)
        with pytest.raises(IntegrityError), connection.begin_nested():
            _job(connection, synthetic_recipient, document, version, id=job, pipeline="f" * 64)
        connection.execute(text("UPDATE leny.rag_trabajos SET status='failed' WHERE id=:id"), {"id": job})
        _job(connection, synthetic_recipient, document, version)
        # Failed request UUIDs remain unavailable even when equivalence is free.
        with pytest.raises(IntegrityError), connection.begin_nested():
            _job(connection, synthetic_recipient, document, version, id=job, pipeline="f" * 64)


def test_rag_running_requires_complete_lease(pg_cluster, synthetic_recipient):
    with _rag(pg_cluster) as connection:
        document, version = _source(connection, synthetic_recipient)
        job = _job(connection, synthetic_recipient, document, version)
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(text("UPDATE leny.rag_trabajos SET status='running' WHERE id=:id"), {"id": job})
        connection.execute(text("""
            UPDATE leny.rag_trabajos SET status='running',worker_id=:worker,run_token=:token,
                lease_until=clock_timestamp()+interval '60 seconds' WHERE id=:id
        """), {"id": job, "worker": uuid4(), "token": uuid4()})


def test_rag_retry_retains_prior_request_identity(pg_cluster, synthetic_recipient):
    with _rag(pg_cluster) as connection:
        document, version = _source(connection, synthetic_recipient)
        first = _job(connection, synthetic_recipient, document, version, status="failed")
        second = _job(connection, synthetic_recipient, document, version)
        connection.execute(text("UPDATE leny.rag_trabajos SET action='retry',retry_of_id=:first WHERE id=:id"), {"first": first, "id": second})
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(text("DELETE FROM leny.rag_trabajos WHERE id=:id"), {"id": first})


def test_rag_validated_pointer_belongs_to_exact_version(pg_cluster, synthetic_recipient):
    with _rag(pg_cluster) as connection:
        _, first = _source(connection, synthetic_recipient)
        _, second = _source(connection, synthetic_recipient)
        indexation = _indexation(connection, first)
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(text("UPDATE leny.documento_versiones SET validated_indexation_id=:indexation WHERE id=:id"), {"indexation": indexation, "id": second})
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(text("UPDATE leny.documento_versiones SET status='pending_publication' WHERE id=:id"), {"id": first})
        connection.execute(text("UPDATE leny.rag_indexaciones SET status='validated',chunk_count=1,validated_at=clock_timestamp() WHERE id=:id"), {"id": indexation})
        connection.execute(text("UPDATE leny.documento_versiones SET status='pending_publication',validated_indexation_id=:indexation WHERE id=:id"), {"indexation": indexation, "id": first})
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(text("DELETE FROM leny.rag_indexaciones WHERE id=:id"), {"id": indexation})


def test_rag_failed_recontextualization_does_not_replace_validated_pointer(pg_cluster, synthetic_recipient):
    with _rag(pg_cluster) as connection:
        document, version = _source(connection, synthetic_recipient)
        old = _indexation(connection, version)
        connection.execute(text("UPDATE leny.rag_indexaciones SET status='validated',chunk_count=1,validated_at=clock_timestamp() WHERE id=:id"), {"id": old})
        connection.execute(text("UPDATE leny.documento_versiones SET status='pending_publication',validated_indexation_id=:indexation WHERE id=:id"), {"indexation": old, "id": version})
        new = _indexation(connection, version)
        connection.execute(text("UPDATE leny.rag_indexaciones SET status='failed' WHERE id=:id"), {"id": new})
        _job(connection, synthetic_recipient, document, version, status="failed")
        assert connection.execute(text("SELECT validated_indexation_id FROM leny.documento_versiones WHERE id=:id"), {"id": version}).scalar_one() == old


def test_rag_embedding_cannot_mix_indexations_and_cascades_with_fragment(pg_cluster, synthetic_recipient):
    with _rag(pg_cluster) as connection:
        _, version = _source(connection, synthetic_recipient)
        first, second = _indexation(connection, version), _indexation(connection, version)
        fragment = _fragment(connection, first)
        with pytest.raises(IntegrityError), connection.begin_nested():
            _embedding(connection, fragment, second)
        _embedding(connection, fragment, first)
        connection.execute(text("DELETE FROM leny.rag_fragmentos WHERE id=:id"), {"id": fragment})
        assert connection.execute(text("SELECT count(*) FROM leny.rag_embeddings WHERE fragment_id=:id"), {"id": fragment}).scalar_one() == 0


@pytest.mark.parametrize("change", [{"ordinal": -1}, {"chars": 1}, {"bytes": 1}, {"hash": "bad"}, {"text": ""}])
def test_rag_fragment_provenance_lengths_and_ordinal(pg_cluster, synthetic_recipient, change):
    with _rag(pg_cluster) as connection:
        _, version = _source(connection, synthetic_recipient)
        indexation = _indexation(connection, version)
        with pytest.raises(IntegrityError), connection.begin_nested():
            _fragment(connection, indexation, **change)


def test_rag_fragment_ordinal_unique_and_dimension_checked(pg_cluster, synthetic_recipient):
    with _rag(pg_cluster) as connection:
        _, version = _source(connection, synthetic_recipient)
        indexation = _indexation(connection, version)
        _fragment(connection, indexation)
        with pytest.raises(IntegrityError), connection.begin_nested():
            _fragment(connection, indexation)
        with pytest.raises(IntegrityError), connection.begin_nested():
            _indexation(connection, version, dimension=768)
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(text("UPDATE leny.rag_indexaciones SET status='validated' WHERE id=:id"), {"id": indexation})


def test_rag_explicit_purge_preserves_request_tombstone_and_worker_quarantine(pg_cluster, synthetic_recipient):
    with _rag(pg_cluster) as connection:
        document, version = _source(connection, synthetic_recipient)
        indexation = _indexation(connection, version)
        fragment = _fragment(connection, indexation)
        _embedding(connection, fragment, indexation)
        job = _job(connection, synthetic_recipient, document, version, status="invalidated")
        worker = uuid4()
        connection.execute(text("INSERT INTO leny.rag_workers(id,host_instance,pid,current_job_id,provider_inflight) VALUES(:id,'synthetic-local-host',1,:job,true)"), {"id": worker, "job": job})
        connection.execute(text("UPDATE leny.rag_trabajos SET indexation_id=:indexation WHERE id=:id"), {"indexation": indexation, "id": job})
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(text("DELETE FROM leny.documento_versiones WHERE id=:id"), {"id": version})
        connection.execute(text("DELETE FROM leny.rag_indexaciones WHERE id=:id"), {"id": indexation})
        connection.execute(text("DELETE FROM leny.documento_versiones WHERE id=:id"), {"id": version})
        connection.execute(text("DELETE FROM leny.documentos WHERE id=:id"), {"id": document})
        row = connection.execute(text("SELECT document_id,version_id,indexation_id,source_document_id,source_version_id FROM leny.rag_trabajos WHERE id=:id"), {"id": job}).one()
        assert row == (None, None, None, document, version)
        assert connection.execute(text("SELECT provider_inflight FROM leny.rag_workers WHERE id=:id"), {"id": worker}).scalar_one() is True
        assert connection.execute(text("SELECT count(*) FROM leny.rag_embeddings WHERE indexation_id=:id"), {"id": indexation}).scalar_one() == 0
