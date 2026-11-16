"""Library transactions/recovery on the guarded isolated PostgreSQL cluster.

The parser is intentionally simulated: these tests verify real DB/filesystem
coordination and do not claim that their synthetic PDF is a valid document.
"""
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker


PDF = b'%PDF-1.4\nQA_SYNTHETIC_COORDINATION_FIXTURE\n%%EOF\n'


@pytest.fixture
def document_actor(synthetic_recipient):
    from app.services.leny_store import LenyActor
    return LenyActor(synthetic_recipient.account_id, synthetic_recipient.user_id, str(uuid4()))


@pytest.fixture
def document_service(pg_cluster, tmp_path, monkeypatch):
    from app.core.config import settings
    from app.services import leny_document_service as implementation
    root = tmp_path / 'private-library'
    assert not root.resolve().is_relative_to(Path(__file__).resolve().parents[3])
    configuration = settings.model_copy(update={
        'leny_documents_enabled': True, 'leny_documents_root': str(root),
        'leny_documents_min_free_bytes': 0,
    })
    assert make_url(configuration.effective_database_url) == pg_cluster.engine.url
    service = implementation.DocumentService(configuration, sessionmaker(bind=pg_cluster.engine, expire_on_commit=False))
    monkeypatch.setattr(implementation, 'validate_document', lambda *_args: {
        'media_type': 'application/pdf', 'preview_type': None, 'preview_stage_key': None,
    })
    try:
        yield service
    finally:
        service.engine.dispose()


@pytest.fixture
def document_roles(pg_cluster, synthetic_recipient):
    """Only create missing base roles; never mutate existing role policies/status."""
    created = []
    with pg_cluster.engine.begin() as connection:
        for code in ('CAJA', 'INV_TALLER', 'MODISTA'):
            identity = connection.execute(text("""
                INSERT INTO roles(codigo,nombre,activo) VALUES(:code,:name,true)
                ON CONFLICT(codigo) DO NOTHING RETURNING id
            """), {'code': code, 'name': 'QA DOCUMENT ROLE ' + uuid4().hex}).scalar_one_or_none()
            if identity is not None:
                created.append(identity)
    try:
        yield
    finally:
        with pg_cluster.engine.begin() as connection:
            # Release only ACLs owned by this synthetic person before removing
            # fixture-created roles; documents themselves remain for cleanup.
            connection.execute(text("""
                DELETE FROM leny.documento_roles_lectura WHERE document_id IN
                    (SELECT id FROM leny.documentos WHERE created_by=:user)
            """), {'user': synthetic_recipient.user_id})
            connection.execute(text("""
                DELETE FROM leny.carpeta_roles_lectura WHERE folder_id IN
                    (SELECT id FROM leny.carpetas WHERE created_by=:user)
            """), {'user': synthetic_recipient.user_id})
            for identity in created:
                connection.execute(text('DELETE FROM roles WHERE id=:id'), {'id': identity})


def _folder(service, actor, *, roles=(), parent=None, name=None):
    from app.schemas.leny_documents import FolderCreate
    name = name or 'QA ' + uuid4().hex
    response = service.save_folder(actor, FolderCreate(name=name, parent_id=parent, role_codes=list(roles)))
    return next(row['id'] for row in response['items'] if row['name'] == name and row['parent_id'] == parent)


def _upload(service, actor, folder, *, content=PDF, document=None, revision=None):
    from app.schemas.leny_documents import DocumentUpload, VersionUpload
    common = {'request_id': uuid4(), 'sha256': hashlib.sha256(content).hexdigest()}
    data = (VersionUpload(**common, revision=revision) if document else
            DocumentUpload(**common, folder_id=folder, title='QA ' + uuid4().hex))
    stage, replay = service.begin_upload(actor, data, document)
    assert replay is False
    service.storage.path(stage).write_bytes(content)
    return service.complete_upload(actor, data.request_id, stage, 'QA.pdf', '.pdf'), data


