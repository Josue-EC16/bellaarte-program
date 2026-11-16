"""Private-library transport security, with no application startup or database."""
import asyncio
from contextlib import contextmanager
import hashlib
import io
import json
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import anyio
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest
from sqlalchemy.exc import OperationalError
from starlette.requests import Request

from app.api.routers import leny_documents as api
from app.schemas.leny_documents import DocumentChange, DocumentUpload, FolderCreate, VersionUpload
from app.services.leny_document_storage import DocumentError
from app.services.leny_store import LenyActor


class FakeLease:
    def __init__(self):
        self.closed = False

    def check(self):
        assert not self.closed

    def close(self):
        self.closed = True


class FakeService:
    def __init__(self, root):
        self.settings = SimpleNamespace(leny_documents_image_bytes=32, leny_documents_max_file_bytes=64)
        self.root = root
        self.storage = SimpleNamespace(path=lambda key: root / key)
        self.lease = FakeLease()
        self.begin_calls, self.complete_calls, self.fail_calls = [], [], []
        self.document_id = uuid4()
        self.duplicate = False
        self.fail_error = None

    def acquire(self):
        return self.lease

    def run_leased(self, lease, function, *args):
        lease.check()
        return function(*args)

    @contextmanager
    def lock(self):
        yield self.lease

    def recover(self):
        pass

    def begin_upload(self, actor, data, document_id):
        self.begin_calls.append((actor, data, document_id))
        return (self.document_id, True) if self.duplicate else ('stage.bin', False)

    def complete_upload(self, actor, request_id, stage, name, extension):
        self.complete_calls.append((actor, request_id, stage, name, extension))
        return {'id': str(self.document_id), 'state': 'ACTIVO'}

    def fail_upload(self, actor, request_id, code='DOCUMENT_UPLOAD_INTERRUPTED'):
        self.fail_calls.append(request_id)
        if self.fail_error:
            raise self.fail_error

    def detail(self, identity):
        assert identity == self.document_id
        return {'id': str(identity), 'state': 'ACTIVO'}

    def list_documents(self, filters, trash=False):
        return {'items': [], 'page': filters.page, 'trash': trash}


@pytest.fixture
def transport(tmp_path):
    service = FakeService(tmp_path)
    actor = LenyActor(12, 34, str(uuid4()))
    app = FastAPI()
    app.include_router(api.router, prefix='/documents')
    app.dependency_overrides[api.document_actor] = lambda: actor
    app.dependency_overrides[api.get_document_service] = lambda: service
    return SimpleNamespace(app=app, service=service, actor=actor, client=TestClient(app))


def metadata(**updates):
    value = dict(request_id=str(uuid4()), sha256=hashlib.sha256(b'PDF').hexdigest(),
                 folder_id=str(uuid4()), title='Procedimiento de inventario')
    value.update(updates)
    return value


def multipart(data=None, filename='procedure.pdf', payload=b'PDF', extra=b'', complete=True):
    boundary = b'qa-private-library'
    first = b'--' + boundary + b'\r\nContent-Disposition: form-data; name="metadata"\r\n\r\n'
    second = b'\r\n--' + boundary + b'\r\nContent-Disposition: form-data; name="file"; filename="'
    body = first + json.dumps(data or metadata()).encode() + second + filename.encode() + b'"\r\nContent-Type: application/pdf\r\n\r\n' + payload + extra
    if complete:
        body += b'\r\n--' + boundary + b'--\r\n'
    return body, {'content-type': 'multipart/form-data; boundary=' + boundary.decode()}


async def asgi_request(app, receive, *, method='POST', path='/documents', headers=()):
    sent = []

    async def send(message):
        sent.append(message)

    scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1', 'method': method,
             'scheme': 'http', 'path': path, 'raw_path': path.encode(), 'query_string': b'',
             'headers': list(headers), 'client': ('127.0.0.1', 50000), 'server': ('test', 80), 'root_path': ''}
    await app(scope, receive, send)
    return sent


