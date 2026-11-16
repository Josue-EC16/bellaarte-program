"""Real RAG transactions on the guarded isolated cluster; no OCR/Ollama calls.

Committed source metadata belongs solely to synthetic_recipient and is cleaned
by its existing fixture. Parser readiness is simulated, never document content.
"""
import hashlib
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def rag_context(pg_cluster, synthetic_recipient, tmp_path, monkeypatch):
    from app.core.config import settings
    from app.services.leny_rag_service import RagService

    actor = SimpleNamespace(account_id=synthetic_recipient.account_id,
                            user_id=synthetic_recipient.user_id)
    root = tmp_path / 'private-rag-library'
    assert not root.resolve().is_relative_to(Path(__file__).resolve().parents[3])
    configured = settings.model_copy(update={
        'leny_rag_enabled': True, 'leny_documents_enabled': True,
        'leny_documents_root': str(root), 'leny_documents_min_free_bytes': 0,
        'leny_rag_min_free_bytes': 0, 'leny_rag_min_ram_bytes': 0,
        'leny_rag_tesseract_path': str(tmp_path / 'no-native-tools' / 'tesseract.exe'),
        'leny_rag_tessdata_path': str(tmp_path / 'no-native-tools' / 'tessdata'),
    })
    assert make_url(configured.effective_database_url) == pg_cluster.engine.url
    with pg_cluster.engine.begin() as connection:
        pg_cluster.assert_identity(connection, pg_cluster.manifest)
        created_admin = connection.execute(text("""
            INSERT INTO roles(codigo,nombre,activo) VALUES('ADMIN',:name,true)
            ON CONFLICT(codigo) DO NOTHING RETURNING id
        """), {'name': 'QA RAG ADMIN ' + uuid4().hex}).scalar_one_or_none()
        admin = created_admin or connection.execute(text("SELECT id FROM roles WHERE codigo='ADMIN' AND activo=true")).scalar_one()
        connection.execute(text('UPDATE cuentas SET rol_id=:role,must_change_password=false WHERE id=:id'),
                           {'role': admin, 'id': actor.account_id})
    service = RagService(configured, sessionmaker(bind=pg_cluster.engine, expire_on_commit=False))
    monkeypatch.setattr(service, 'local_dependencies', lambda: {'ready': True, 'parsers': True, 'tesseract': True})
    workers = []
    context = SimpleNamespace(service=service, actor=actor, cluster=pg_cluster,
                              recipient=synthetic_recipient, workers=workers)
    try:
        yield context
    finally:
        service.documents.engine.dispose()
        with pg_cluster.engine.begin() as connection:
            pg_cluster.assert_identity(connection, pg_cluster.manifest)
            for worker in workers:
                connection.execute(text('DELETE FROM leny.rag_workers WHERE id=:id'), {'id': worker})
            connection.execute(text('UPDATE cuentas SET rol_id=:role,must_change_password=true WHERE id=:id'),
                               {'role': synthetic_recipient.role_id, 'id': actor.account_id})
            if created_admin:
                connection.execute(text('DELETE FROM roles WHERE id=:id'), {'id': created_admin})


def _source(context):
    folder, document, version = uuid4(), uuid4(), uuid4()
    values = dict(folder=folder, document=document, version=version,
                  user=context.actor.user_id, label=folder.hex, hash='a' * 64)
    with context.cluster.engine.begin() as connection:
        connection.execute(text('INSERT INTO leny.carpetas(id,name,name_key,created_by) VALUES(:folder,:label,:label,:user)'), values)
        connection.execute(text("INSERT INTO leny.documentos(id,folder_id,title,created_by) VALUES(:document,:folder,'QA RAG SOURCE',:user)"), values)
        connection.execute(text("""
            INSERT INTO leny.documento_versiones(id,document_id,number,storage_key,sha256,size_bytes,media_type,original_name,created_by)
            VALUES(:version,:document,1,:label,:hash,100,'application/pdf','QA.pdf',:user)
        """), values)
    return document, version


def _request(*, request_id=None, action='contextualize', retry_of=None):
    from app.schemas.leny_rag import ContextualizationRequest
    return ContextualizationRequest(request_id=request_id or uuid4(), action=action, retry_of=retry_of)