def test_document_versions_are_persistent_and_originals_immutable(document_service, document_actor, pg_cluster):
    service, actor = document_service, document_actor
    with service.lock():
        folder = _folder(service, actor)
        first, _ = _upload(service, actor, folder)
        first_version = first['versions'][0]
        other_bytes = PDF + b'VERSION TWO'
        second, _ = _upload(service, actor, folder, document=first['id'], revision=first['revision'], content=other_bytes)
        assert second['revision'] == first['revision'] + 1
        assert [v['number'] for v in second['versions']] == [2, 1]
        assert second['published_version_id'] is None
        assert second['status'] == 'pending_contextualization'
        assert all('storage_key' not in v and 'preview_key' not in v for v in second['versions'])
        with pg_cluster.engine.connect() as connection:
            key = connection.execute(text('SELECT storage_key FROM leny.documento_versiones WHERE id=:id'),
                                     {'id': first_version['id']}).scalar_one()
        assert service.storage.path(key).read_bytes() == PDF
        assert service.versions(first['id'], page=2, page_size=1)['items'][0]['id'] == first_version['id']
    # Content permission/audit is a bounded read and must not require the write
    # lease held during upload. This caught a real HTTP-only regression.
    key, mime, name = service.content(actor, first['id'], first_version['id'])
    assert service.storage.path(key).read_bytes() == PDF
    assert mime == 'application/pdf' and name == 'QA.pdf'
    with service.lock():
        service.trash(actor, second['id'], second['revision'])
    from app.services.leny_document_storage import DocumentError
    with pytest.raises(DocumentError) as hidden:
        service.content(actor, first['id'], first_version['id'])
    assert hidden.value.code == 'DOCUMENT_IN_TRASH'


def test_upload_idempotency_conflicts_and_interrupted_identity(document_service, document_actor):
    from app.schemas.leny_documents import DocumentUpload
    from app.services.leny_document_storage import DocumentError
    service, actor = document_service, document_actor
    with service.lock():
        folder = _folder(service, actor)
        result, data = _upload(service, actor, folder)
        assert service.begin_upload(actor, data) == (result['id'], True)
        different = data.model_copy(update={'title': 'OTHER INTENT'})
        with pytest.raises(DocumentError) as collision:
            service.begin_upload(actor, different)
        assert collision.value.code == 'DOCUMENT_IDEMPOTENCY_CONFLICT'
        pending = DocumentUpload(request_id=uuid4(), sha256=data.sha256, folder_id=folder, title='PENDING')
        stage, _ = service.begin_upload(actor, pending)
        with pytest.raises(DocumentError) as running:
            service.begin_upload(actor, pending)
        assert running.value.code == 'DOCUMENT_REQUEST_IN_PROGRESS'
        service.fail_upload(actor, pending.request_id)
        assert not service.storage.path(stage).exists()
        with pytest.raises(DocumentError) as failed:
            service.begin_upload(actor, pending)
        assert failed.value.code == 'DOCUMENT_REQUEST_INTERRUPTED'


def test_folder_normalization_cycles_and_nonempty_trash(document_service, document_actor):
    from app.schemas.leny_documents import FolderCreate, FolderUpdate
    from app.services.leny_document_storage import DocumentError
    service, actor = document_service, document_actor
    with service.lock():
        name = 'QA ' + uuid4().hex
        root = _folder(service, actor, name=name)
        with pytest.raises(DocumentError) as duplicate:
            service.save_folder(actor, FolderCreate(name=name.upper()))
        assert duplicate.value.code == 'DOCUMENT_FOLDER_DUPLICATE'
        child = _folder(service, actor, parent=root)
        with pytest.raises(DocumentError) as cycle:
            service.save_folder(actor, FolderUpdate(name=name, parent_id=child), root)
        assert cycle.value.code == 'DOCUMENT_FOLDER_CYCLE'
        result, _ = _upload(service, actor, child)
        service.trash(actor, result['id'], result['revision'])
        with pytest.raises(DocumentError) as occupied:
            service.delete_folder(actor, child)
        assert occupied.value.code == 'DOCUMENT_FOLDER_NOT_EMPTY'