@pytest.mark.parametrize('path', ['/documents', '/documents/folders', '/documents/' + str(uuid4()) + '/versions'])
@pytest.mark.parametrize('status', [401, 403])
def test_authorization_rejects_before_body_is_received(transport, path, status):
    def deny():
        raise HTTPException(status, 'Acceso denegado')

    transport.app.dependency_overrides[api.document_actor] = deny

    async def receive():
        pytest.fail('Unauthorized upload must never consume a body chunk')

    sent = anyio.run(lambda: asgi_request(transport.app, receive, path=path,
                                         headers=[(b'content-length', b'999999999')]))
    assert sent[0]['status'] == status
    assert not transport.service.begin_calls


def test_upload_streams_single_file_and_releases_lease(transport):
    data = metadata()
    body, headers = multipart(data)
    result = transport.client.post('/documents', content=body, headers=headers)
    assert result.status_code == 200
    assert transport.service.root.joinpath('stage.bin').read_bytes() == b'PDF'
    assert len(transport.service.complete_calls) == 1
    assert str(transport.service.complete_calls[0][1]) == data['request_id']
    assert transport.service.lease.closed


def test_existing_document_uses_version_contract(transport):
    identity = uuid4()
    body, headers = multipart(dict(request_id=str(uuid4()), sha256='a' * 64, revision=2))
    result = transport.client.post(f'/documents/{identity}/versions', content=body, headers=headers)
    assert result.status_code == 200
    assert transport.service.begin_calls[0][2] == identity
    assert isinstance(transport.service.begin_calls[0][1], VersionUpload)


@pytest.mark.parametrize('filename', ['../secret.pdf', 'C:\\private.pdf', '/absolute.pdf', 'bad:name.pdf', 'bad\x00.pdf'])
def test_upload_rejects_path_or_control_characters_in_filename(transport, filename):
    body, headers = multipart(filename=filename)
    response = transport.client.post('/documents', content=body, headers=headers)
    assert response.status_code == 422
    assert response.json()['detail']['code'] == 'DOCUMENT_FILENAME_INVALID'
    assert not transport.service.complete_calls
    assert not transport.service.root.joinpath('stage.bin').exists()
    assert transport.service.lease.closed


@pytest.mark.parametrize('filename', ['executable.exe', 'macro.docm', 'old.doc', 'active.svg', 'page.html'])
def test_upload_rejects_unsupported_extensions(transport, filename):
    body, headers = multipart(filename=filename)
    response = transport.client.post('/documents', content=body, headers=headers)
    assert response.status_code == 415
    assert not transport.service.complete_calls
    assert transport.service.lease.closed


@pytest.mark.parametrize('filename,size', [('procedure.pdf', 65), ('image.png', 33)])
def test_independent_file_size_limits_without_content_length(transport, filename, size):
    body, headers = multipart(filename=filename, payload=b'x' * size)
    # An iterator produces chunked transport, without a Content-Length header.
    response = transport.client.post('/documents', content=iter([body]), headers=headers)
    assert response.status_code == 413
    assert response.json()['detail']['code'] == 'DOCUMENT_SIZE_LIMIT'
    assert not transport.service.complete_calls
    assert transport.service.lease.closed


def test_whole_body_limit_is_enforced(transport, monkeypatch):
    monkeypatch.setattr(api.settings, 'leny_documents_max_body_bytes', 100)
    body, headers = multipart()
    response = transport.client.post('/documents', content=body, headers=headers)
    assert response.status_code == 413
    assert response.json()['detail']['code'] == 'DOCUMENT_BODY_LIMIT'
    assert not transport.service.begin_calls
    assert transport.service.lease.closed


def test_metadata_size_limit_precedes_service_mutation(transport):
    body, headers = multipart(metadata(description='x' * 17000))
    response = transport.client.post('/documents', content=body, headers=headers)
    assert response.status_code == 413
    assert not transport.service.begin_calls
    assert transport.service.lease.closed


@pytest.mark.parametrize('payload,content_type', [
    (b'invalid', 'application/json'),
    (b'invalid', 'multipart/form-data'),
    (b'broken\r\n', 'multipart/form-data; boundary=expected'),
])
def test_malformed_multipart_has_safe_error(transport, payload, content_type):
    response = transport.client.post('/documents', content=payload, headers={'content-type': content_type})
    assert response.status_code == 422
    assert response.json()['detail']['code'] == 'DOCUMENT_MULTIPART_INVALID'
    assert not transport.service.complete_calls