def _submit(context, source=None, **options):
    source = source or _source(context)
    data = _request(**options)
    result, admitted = context.service.submit(context.actor, *source, data)
    assert admitted
    return source, data, result


def _worker(context):
    identity = uuid4()
    context.workers.append(identity)
    context.service.register(identity, 'qa-' + uuid4().hex, 1)
    return identity


def _claim(context):
    source, request, job = _submit(context)
    worker = _worker(context)
    claim = context.service.claim(worker)
    assert claim['id'] == job['id']
    return source, request, worker, claim


def _fragments(context, count=2):
    from app.services.leny_rag_chunking import fragment_units
    units = [dict(text=f'Precio empresarial Bs {125 + ordinal},50; descuento 10%.',
                  source_type='PDF_TEXT', locator={'page': ordinal + 1}) for ordinal in range(count)]
    return fragment_units(units, context.service.settings)


def _complete(context, claim):
    context.service.fragments(claim, _fragments(context), {'complete': True, 'warnings': []})
    pending = context.service.pending_fragments(claim['indexation_id'])
    context.service.save_vectors(claim, pending, [[1.0] + [0.0] * 1023 for _ in pending])
    context.service.finish(claim)


def _state(context, version):
    with context.cluster.engine.connect() as connection:
        return connection.execute(text('SELECT status,validated_indexation_id FROM leny.documento_versiones WHERE id=:id'), {'id': version}).one()


def test_backend_shutdown_requeues_same_request_and_preserves_saved_vectors(rag_context):
    context=rag_context
    _,_,worker,claim=_claim(context)
    context.service.fragments(claim,_fragments(context),{'complete':True,'warnings':[]})
    pending=context.service.pending_fragments(claim['indexation_id'])
    context.service.save_vectors(claim,pending[:1],[[1.0]+[0.0]*1023])
    context.service.defer(claim,'RAG_WORKER_SHUTDOWN')
    context.service.stopped(worker)
    with context.cluster.engine.connect() as db:
        row=db.execute(text('SELECT status,error_code,run_token FROM leny.rag_trabajos WHERE id=:id'),{'id':claim['id']}).one()
        assert tuple(row)==('queued','RAG_WORKER_SHUTDOWN',None)
        assert db.scalar(text('SELECT count(*) FROM leny.rag_embeddings WHERE indexation_id=:id'),{'id':claim['indexation_id']})==1
    new_worker=_worker(context)
    resumed=context.service.claim(new_worker)
    assert resumed['id']==claim['id'] and resumed['indexation_id']==claim['indexation_id']
    assert len(context.service.pending_fragments(resumed['indexation_id']))==len(pending)-1
    _complete(context,resumed)
    with context.cluster.engine.connect() as db:
        assert db.scalar(text('SELECT status FROM leny.rag_trabajos WHERE id=:id'),{'id':claim['id']})=='completed'


def test_backend_shutdown_never_overrides_an_explicit_user_cancellation(rag_context):
    from app.services.leny_rag_common import RagError
    context=rag_context
    _,_,worker,claim=_claim(context)
    context.service.cancel(context.actor,claim['id'])
    with pytest.raises(RagError) as cancelled:
        context.service.defer(claim,'RAG_WORKER_SHUTDOWN')
    assert cancelled.value.code=='RAG_CANCELLED'
    context.service.stopped(worker)
    next_worker=_worker(context)
    assert context.service.claim(next_worker) is None
    with context.cluster.engine.connect() as db:
        assert db.scalar(text('SELECT status FROM leny.rag_trabajos WHERE id=:id'),{'id':claim['id']})=='cancelled'


def test_rag_submit_idempotency_keeps_one_job_and_rejects_reused_payload(rag_context):
    context = rag_context
    source, data, initial = _submit(context)
    replay, admitted = context.service.submit(context.actor, *source, data)
    assert admitted is False and replay['id'] == initial['id']
    other = _source(context)
    from app.services.leny_rag_common import RagError
    with pytest.raises(RagError) as conflict:
        context.service.submit(context.actor, *other, data)
    assert conflict.value.code == 'RAG_REQUEST_CONFLICT'
    assert context.service.history(*source)['total'] == 1


