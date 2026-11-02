"""LENY DDL and constraints, only through the fail-closed isolated PG launcher."""
import importlib.util
from pathlib import Path
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import sessionmaker
from app.services.leny_policy import POLICY_VERSION


def _migration(filename="20261019_0017_leny.py"):
    path = Path(__file__).resolve().parents[2] / "alembic/versions" / filename
    spec = importlib.util.spec_from_file_location("leny_migration_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _public_snapshot(connection):
    """Definitions and table contents, without logging data or consuming sequences."""
    definitions = connection.execute(text("""
        SELECT 'column', table_name || '.' || column_name,
               concat_ws('|', data_type, udt_name, is_nullable, column_default, numeric_precision, numeric_scale)
        FROM information_schema.columns WHERE table_schema='public'
        UNION ALL
        SELECT 'constraint', c.conrelid::regclass::text || '.' || c.conname, pg_get_constraintdef(c.oid)
        FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='public'
        UNION ALL
        SELECT 'index', indexname, indexdef FROM pg_indexes WHERE schemaname='public'
        UNION ALL
        SELECT 'function', p.oid::regprocedure::text, pg_get_functiondef(p.oid)
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
        WHERE n.nspname='public' AND p.prokind='f'
        UNION ALL
        SELECT 'trigger', t.tgrelid::regclass::text || '.' || t.tgname, pg_get_triggerdef(t.oid)
        FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND NOT t.tgisinternal
        ORDER BY 1,2,3
    """)).all()
    tables = connection.execute(text("""
        SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename
    """)).scalars().all()
    quote = connection.dialect.identifier_preparer.quote
    contents = {}
    for table in tables:
        # Identifiers originate in pg_catalog and are quoted by the driver dialect.
        contents[table] = connection.execute(text(
            f"SELECT md5(coalesce(string_agg(row_to_json(t)::text, '' ORDER BY row_to_json(t)::text), '')) "
            f"FROM public.{quote(table)} t"
        )).scalar_one()
    return definitions, contents


def test_leny_migration_rollback_preserves_public_and_restricts_installed_extension(pg_cluster):
    migration = _migration()
    policy_migration = _migration("20261019_0018_leny_policy_rate.py")
    document_migration = _migration("20261019_0019_leny_documents.py")
    rag_migration = _migration("20261019_0020_leny_contextualization.py")
    with pg_cluster.migration_engine.connect() as connection:
        transaction = connection.begin()
        try:
            pg_cluster.assert_identity(connection, pg_cluster.manifest, migrator=True)
            before = _public_snapshot(connection)
            with Operations.context(MigrationContext.configure(connection)):
                extension = connection.execute(text("""
                    SELECT e.oid FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace
                    WHERE e.extname='vector' AND n.nspname='leny'
                """)).scalar_one_or_none()
                if connection.execute(text("SELECT to_regclass('leny.rag_trabajos')")).scalar_one():
                    _migration('20261020_0021_leny_publication_sources.py').downgrade()
                    rag_migration.downgrade()
                document_migration.downgrade()
                policy_migration.downgrade()
                if extension is not None:
                    # 0017 deliberately uses DROP SCHEMA RESTRICT. After the
                    # separately provisioned extension exists, a full downgrade
                    # must fail closed. Its SAVEPOINT rolls back the two table
                    # drops too. Never remove vector or elevate the test role.
                    with pytest.raises(DBAPIError) as blocked, connection.begin_nested():
                        migration.downgrade()
                    assert blocked.value.orig.pgcode == '2BP01'
                    assert connection.execute(text("SELECT to_regclass('leny.mensajes')")).scalar_one()
                    assert connection.execute(text("SELECT oid FROM pg_extension WHERE extname='vector'")).scalar_one() == extension
                    assert _public_snapshot(connection) == before
                else:
                    # Retain the original full roundtrip for a pre-extension
                    # fixture; its historical behavior is not silently mocked.
                    migration.downgrade()
                    assert connection.execute(text("SELECT to_regnamespace('leny')")).scalar_one() is None
                    assert _public_snapshot(connection) == before
                    migration.upgrade()
                    assert connection.execute(text("SELECT to_regclass('leny.mensajes')")).scalar_one()
                    assert _public_snapshot(connection) == before
                    migration.downgrade()
                    assert _public_snapshot(connection) == before
        finally:
            transaction.rollback()
        # Transaction rollback restores the original schema and its runtime grants.
        assert connection.execute(text("SELECT to_regclass('leny.conversaciones')")).scalar_one()
        assert _public_snapshot(connection) == before


def test_leny_policy_migration_legacy_default_and_public_unchanged(pg_cluster, synthetic_recipient):
    migration = _migration("20261019_0018_leny_policy_rate.py")
    with pg_cluster.migration_engine.connect() as connection:
        transaction = connection.begin()
        try:
            before = _public_snapshot(connection)
            with Operations.context(MigrationContext.configure(connection)):
                migration.downgrade()
                conversation = _conversation(connection, synthetic_recipient)
                _message(connection, conversation, uuid4())
                migration.upgrade()
                assert connection.execute(text("SELECT context_eligible FROM leny.mensajes WHERE conversation_id=:id"),
                                          {'id': conversation}).scalar_one() is False
                assert _public_snapshot(connection) == before
                migration.downgrade()
                assert _public_snapshot(connection) == before
        finally:
            transaction.rollback()


def _conversation(connection, recipient):
    identifier = uuid4()
    connection.execute(text("""
        INSERT INTO leny.conversaciones(id,user_id,account_id,title)
        VALUES(:id,:user,:account,'QA LENY')
    """), {"id": identifier, "user": recipient.user_id, "account": recipient.account_id})
    return identifier


def _message(connection, conversation, request_id, *, sequence=1, role="user", status="completed"):
    connection.execute(text("""
        INSERT INTO leny.mensajes(id,conversation_id,sequence,request_id,role,content,status)
        VALUES(:id,:conversation,:sequence,:request,:role,'QA SYNTHETIC',:status)
    """), {"id": uuid4(), "conversation": conversation, "sequence": sequence,
           "request": request_id, "role": role, "status": status})


def test_leny_request_identity_sequence_and_cascade(pg_cluster, synthetic_recipient):
    with pg_cluster.engine.connect() as connection:
        transaction = connection.begin()
        try:
            conversation = _conversation(connection, synthetic_recipient)
            other = _conversation(connection, synthetic_recipient)
            request = uuid4()
            _message(connection, conversation, request)
            _message(connection, conversation, request, sequence=2, role="assistant")
            # Idempotency key cannot be moved into a different conversation.
            with pytest.raises(IntegrityError), connection.begin_nested():
                _message(connection, other, request)
            # Sequence uniqueness applies independently of the request id.
            with pytest.raises(IntegrityError), connection.begin_nested():
                _message(connection, conversation, uuid4())
            with pytest.raises(IntegrityError), connection.begin_nested():
                _message(connection, other, uuid4(), sequence=0)
            with pytest.raises(IntegrityError), connection.begin_nested():
                _message(connection, other, uuid4(), role="system")
            with pytest.raises(IntegrityError), connection.begin_nested():
                _message(connection, other, uuid4(), status="invented")
            connection.execute(text("DELETE FROM leny.conversaciones WHERE id=:id"), {"id": conversation})
            assert connection.execute(text("SELECT count(*) FROM leny.mensajes WHERE conversation_id=:id"),
                                      {"id": conversation}).scalar_one() == 0
        finally:
            transaction.rollback()


def test_leny_restricts_owner_deletion(pg_cluster, synthetic_recipient):
    with pg_cluster.engine.connect() as connection:
        transaction = connection.begin()
        try:
            _conversation(connection, synthetic_recipient)
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(text("DELETE FROM cuentas WHERE id=:id"), {"id": synthetic_recipient.account_id})
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(text("DELETE FROM usuarios WHERE id=:id"), {"id": synthetic_recipient.user_id})
        finally:
            transaction.rollback()


@pytest.fixture
def leny_store(pg_cluster):
    from app.services.leny_store import LenyStore
    return LenyStore(sessionmaker(bind=pg_cluster.engine, expire_on_commit=False))


@pytest.fixture
def leny_actor(synthetic_recipient):
    from app.services.leny_store import LenyActor
    return LenyActor(synthetic_recipient.account_id, synthetic_recipient.user_id, str(uuid4()))


@pytest.fixture
def other_leny_actor(pg_cluster, synthetic_recipient):
    """A second real individual; role cannot confer ownership in LenyActor."""
    from app.services.leny_store import LenyActor
    token = uuid4().hex
    with pg_cluster.engine.begin() as connection:
        user = connection.execute(text("""
            INSERT INTO usuarios(nombres,apellido_paterno,ci,celular,correo,zona,activo)
            VALUES('QA','LENY PRIVACY',:ci,'00000000',:mail,'TEST',true) RETURNING id
        """), {"ci": token[:25], "mail": token + '@example.invalid'}).scalar_one()
        account = connection.execute(text("""
            INSERT INTO cuentas(usuario_id,rol_id,username,password_hash,must_change_password,is_active)
            VALUES(:user,:role,:name,'NOT_A_REAL_LOGIN_HASH',true,true) RETURNING id
        """), {"user": user, "role": synthetic_recipient.role_id, "name": 'qa_' + token}).scalar_one()
    try:
        yield LenyActor(account, user, str(uuid4()))
    finally:
        with pg_cluster.engine.begin() as connection:
            connection.execute(text('DELETE FROM leny.conversaciones WHERE user_id=:id'), {"id": user})
            connection.execute(text('DELETE FROM leny.admissions WHERE user_id=:id'), {"id": user})
            connection.execute(text('DELETE FROM leny.rate_users WHERE user_id=:id'), {"id": user})
            connection.execute(text('DELETE FROM auditoria_sistema WHERE usu_id=:id'), {"id": user})
            connection.execute(text('DELETE FROM cuentas WHERE id=:id'), {"id": account})
            connection.execute(text('DELETE FROM usuarios WHERE id=:id'), {"id": user})


@pytest.fixture
def coordinator(pg_cluster):
    from app.services.leny_coordination import PostgresCoordinator
    coordinator = PostgresCoordinator(pg_cluster.engine.url)
    try:
        yield coordinator
    finally:
        coordinator.engine.dispose()


def test_leny_store_private_crud_and_physical_deletion(leny_store, leny_actor, other_leny_actor, pg_cluster):
    from app.services.leny_ollama import LenyError
    conversation = leny_store.create(leny_actor)['id']
    from uuid import UUID
    conversation = UUID(conversation)
    assistant, history = leny_store.begin_turn(leny_actor, conversation, uuid4(), 'Hola QA', 'qa-model')
    assert history == []
    leny_store.save(leny_actor, conversation, assistant, 'Respuesta QA', 'completed')
    assert leny_store.list(leny_actor, 1, 20)['total'] == 1
    assert leny_store.list(other_leny_actor, 1, 20)['total'] == 0
    assert leny_store.detail(leny_actor, conversation, 1, 50)['total'] == 2
    # Even administrative permissions never enter the ownership interface.
    for operation in (
        lambda: leny_store.detail(other_leny_actor, conversation, 1, 50),
        lambda: leny_store.remove(other_leny_actor, conversation),
        lambda: leny_store.begin_turn(other_leny_actor, conversation, uuid4(), 'Intrusión', 'qa-model'),
        lambda: leny_store.save(other_leny_actor, conversation, assistant, 'Intrusión', 'completed'),
    ):
        with pytest.raises(LenyError) as failure:
            operation()
        assert failure.value.status == 404
    leny_store.remove(leny_actor, conversation)
    with pg_cluster.engine.connect() as connection:
        assert connection.execute(text('SELECT count(*) FROM leny.conversaciones WHERE id=:id'), {'id': conversation}).scalar_one() == 0
        assert connection.execute(text('SELECT count(*) FROM leny.mensajes WHERE conversation_id=:id'), {'id': conversation}).scalar_one() == 0


@pytest.mark.parametrize('status', ['completed', 'failed', 'interrupted'])
def test_leny_duplicate_requests_preserve_terminal_state(leny_store, leny_actor, status):
    from uuid import UUID
    from app.services.leny_store import LenyConflict
    conversation = UUID(leny_store.create(leny_actor)['id'])
    request = uuid4()
    assistant, _ = leny_store.begin_turn(leny_actor, conversation, request, 'Pregunta QA', 'qa-model')
    leny_store.save(leny_actor, conversation, assistant, 'Resultado QA', status)
    with pytest.raises(LenyConflict) as duplicate:
        leny_store.duplicate(leny_actor, conversation, request, 'Pregunta QA')
    assert duplicate.value.status == 409
    assert duplicate.value.code == 'LENY_REQUEST_DUPLICATE'
    assert duplicate.value.generation_status == status
    assert duplicate.value.request_id == request
    with pytest.raises(LenyConflict) as changed:
        leny_store.duplicate(leny_actor, conversation, request, 'Contenido diferente')
    assert changed.value.code == 'LENY_REQUEST_REUSED'
    with pytest.raises(LenyConflict):
        leny_store.begin_turn(leny_actor, conversation, request, 'Pregunta QA', 'qa-model')
    assert leny_store.detail(leny_actor, conversation, 1, 50)['total'] == 2


def test_leny_context_excludes_partial_turn_and_reconciles_abandonment(leny_store, leny_actor, coordinator):
    from uuid import UUID
    from app.services.leny_store import LenyConflict
    conversation = UUID(leny_store.create(leny_actor)['id'])
    lease = coordinator.acquire()
    try:
        leny_store.reconcile()
        first, _ = leny_store.begin_turn(leny_actor, conversation, uuid4(), 'Completa QA', 'qa-model')
        leny_store.save(leny_actor, conversation, first, 'Respuesta completa QA', 'completed',
                        category='business', reason='business_context', policy_version=POLICY_VERSION, context_eligible=True)
        partial, context = leny_store.begin_turn(leny_actor, conversation, uuid4(), 'Interrumpida QA', 'qa-model')
        assert context == [{'role': 'user', 'content': 'Completa QA'}, {'role': 'assistant', 'content': 'Respuesta completa QA'}]
        leny_store.save(leny_actor, conversation, partial, 'Respuesta parcial QA', 'generating')
        with pytest.raises(LenyConflict) as deleting:
            leny_store.remove(leny_actor, conversation)
        assert deleting.value.code == 'LENY_GENERATING'
    finally:
        lease.close()
    # New coordinator lease simulates another worker after the old one exits.
    lease = coordinator.acquire()
    try:
        assert leny_store.reconcile() == 1
        assert leny_store.reconcile() == 0
        rows = leny_store.detail(leny_actor, conversation, 1, 50)['items']
        assert rows[-1]['status'] == 'interrupted'
        assert rows[-1]['content'] == 'Respuesta parcial QA'
        with pytest.raises(LenyConflict):
            leny_store.save(leny_actor, conversation, partial, 'No sobrescribir', 'completed')
        final, context = leny_store.begin_turn(leny_actor, conversation, uuid4(), 'Nueva QA', 'qa-model')
        assert context == [{'role': 'user', 'content': 'Completa QA'}, {'role': 'assistant', 'content': 'Respuesta completa QA'}]
        leny_store.save(leny_actor, conversation, final, '', 'interrupted')
    finally:
        lease.close()


def test_old_policy_and_refused_turns_remain_visible_but_never_enter_context(leny_store, leny_actor, coordinator):
    from uuid import UUID
    conversation = UUID(leny_store.create(leny_actor)['id'])
    lease = coordinator.acquire()
    try:
        leny_store.reconcile()
        old, context = leny_store.begin_turn(leny_actor, conversation, uuid4(), 'Consulta empresarial antigua', 'qa-model')
        assert context == []
        leny_store.save(leny_actor, conversation, old, 'Respuesta de política anterior', 'completed',
                        category='business', reason='business_context', policy_version='legacy-test-policy', context_eligible=True)
        refused, context = leny_store.begin_turn(leny_actor, conversation, uuid4(), 'Consulta rechazada', 'qa-model')
        assert context == []
        leny_store.save(leny_actor, conversation, refused, 'Fuera de ámbito empresarial', 'completed',
                        category='out_of_scope', reason='outside_business_scope', policy_version=POLICY_VERSION, context_eligible=False)
        approved, context = leny_store.begin_turn(leny_actor, conversation, uuid4(), 'Consulta empresarial vigente', 'qa-model')
        assert context == []
        leny_store.save(leny_actor, conversation, approved, 'Respuesta empresarial vigente', 'completed',
                        category='business', reason='business_context', policy_version=POLICY_VERSION, context_eligible=True)
        next_turn, context = leny_store.begin_turn(leny_actor, conversation, uuid4(), 'Seguimiento', 'qa-model')
        assert context == [
            {'role': 'user', 'content': 'Consulta empresarial vigente'},
            {'role': 'assistant', 'content': 'Respuesta empresarial vigente'},
        ]
        leny_store.save(leny_actor, conversation, next_turn, '', 'interrupted')
        detail = leny_store.detail(leny_actor, conversation, 1, 50)
        assert detail['total'] == 8
        assert any(row['content'] == 'Respuesta de política anterior' for row in detail['items'])
        assert any(row['content'] == 'Fuera de ámbito empresarial' for row in detail['items'])
    finally:
        lease.close()


def test_leny_global_advisory_lock_contention_and_exception_release(coordinator):
    from app.services.leny_ollama import LenyError
    lease = coordinator.acquire()
    try:
        lease.check()
        with pytest.raises(LenyError) as busy:
            coordinator.acquire()
        assert busy.value.code == 'LENY_BUSY'
        assert busy.value.status == 429
        with pytest.raises(RuntimeError):
            try:
                raise RuntimeError('Synthetic generation failure')
            finally:
                lease.close()
    finally:
        lease.close()  # idempotent cleanup, including after exception
    next_lease = coordinator.acquire()
    try:
        next_lease.check()
    finally:
        next_lease.close()


def test_leny_connection_loss_releases_lock_and_detects_lost_lease(coordinator, pg_cluster):
    from app.services.leny_ollama import LenyError
    lease = coordinator.acquire()
    try:
        pid = lease._connection.execute(text('SELECT pg_backend_pid()')).scalar_one()
        # Only the synthetic runner's dedicated connection is terminated. This
        # reproduces backend/network loss without restarting any PostgreSQL server.
        with pg_cluster.engine.begin() as connection:
            assert connection.execute(text('SELECT pg_terminate_backend(:pid)'), {'pid': pid}).scalar_one()
        with pytest.raises(LenyError) as lost:
            lease.check()
        assert lost.value.code == 'LENY_LOCK_LOST'
    finally:
        lease.close()
    next_lease = coordinator.acquire()
    try:
        next_lease.check()
    finally:
        next_lease.close()