def test_missing_metadata_is_not_accepted(transport):
    body, headers = multipart()
    body = body.replace(b'name="metadata"', b'name="unexpected"', 1)
    response = transport.client.post('/documents', content=body, headers=headers)
    assert response.status_code == 422
    assert not transport.service.begin_calls
    assert transport.service.lease.closed


@pytest.mark.parametrize('payload,complete', [(b'', True), (b'PDF', False)])
def test_empty_or_truncated_file_is_never_completed(transport, payload, complete):
    body, headers = multipart(payload=payload, complete=complete)
    response = transport.client.post('/documents', content=body, headers=headers)
    assert response.status_code == 422
    assert not transport.service.complete_calls
    assert transport.service.fail_calls
    assert transport.service.lease.closed


def test_second_file_is_rejected(transport):
    extra = b'\r\n--qa-private-library\r\nContent-Disposition: form-data; name="file"; filename="other.pdf"\r\n\r\nSECOND'
    body, headers = multipart(extra=extra)
    response = transport.client.post('/documents', content=body, headers=headers)
    assert response.status_code == 422
    assert not transport.service.complete_calls
    assert transport.service.lease.closed


def test_duplicate_request_replays_without_file_write_or_generation(transport):
    transport.service.duplicate = True
    body, headers = multipart()
    response = transport.client.post('/documents', content=body, headers=headers)
    assert response.status_code == 200
    assert response.json()['id'] == str(transport.service.document_id)
    assert not transport.service.complete_calls
    assert not transport.service.root.joinpath('stage.bin').exists()
    assert transport.service.lease.closed


def test_disconnect_closes_file_and_lease_when_failure_recording_also_fails(transport):
    transport.service.fail_error = OSError('private-storage-path')
    body, headers = multipart(complete=False)
    received = 0

    async def receive():
        nonlocal received
        received += 1
        if received == 1:
            return {'type': 'http.request', 'body': body, 'more_body': True}
        return {'type': 'http.disconnect'}

    encoded_headers = [(key.encode(), value.encode()) for key, value in headers.items()]
    sent = anyio.run(lambda: asgi_request(transport.app, receive, headers=encoded_headers))
    assert sent[0]['status'] == 503
    assert b'private-storage-path' not in b''.join(m.get('body', b'') for m in sent)
    assert transport.service.fail_calls
    assert transport.service.lease.closed
    # Windows refuses an unlink while an unshared write handle remains open.
    transport.service.root.joinpath('stage.bin').unlink()


def test_task_cancellation_releases_lease_even_when_recording_failure_raises(transport):
    transport.service.fail_error = OSError('synthetic cleanup failure')
    body, headers = multipart(complete=False)

    async def stream():
        yield body
        raise asyncio.CancelledError()

    request = SimpleNamespace(headers=headers, stream=stream)

    async def run():
        with pytest.raises(OSError, match='synthetic cleanup failure'):
            await api.receive_upload(request, transport.actor, transport.service)

    anyio.run(run)
    assert transport.service.fail_calls
    assert transport.service.lease.closed
    transport.service.root.joinpath('stage.bin').unlink()


def test_lost_lease_prevents_processing_next_upload_chunk(transport):
    body, headers = multipart()
    before_file = body.index(b'\r\n--qa-private-library', body.index(b'name="metadata"'))
    first = body[:before_file + 2]
    second = body[before_file + 2:]
    previous_check = transport.service.lease.check
    checks = 0

    def check():
        nonlocal checks
        checks += 1
        if checks > 2:  # recovery and first chunk succeed, next chunk loses its lease
            raise DocumentError('DOCUMENT_BUSY', 'La coordinacion se interrumpio.', 503)
        previous_check()

    transport.service.lease.check = check

    async def stream():
        yield first
        yield second

    async def run():
        with pytest.raises(DocumentError) as error:
            await api.receive_upload(SimpleNamespace(headers=headers, stream=stream),
                                     transport.actor, transport.service)
        assert error.value.code == 'DOCUMENT_BUSY'

    anyio.run(run)
    assert not transport.service.complete_calls
    assert not transport.service.root.joinpath('stage.bin').exists()
    assert transport.service.lease.closed