def test_rag_failed_request_requires_new_explicit_retry_link(rag_context):
    context = rag_context
    source, data, _, claim = _claim(context)
    context.service.fail(claim, 'RAG_PROVIDER_TIMEOUT')
    from app.services.leny_rag_common import RagError
    with pytest.raises(RagError) as reused:
        context.service.submit(context.actor, *source, data)
    assert reused.value.code == 'RAG_REQUEST_TERMINAL'
    _, retry, result = _submit(context, source, action='retry', retry_of=data.request_id)
    assert retry.request_id != data.request_id and result['retry_of'] == data.request_id
    assert context.service.get(data.request_id)['status'] == 'failed'


def test_rag_rate_limit_counts_cancelled_requests_but_not_replays(rag_context):
    context = rag_context
    context.service.settings.leny_rag_rate_limit = 2
    first_source, first, _ = _submit(context)
    context.service.submit(context.actor, *first_source, first)
    context.service.cancel(context.actor, first.request_id)
    second_source, second, _ = _submit(context)
    context.service.cancel(context.actor, second.request_id)
    from app.services.leny_rag_common import RagError
    with pytest.raises(RagError) as limited:
        _submit(context)
    assert limited.value.code == 'RAG_RATE_LIMITED' and limited.value.status == 429
    with context.cluster.engine.connect() as connection:
        assert connection.execute(text('SELECT count(*) FROM leny.rag_trabajos WHERE account_id=:id'), {'id': context.actor.account_id}).scalar_one() == 2


def test_rag_admission_prevents_second_active_request_for_same_version(rag_context):
    context = rag_context
    source, _, _ = _submit(context)
    from app.services.leny_rag_common import RagError
    with pytest.raises(RagError) as active:
        _submit(context, source)
    assert active.value.code == 'RAG_ALREADY_ACTIVE'
    worker = _worker(context)
    claim = context.service.claim(worker)
    with pytest.raises(RagError) as active:
        _submit(context, source, action='recontextualize')
    assert active.value.code == 'RAG_ALREADY_ACTIVE'
    context.service.fail(claim, 'RAG_OPERATION_FAILED')


def test_rag_worker_cannot_claim_second_job_until_first_finishes(rag_context):
    context = rag_context
    _submit(context)
    _submit(context)
    worker = _worker(context)
    first = context.service.claim(worker)
    assert first is not None
    assert context.service.claim(worker) is None
    context.service.fail(first, 'RAG_OPERATION_FAILED')
    assert context.service.claim(worker) is not None


@pytest.mark.parametrize('change', ['password', 'account', 'role', 'user'])
def test_rag_revoked_actor_invalidates_queued_job_before_claim(rag_context, change):
    context = rag_context
    _, data, _ = _submit(context)
    worker = _worker(context)
    assignments = {'password': ('cuentas', 'must_change_password=true', context.actor.account_id),
                   'account': ('cuentas', 'is_active=false', context.actor.account_id),
                   'role': ('cuentas', 'rol_id=:role', context.actor.account_id),
                   'user': ('usuarios', 'activo=false', context.actor.user_id)}
    table, assignment, identity = assignments[change]
    with context.cluster.engine.begin() as connection:
        # Table/assignment are fixed test constants, never caller SQL.
        connection.execute(text(f'UPDATE {table} SET {assignment} WHERE id=:id'),
                           {'id': identity, 'role': context.recipient.role_id})
    assert context.service.claim(worker) is None
    assert context.service.get(data.request_id)['status'] == 'invalidated'


def test_rag_revocation_after_claim_blocks_finalization(rag_context):
    context = rag_context
    source, _, _, claim = _claim(context)
    with context.cluster.engine.begin() as connection:
        connection.execute(text('UPDATE cuentas SET is_active=false WHERE id=:id'), {'id': context.actor.account_id})
    from app.services.leny_rag_common import RagError
    with pytest.raises(RagError) as invalid:
        context.service.check(claim['id'], claim['token'])
    assert invalid.value.code == 'RAG_INVALIDATED'
    context.service.fail(claim, invalid.value.code)
    assert _state(context, source[1]).validated_indexation_id is None