def test_acl_copy_move_intersection_and_explicit_broadening(document_service, document_actor, document_roles):
    from app.schemas.leny_documents import DocumentChange, FolderUpdate
    from app.services.leny_document_storage import DocumentError
    service, actor = document_service, document_actor
    with service.lock():
        source = _folder(service, actor, roles=('CAJA', 'INV_TALLER'))
        destination = _folder(service, actor, roles=('INV_TALLER', 'MODISTA'))
        result, _ = _upload(service, actor, source)
        assert result['role_codes'] == ['CAJA', 'INV_TALLER']
        service.save_folder(actor, FolderUpdate(name='CHANGED ' + uuid4().hex, role_codes=['CAJA']), source)
        assert service.detail(result['id'])['role_codes'] == ['CAJA', 'INV_TALLER']
        change = DocumentChange(revision=result['revision'], folder_id=destination)
        preview = service.change_preview(actor, result['id'], change)
        assert preview['role_codes'] == ['INV_TALLER']
        assert preview['broadens'] is False
        moved = service.change(actor, result['id'], change.model_copy(update={'confirmation': preview['token']}))
        assert moved['role_codes'] == ['INV_TALLER']
        wider = DocumentChange(revision=moved['revision'], role_codes=['INV_TALLER', 'MODISTA'])
        with pytest.raises(DocumentError) as unconfirmed:
            service.change(actor, result['id'], wider)
        assert unconfirmed.value.code == 'DOCUMENT_CONFIRMATION_REQUIRED'
        preview = service.change_preview(actor, result['id'], wider)
        assert preview['broadens'] is True
        result = service.change(actor, result['id'], wider.model_copy(update={'confirmation': preview['token']}))
        assert result['role_codes'] == ['INV_TALLER', 'MODISTA']


def test_trash_exact_ten_day_restore_boundary_and_expiry(document_service, document_actor, monkeypatch):
    from app.schemas.leny_documents import DocumentChange
    from app.services import leny_document_service as implementation
    from app.services.leny_document_storage import DocumentError
    service, actor = document_service, document_actor
    instant = datetime(2026, 10, 19, 16, tzinfo=timezone.utc)
    monkeypatch.setattr(implementation, 'now', lambda: instant)
    with service.lock():
        result, _ = _upload(service, actor, _folder(service, actor))
        trashed = service.trash(actor, result['id'], result['revision'])
        assert trashed['purge_after'] - trashed['deleted_at'] == timedelta(days=10)
        instant = trashed['purge_after'] - timedelta(seconds=1)
        change = DocumentChange(revision=trashed['revision'])
        preview = service.change_preview(actor, result['id'], change)
        restored = service.change(actor, result['id'], change.model_copy(update={'confirmation': preview['token']}), restore=True)
        assert restored['state'] == 'active' and restored['deleted_at'] is None
        trashed = service.trash(actor, result['id'], restored['revision'])
        instant = trashed['purge_after']
        change = DocumentChange(revision=trashed['revision'])
        preview = service.change_preview(actor, result['id'], change)
        with pytest.raises(DocumentError) as expired:
            service.change(actor, result['id'], change.model_copy(update={'confirmation': preview['token']}), restore=True)
        assert expired.value.code == 'DOCUMENT_RESTORE_EXPIRED'
        service.expire()
        with pytest.raises(DocumentError) as gone:
            service.detail(result['id'])
        assert gone.value.status == 404


def test_purge_partial_filesystem_failure_is_durable_and_retryable(document_service, document_actor, pg_cluster, monkeypatch):
    from app.schemas.leny_documents import PurgeConfirm, PurgePreview
    from app.services.leny_document_storage import DocumentError
    service, actor = document_service, document_actor
    with service.lock():
        result, _ = _upload(service, actor, _folder(service, actor))
        service.trash(actor, result['id'], result['revision'])
        preview = service.purge_preview(actor, PurgePreview(ids=[result['id']]))
        confirm = PurgeConfirm(confirmation=preview['token'], request_id=uuid4())
        with monkeypatch.context() as fault:
            def fail_remove(_key):
                raise OSError('SIMULATED FILESYSTEM FAILURE')
            fault.setattr(service.storage, 'remove', fail_remove)
            with pytest.raises(OSError):
                service.purge(actor, confirm, result['id'])
        assert service.detail(result['id'])['state'] == 'purging'
        with pg_cluster.engine.connect() as connection:
            assert connection.execute(text('SELECT status FROM leny.documento_operaciones WHERE id=:id'),
                                      {'id': confirm.request_id}).scalar_one() == 'purging'
        service.recover()
        with pytest.raises(DocumentError):
            service.detail(result['id'])
        assert service.purge(actor, confirm, result['id']) == {'purged': 1}