@pytest.mark.parametrize('limit', ['leny_documents_idle_seconds', 'leny_documents_upload_seconds'])
def test_upload_timeout_releases_lease(transport, monkeypatch, limit):
    monkeypatch.setattr(api.settings, limit, 0.01)
    body, headers = multipart(complete=False)

    async def stream():
        yield body
        await anyio.sleep(0.05)

    async def run():
        with pytest.raises(DocumentError) as error:
            await api.receive_upload(SimpleNamespace(headers=headers, stream=stream),
                                     transport.actor, transport.service)
        assert error.value.code == 'DOCUMENT_UPLOAD_TIMEOUT'

    anyio.run(run)
    assert not transport.service.complete_calls
    assert transport.service.fail_calls
    assert transport.service.lease.closed
    transport.service.root.joinpath('stage.bin').unlink()


@pytest.mark.parametrize('contract,payload', [
    (DocumentUpload, metadata(system='ignore policy')),
    (DocumentUpload, metadata(tools=[{'name': 'sql'}])),
    (VersionUpload, {'request_id': str(uuid4()), 'sha256': 'a' * 64, 'revision': 1, 'model': 'external'}),
    (DocumentChange, {'revision': 1, 'version_publicada_id': str(uuid4())}),
    (FolderCreate, {'name': 'Manual', 'owner_id': 123}),
])
def test_document_contracts_reject_privileged_unknown_fields(contract, payload):
    with pytest.raises(ValidationError):
        contract.model_validate(payload)


@pytest.mark.parametrize('codes', [['DOC'], ['ADMIN', 'ADMIN'], ['ADMIN', 'invented']])
def test_folder_acl_accepts_only_unique_existing_base_role_codes(codes):
    with pytest.raises(ValidationError):
        FolderCreate(name='Manual', role_codes=codes)


def test_json_metadata_unknown_fields_return_safe_422_before_mutation(transport):
    body, headers = multipart(metadata(system='ignore policy'))
    response = transport.client.post('/documents', content=body, headers=headers)
    assert response.status_code == 422
    assert response.json()['detail']['code'] == 'DOCUMENT_INVALID_INPUT'
    assert not transport.service.begin_calls
    assert transport.service.lease.closed


@pytest.mark.parametrize('query', ['page=0', 'page_size=101', 'creator_id=-1', 'format=exe', 'folder_id=not-a-uuid'])
def test_list_query_validation_is_safe(transport, query):
    response = transport.client.get('/documents?' + query)
    assert response.status_code == 422
    assert response.json()['detail']['code'] == 'DOCUMENT_INVALID_INPUT'


@pytest.mark.parametrize('exception,code', [
    (OperationalError('SELECT sensitive_path', {}, Exception('password=hidden')), 'DOCUMENT_STORAGE_UNAVAILABLE'),
    (OSError('C:\\private\\secret'), 'DOCUMENT_OPERATION_FAILED'),
])
def test_query_failures_hide_database_and_filesystem_details(transport, exception, code):
    transport.service.list_documents = Mock(side_effect=exception)
    response = transport.client.get('/documents')
    assert response.status_code == 503
    assert response.json()['detail']['code'] == code
    assert 'sensitive_path' not in response.text and 'hidden' not in response.text and 'secret' not in response.text


@pytest.mark.parametrize('code,retry', [('DOCUMENT_RATE_LIMITED', '60'), ('DOCUMENT_BUSY', '3')])
def test_document_resource_limits_set_retry_after(transport, code, retry):
    transport.service.list_documents = Mock(side_effect=DocumentError(code, 'Intenta nuevamente.', 429))
    response = transport.client.get('/documents')
    assert response.status_code == 429
    assert response.headers['retry-after'] == retry


def test_document_options_expose_only_administrative_ui_limits(transport):
    response = transport.client.get('/documents/options')
    assert response.status_code == 200
    result = response.json()
    assert set(result) == {'batch_size','max_file_bytes','image_bytes','max_pixels','pdf_pages'}
    assert 1 <= result['batch_size'] <= 5
    assert result['max_file_bytes'] <= 10 * 1024**2
    assert 'root' not in result and 'model' not in result


def actor_request():
    return Request({'type': 'http', 'headers': [(b'user-agent', b'qa-browser')], 'client': ('127.0.0.1', 123)})