def test_rag_fragment_checkpoint_is_repeatable_and_rejects_mutated_text(rag_context):
    context = rag_context
    _, _, _, claim = _claim(context)
    fragments = _fragments(context)
    context.service.fragments(claim, fragments, {'complete': True})
    initial = context.service.pending_fragments(claim['indexation_id'])
    context.service.fragments(claim, fragments, {'complete': True})
    assert context.service.pending_fragments(claim['indexation_id']) == initial
    changed = [dict(fragment) for fragment in fragments]
    changed[0]['text'] = changed[0]['text'].replace('125', '999')
    changed[0]['sha256'] = hashlib.sha256(changed[0]['text'].encode()).hexdigest()
    from app.services.leny_rag_common import RagError
    with pytest.raises(RagError) as damaged:
        context.service.fragments(claim, changed, {'complete': True})
    assert damaged.value.code == 'RAG_INTEGRITY'
    assert context.service.pending_fragments(claim['indexation_id']) == initial


def test_rag_new_fragment_hash_must_match_text(rag_context):
    context = rag_context
    _, _, _, claim = _claim(context)
    fragments = _fragments(context)
    fragments[0]['sha256'] = 'f' * 64
    from app.services.leny_rag_common import RagError
    with pytest.raises(RagError) as invalid:
        context.service.fragments(claim, fragments, {'complete': True})
    assert invalid.value.code == 'RAG_INTEGRITY'
    assert context.service.pending_fragments(claim['indexation_id']) == []


@pytest.mark.parametrize('vectors', [[], [[1.0] * 1023], [[0.0] * 1024], [[float('nan')] + [0.0] * 1023]])
def test_rag_bad_vector_batch_never_persists_partial_values(rag_context, vectors):
    context = rag_context
    _, _, _, claim = _claim(context)
    context.service.fragments(claim, _fragments(context, count=1), {'complete': True})
    rows = context.service.pending_fragments(claim['indexation_id'])
    from app.services.leny_rag_common import RagError
    with pytest.raises(RagError) as invalid:
        context.service.save_vectors(claim, rows, vectors)
    assert invalid.value.code == 'RAG_PROVIDER_RESPONSE'
    assert context.service.pending_fragments(claim['indexation_id']) == rows


def test_rag_vector_checkpoint_is_idempotent_and_cannot_mix_indexations(rag_context):
    context = rag_context
    source, _, _, first = _claim(context)
    context.service.fragments(first, _fragments(context, count=1), {'complete': True})
    first_rows = context.service.pending_fragments(first['indexation_id'])
    context.service.fail(first, 'RAG_OPERATION_FAILED')
    _submit(context, source, action='recontextualize')
    second = context.service.claim(context.workers[0])
    context.service.fragments(second, _fragments(context, count=1), {'complete': True})
    vector = [[1.0] + [0.0] * 1023]
    from app.services.leny_rag_common import RagError
    with pytest.raises(RagError) as mixed:
        context.service.save_vectors(second, first_rows, vector)
    assert mixed.value.code == 'RAG_INTEGRITY'
    rows = context.service.pending_fragments(second['indexation_id'])
    context.service.save_vectors(second, rows, vector)
    context.service.save_vectors(second, rows, vector)
    assert context.service.pending_fragments(second['indexation_id']) == []
    with context.cluster.engine.connect() as connection:
        assert connection.execute(text('SELECT count(*) FROM leny.rag_embeddings WHERE indexation_id=:id'), {'id': second['indexation_id']}).scalar_one() == 1