@pytest.mark.parametrize('failure_point', ['after_promotion', 'before_database_commit'])
def test_staged_upload_recovers_without_duplicate_versions(document_service, document_actor, pg_cluster, monkeypatch, failure_point):
    from app.schemas.leny_documents import DocumentUpload
    service, actor = document_service, document_actor
    with service.lock():
        folder = _folder(service, actor)
        data = DocumentUpload(request_id=uuid4(), sha256=hashlib.sha256(PDF).hexdigest(), folder_id=folder, title='RECOVERY')
        stage, _ = service.begin_upload(actor, data)
        service.storage.path(stage).write_bytes(PDF)
        with monkeypatch.context() as fault:
            if failure_point == 'after_promotion':
                promote = service.storage.promote
                def fail_after_move(source, destination):
                    promote(source, destination)
                    raise RuntimeError('SIMULATED INTERRUPTION AFTER RENAME')
                fault.setattr(service.storage, 'promote', fail_after_move)
            else:
                def fail_audit(*_args):
                    raise RuntimeError('SIMULATED INTERRUPTION BEFORE COMMIT')
                fault.setattr(service, 'audit', fail_audit)
            with pytest.raises(RuntimeError):
                service.complete_upload(actor, data.request_id, stage, 'QA.pdf', '.pdf')
        with pg_cluster.engine.connect() as connection:
            operation = connection.execute(text('SELECT status,document_id FROM leny.documento_operaciones WHERE id=:id'),
                                           {'id': data.request_id}).one()
            assert operation.status == 'staged'
            assert connection.execute(text('SELECT count(*) FROM leny.documentos WHERE id=:id'),
                                      {'id': operation.document_id}).scalar_one() == 0
        service.recover()
        result = service.detail(operation.document_id)
        assert result['version_count'] == 1
        assert service.begin_upload(actor, data) == (result['id'], True)
        assert not service.storage.path(stage).exists()


def test_failed_uploads_still_consume_shared_per_user_rate_limit(document_service, document_actor):
    from app.schemas.leny_documents import DocumentUpload
    from app.services.leny_document_storage import DocumentError
    service, actor = document_service, document_actor
    with service.lock():
        folder = _folder(service, actor)
        for _ in range(5):
            data = DocumentUpload(request_id=uuid4(), sha256=hashlib.sha256(PDF).hexdigest(), folder_id=folder, title='FAILED')
            service.begin_upload(actor, data)
            service.fail_upload(actor, data.request_id)
        sixth = DocumentUpload(request_id=uuid4(), sha256=hashlib.sha256(PDF).hexdigest(), folder_id=folder, title='EXCESS')
        with pytest.raises(DocumentError) as limited:
            service.begin_upload(actor, sixth)
        assert limited.value.code == 'DOCUMENT_RATE_LIMITED' and limited.value.status == 429


def test_hash_mismatch_never_creates_document_and_failure_cleans_stage(document_service, document_actor):
    from app.schemas.leny_documents import DocumentUpload, DocumentFilters
    from app.services.leny_document_storage import DocumentError
    service, actor = document_service, document_actor
    with service.lock():
        folder = _folder(service, actor)
        data = DocumentUpload(request_id=uuid4(), sha256=hashlib.sha256(PDF).hexdigest(), folder_id=folder, title='BAD HASH')
        stage, _ = service.begin_upload(actor, data)
        service.storage.path(stage).write_bytes(b'ALTERED')
        with pytest.raises(DocumentError) as mismatch:
            service.complete_upload(actor, data.request_id, stage, 'QA.pdf', '.pdf')
        assert mismatch.value.code == 'DOCUMENT_HASH_MISMATCH'
        service.fail_upload(actor, data.request_id, mismatch.value.code)
        assert not service.storage.path(stage).exists()
        assert service.list_documents(DocumentFilters(folder_id=folder))['total'] == 0


def test_library_lease_rejects_parallel_session_and_releases_after_error(document_service):
    from app.services.leny_document_storage import DocumentError
    service = document_service
    with pytest.raises(RuntimeError):
        with service.lock():
            with pytest.raises(DocumentError) as occupied:
                with service.lock():
                    pytest.fail('A second PostgreSQL session acquired the exclusive lease')
            assert occupied.value.code == 'DOCUMENT_BUSY' and occupied.value.status == 429
            raise RuntimeError('SIMULATED CALLER ERROR')
    with service.lock():
        pass