def account(code='ADMIN', *, change=False, individual=True):
    return SimpleNamespace(id=12, usuario_id=34, rol=SimpleNamespace(codigo=code),
                           must_change_password=change, usuario=SimpleNamespace(id=34) if individual else None)


@pytest.mark.parametrize('code', ['CAJA', 'INV_BOUTIQUE', 'INV_TALLER', 'MODISTA', 'DOC'])
def test_document_actor_denies_every_non_admin_even_if_permission_was_granted(code, monkeypatch):
    monkeypatch.setattr(api.settings, 'leny_documents_enabled', True)
    db = Mock()
    with pytest.raises(HTTPException) as error:
        api.document_actor(actor_request(), account(code), db)
    assert error.value.status_code == 403
    db.close.assert_called_once()


@pytest.mark.parametrize('value', [account(change=True), account(individual=False),
                                   SimpleNamespace(id=12, usuario_id=34, rol=SimpleNamespace(codigo='ADMIN'),
                                                   must_change_password=False, usuario=SimpleNamespace(id=99))])
def test_document_actor_requires_personal_account_and_completed_password_change(value, monkeypatch):
    monkeypatch.setattr(api.settings, 'leny_documents_enabled', True)
    db = Mock()
    with pytest.raises(HTTPException) as error:
        api.document_actor(actor_request(), value, db)
    assert error.value.status_code == 403
    db.close.assert_called_once()


def test_document_actor_uses_backend_identity_and_closes_authentication_session(monkeypatch):
    monkeypatch.setattr(api.settings, 'leny_documents_enabled', True)
    db = Mock()
    actor = api.document_actor(actor_request(), account(), db)
    assert actor.account_id == 12 and actor.user_id == 34
    assert actor.ip_address == '127.0.0.1' and actor.user_agent == 'qa-browser'
    db.close.assert_called_once()


def test_disabled_library_rejects_admin_and_closes_session(monkeypatch):
    monkeypatch.setattr(api.settings, 'leny_documents_enabled', False)
    db = Mock()
    with pytest.raises(DocumentError) as error:
        api.document_actor(actor_request(), account(), db)
    assert error.value.code == 'DOCUMENT_LIBRARY_DISABLED'
    assert error.value.status == 503
    db.close.assert_called_once()


def test_publish_requires_explicit_version_index_and_confirmation(transport):
    result = transport.client.post('/documents/' + str(uuid4()) + '/publish')
    assert result.status_code == 422
    assert result.json()['detail']['code'] == 'DOCUMENT_INVALID_INPUT'


def test_authorized_file_response_closes_context_on_send_failure_before_first_chunk():
    handle = io.BytesIO(b'private-document')
    context = Mock()
    context.__exit__ = Mock(side_effect=lambda *_: handle.close())
    response = api.AuthorizedFileResponse(iter([b'private-document']), context)

    async def receive():
        await anyio.sleep_forever()

    async def send(_message):
        raise OSError('browser disconnected before first chunk')

    async def run():
        with pytest.raises(BaseException):
            await response({'type': 'http', 'asgi': {'spec_version': '2.0'}}, receive, send)

    anyio.run(run)
    context.__exit__.assert_called_once()
    assert handle.closed


def test_content_download_has_private_headers_and_releases_file_handle(transport):
    handle = io.BytesIO(b'private-document')

    @contextmanager
    def opened(_key):
        with handle:
            yield handle

    transport.service.storage.open = opened
    transport.service.content = Mock(return_value=('versions/uuid.blob', 'application/pdf', 'manual.pdf'))
    response = transport.client.get(f'/documents/{uuid4()}/versions/{uuid4()}/content')
    assert response.status_code == 200 and response.content == b'private-document'
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert 'sandbox' in response.headers['content-security-policy']
    assert response.headers['content-disposition'].startswith('attachment;')
    assert handle.closed


def test_pdf_preview_only_offers_authenticated_download(transport):
    transport.service.content = Mock(return_value=(None, 'application/pdf', 'manual.pdf'))
    response = transport.client.get(f'/documents/{uuid4()}/versions/{uuid4()}/preview')
    assert response.status_code == 200
    assert response.json()['kind'] == 'download'
    assert response.headers['cache-control'] == 'no-store'