def test_rag_finish_requires_complete_coverage_and_all_vectors(rag_context):
    context = rag_context
    source, data, _, claim = _claim(context)
    fragments = _fragments(context)
    context.service.fragments(claim, fragments, {'complete': False})
    from app.services.leny_rag_common import RagError
    with pytest.raises(RagError):
        context.service.finish(claim)
    rows = context.service.pending_fragments(claim['indexation_id'])
    context.service.save_vectors(claim, rows[:1], [[1.0] + [0.0] * 1023])
    context.service.fragments(claim, fragments, {'complete': True})
    with pytest.raises(RagError):
        context.service.finish(claim)
    assert _state(context, source[1]).validated_indexation_id is None
    rows = context.service.pending_fragments(claim['indexation_id'])
    context.service.save_vectors(claim, rows, [[1.0] + [0.0] * 1023 for _ in rows])
    context.service.finish(claim)
    assert _state(context, source[1]) == ('pending_publication', claim['indexation_id'])
    assert context.service.get(data.request_id)['status'] == 'completed'
    with context.cluster.engine.connect() as connection:
        assert connection.execute(text('SELECT published_version_id FROM leny.documentos WHERE id=:id'), {'id': source[0]}).scalar_one() is None


def test_rag_failed_recontextualization_preserves_previous_validated_index(rag_context):
    context = rag_context
    source, _, worker, first = _claim(context)
    _complete(context, first)
    from app.services.leny_rag_common import RagError
    with pytest.raises(RagError) as already:
        _submit(context, source)
    assert already.value.code == 'RAG_ALREADY_VALIDATED'
    _submit(context, source, action='recontextualize')
    second = context.service.claim(worker)
    assert second['indexation_id'] != first['indexation_id']
    context.service.fail(second, 'RAG_PROVIDER_TIMEOUT')
    assert _state(context, source[1]) == ('pending_publication', first['indexation_id'])


def test_rag_cancel_queued_is_terminal_and_running_cancels_cooperatively(rag_context):
    context = rag_context
    _, request, _ = _submit(context)
    assert context.service.cancel(context.actor, request.request_id)['status'] == 'cancelled'
    assert context.service.cancel(context.actor, request.request_id)['status'] == 'cancelled'
    _, running, _, claim = _claim(context)
    assert context.service.cancel(context.actor, running.request_id)['cancel_requested']
    from app.services.leny_rag_common import RagError
    with pytest.raises(RagError) as cancelled:
        context.service.check(claim['id'], claim['token'])
    assert cancelled.value.code == 'RAG_CANCELLED'
    context.service.fail(claim, cancelled.value.code)
    assert context.service.get(running.request_id)['status'] == 'cancelled'


def test_rag_provider_marker_can_clear_after_confirmed_cancelled_inference(rag_context):
    context = rag_context
    _, request, worker, claim = _claim(context)
    context.service.heartbeat(worker, claim['id'], claim['token'], provider_inflight=True)
    context.service.cancel(context.actor, request.request_id)
    context.service.fail(claim, 'RAG_CANCELLED')
    # Clearing follows a confirmed HTTP completion/cleanup, even when the job
    # has already dropped its execution token. It must not leave false quarantine.
    context.service.heartbeat(worker, claim['id'], claim['token'], provider_inflight=False)
    with context.cluster.engine.connect() as connection:
        marker = connection.execute(text('SELECT provider_inflight,provider_digest FROM leny.rag_workers WHERE id=:id'), {'id': worker}).one()
    assert marker == (False, None)
    context.service.stopped(worker)
    assert _worker(context) is not None


def test_rag_trash_invalidates_pending_and_blocks_running_activation(rag_context):
    context = rag_context
    source, request, _ = _submit(context)
    with context.service.documents.lock():
        context.service.documents.trash(context.actor, source[0], 1)
    assert context.service.get(request.request_id)['status'] == 'invalidated'
    source, request, _, claim = _claim(context)
    with context.service.documents.lock():
        context.service.documents.trash(context.actor, source[0], 1)
    from app.services.leny_rag_common import RagError
    with pytest.raises(RagError):
        context.service.finish(claim)
    context.service.fail(claim, 'RAG_INVALIDATED')
    assert context.service.get(request.request_id)['status'] == 'invalidated'
    assert _state(context, source[1]).validated_indexation_id is None


def test_rag_purge_retains_request_identity_and_inflight_worker_quarantine(rag_context):
    context = rag_context
    source, request, worker, claim = _claim(context)
    context.service.fragments(claim, _fragments(context), {'complete': True})
    context.service.heartbeat(worker, claim['id'], claim['token'], provider_inflight=True)
    from app.services.leny_rag_service import purge_derived
    with context.service.documents.lock(), context.service.documents.transaction() as db:
        purge_derived(db, source[1])
    result = context.service.get(request.request_id)
    assert result['status'] == 'invalidated' and result['indexation_id'] is None
    assert result['version_id'] is None and result['source_version_id'] == source[1]
    with context.cluster.engine.connect() as connection:
        assert connection.execute(text('SELECT count(*) FROM leny.rag_indexaciones WHERE version_id=:id'), {'id': source[1]}).scalar_one() == 0
        assert connection.execute(text('SELECT provider_inflight FROM leny.rag_workers WHERE id=:id'), {'id': worker}).scalar_one()
    context.service.stopped(worker)
    from app.services.leny_rag_common import RagError
    with pytest.raises(RagError) as quarantined:
        _worker(context)
    assert quarantined.value.code == 'RAG_INFERENCE_UNCERTAIN'
    assert context.service.status()['code'] == 'RAG_INFERENCE_UNCERTAIN'


def test_rag_restart_renews_fencing_token_and_rejects_old_owner(rag_context):
    context = rag_context
    _, _, worker, claim = _claim(context)
    context.service.stopped(worker)
    replacement = _worker(context)
    next_claim = context.service.claim(replacement)
    assert next_claim['id'] == claim['id'] and next_claim['token'] != claim['token']
    from app.services.leny_rag_common import RagError
    with pytest.raises(RagError) as fenced:
        context.service.check(claim['id'], claim['token'])
    assert fenced.value.code == 'RAG_LOCK_LOST'
    context.service.check(next_claim['id'], next_claim['token'])


def test_rag_changed_source_hash_invalidates_before_claim(rag_context):
    context = rag_context
    source, request, _ = _submit(context)
    worker = _worker(context)
    with context.cluster.engine.begin() as connection:
        connection.execute(text('UPDATE leny.documento_versiones SET sha256=:hash WHERE id=:id'), {'hash': 'b' * 64, 'id': source[1]})
    assert context.service.claim(worker) is None
    assert context.service.get(request.request_id)['status'] == 'invalidated'


def test_rag_staging_retention_removes_only_expired_failed_content(rag_context):
    from app.services.leny_rag_service import cleanup_staging

    context = rag_context
    worker = _worker(context)
    source, _, _ = _submit(context)
    validated = context.service.claim(worker)
    _complete(context, validated)
    failed = []
    for _ in range(2):
        _, request, _ = _submit(context)
        claim = context.service.claim(worker)
        context.service.fragments(claim, _fragments(context), {'complete': True})
        pending = context.service.pending_fragments(claim['indexation_id'])
        context.service.save_vectors(claim, pending, [[1.0] + [0.0] * 1023 for _ in pending])
        context.service.fail(claim, 'RAG_PROVIDER_TIMEOUT')
        failed.append((request.request_id, claim['indexation_id']))
    expired_request, expired_index = failed[0]
    with context.cluster.engine.begin() as connection:
        connection.execute(text("UPDATE leny.rag_indexaciones SET updated_at=now()-interval '8 days' WHERE id IN (:old,:valid)"),
                           {'old': expired_index, 'valid': validated['indexation_id']})
    with context.service.documents.lock(), context.service.documents.transaction() as db:
        assert cleanup_staging(db, 7) == 1
    assert _state(context, source[1]) == ('pending_publication', validated['indexation_id'])
    tombstone = context.service.get(expired_request)
    assert tombstone['status'] == 'failed' and tombstone['indexation_id'] is None
    assert context.service.get(failed[1][0])['indexation_id'] == failed[1][1]
    with context.cluster.engine.connect() as connection:
        for table in ('rag_indexaciones', 'rag_fragmentos', 'rag_embeddings'):
            column = 'id' if table == 'rag_indexaciones' else 'indexation_id'
            assert connection.execute(text(f'SELECT count(*) FROM leny.{table} WHERE {column}=:id'),
                                      {'id': expired_index}).scalar_one() == 0
        assert connection.execute(text('SELECT count(*) FROM leny.rag_embeddings WHERE indexation_id=:id'),
                                  {'id': validated['indexation_id']}).scalar_one() == 2
