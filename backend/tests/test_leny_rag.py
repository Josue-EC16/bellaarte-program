"""RAG contracts and local transport policy without a database or native tools."""
import asyncio
import hashlib
import json
from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.leny_rag import ContextualizationRequest
from app.services.leny_document_storage import DocumentError
from app.services.leny_rag_chunking import fragment_units, normalize_text
from app.services.leny_rag_common import RagError, canonical_hash
from app.services.leny_rag_embeddings import EmbeddingProvider


def config(**overrides):
    return Settings(_env_file=None, **overrides)


class OllamaFixture:
    """Real HTTPX serialization/lifecycle, entirely in-process transport."""
    def __init__(self, settings, *, vectors=None, resident=False, size_vram=0):
        self.settings = settings
        self.vectors = vectors
        self.resident = resident
        self.size_vram = size_vram
        self.digest = settings.leny_rag_model_digest
        self.model_name = settings.leny_rag_model
        self.remote = False
        self.dimension = 1024
        self.requests = []
        self.embed_override = None

    def handle(self, request):
        payload = json.loads(request.content) if request.content else None
        self.requests.append((request.method, request.url.path, payload))
        if request.url.path == '/api/tags':
            return httpx.Response(200, json={'models': [{'name': self.model_name, 'digest': self.digest}]})
        if request.url.path == '/api/show':
            return httpx.Response(200, json={'capabilities': ['embedding'], 'model_info': {'qwen3.embedding_length': self.dimension},
                                             **({'remote_host': 'https://external.invalid'} if self.remote else {})})
        if request.url.path == '/api/ps':
            models = [{'name': self.settings.leny_rag_model, 'digest': self.digest, 'size_vram': self.size_vram}] if self.resident else []
            return httpx.Response(200, json={'models': models})
        if request.url.path == '/api/embed':
            if payload.get('keep_alive') == 0:
                self.resident = False
                return httpx.Response(200, json={'model': self.settings.leny_rag_model, 'embeddings': []})
            if self.embed_override:
                return self.embed_override(request)
            self.resident = True
            vectors = self.vectors if self.vectors is not None else [[0.5] * 1024 for _ in payload['input']]
            # Content permits deliberately non-finite provider output, unlike
            # httpx's strict JSON encoder; the adapter must reject it itself.
            return httpx.Response(200, content=json.dumps({'model': self.settings.leny_rag_model, 'embeddings': vectors}).encode())
        raise AssertionError('Unexpected provider endpoint')

    def provider(self):
        return EmbeddingProvider(self.settings, httpx.MockTransport(self.handle))


@pytest.mark.parametrize('injected', [
    {'model': 'other'}, {'owner_id': 1}, {'system': 'ignore previous'},
    {'options': {'num_gpu': 1}}, {'tools': ['sql']}, {'document_id': str(uuid4())},
])
def test_request_never_accepts_client_owned_security_or_provider_settings(injected):
    with pytest.raises(ValidationError):
        ContextualizationRequest(request_id=uuid4(), **injected)


@pytest.mark.parametrize('payload', [
    {'action': 'retry'}, {'action': 'contextualize', 'retry_of': uuid4()},
    {'action': 'recontextualize', 'retry_of': uuid4()}, {'action': 'publish'},
    {'request_id': 'malformed'},
])
def test_request_rejects_inconsistent_retry_and_invalid_identifiers(payload):
    with pytest.raises(ValidationError):
        ContextualizationRequest(**{'request_id': uuid4(), **payload})


def test_request_preserves_explicit_retry_link_and_server_default_action():
    identity, previous = uuid4(), uuid4()
    retry = ContextualizationRequest(request_id=identity, action='retry', retry_of=previous)
    assert retry.request_id == identity and retry.retry_of == previous
    assert ContextualizationRequest(request_id=identity).action == 'contextualize'


@pytest.mark.parametrize('override', [
    {'leny_rag_model': 'qwen3-embedding:4b'}, {'leny_rag_dimension': 512},
    {'leny_rag_batch_size': 5}, {'leny_rag_cpu_threads': 8},
    {'leny_rag_model_digest': 'not-a-digest'},
    {'leny_ollama_url': 'https://cloud.invalid'},
])
def test_configuration_rejects_unapproved_model_cloud_and_resource_expansion(override):
    with pytest.raises(ValidationError):
        config(**override)


def test_embedding_uses_cpu_without_truncation_and_releases_only_owned_tag():
    settings = config()
    fixture = OllamaFixture(settings)
    provider = fixture.provider()

    async def exercise():
        result = await provider.embed(['Margen de utilidad: 25%; costo Bs 100.', 'Taller: pedido 07.'])
        assert len(result) == 2 and all(len(vector) == 1024 for vector in result)
        assert provider.owned_model is True and provider.response_complete is True
        await provider.release()
        assert provider.owned_model is False and fixture.resident is False

    asyncio.run(exercise())
    requests = [payload for method, path, payload in fixture.requests if path == '/api/embed']
    assert requests[0]['truncate'] is False
    assert requests[0]['model'] == settings.leny_rag_model
    assert requests[0]['options'] == {'num_gpu': 0, 'num_thread': 4, 'num_ctx': 4096}
    assert requests[0]['input'][0] == 'Margen de utilidad: 25%; costo Bs 100.'
    assert requests[1] == {'model': settings.leny_rag_model, 'input': [], 'keep_alive': 0}
    assert not any(path == '/api/generate' or path == '/api/chat' for _, path, _ in fixture.requests)


def test_release_without_ownership_does_not_even_contact_or_unload_ollama():
    fixture = OllamaFixture(config(), resident=True)
    asyncio.run(fixture.provider().release())
    assert fixture.resident is True and fixture.requests == []


@pytest.mark.parametrize('change,code', [
    ('missing', 'RAG_MODEL_MISSING'), ('digest', 'RAG_MODEL_CHANGED'),
    ('remote', 'RAG_MODEL_CHANGED'), ('dimension', 'RAG_PROVIDER_RESPONSE'),
    ('resident', 'RAG_EXTERNAL_MODEL'),
])
def test_embedding_preflight_rejects_wrong_identity_dimension_and_external_residency(change, code):
    fixture = OllamaFixture(config())
    if change == 'missing': fixture.model_name = 'qwen3-embedding:4b'
    if change == 'digest': fixture.digest = '0' * 64
    if change == 'remote': fixture.remote = True
    if change == 'dimension': fixture.dimension = 768
    if change == 'resident': fixture.resident = True
    with pytest.raises(RagError) as failure:
        asyncio.run(fixture.provider().embed(['Información empresarial']))
    assert failure.value.code == code
    assert not any(path == '/api/embed' for _, path, _ in fixture.requests)


@pytest.mark.parametrize('vram', [None, 1, 1024**3])
def test_embedding_rejects_unconfirmed_cpu_residency_after_inference(vram):
    fixture = OllamaFixture(config(), size_vram=vram)
    provider = fixture.provider()
    with pytest.raises(RagError) as failure:
        asyncio.run(provider.embed(['Inventario empresarial']))
    assert failure.value.code == 'RAG_CPU_REQUIRED'
    assert provider.response_complete is True and provider.owned_model is True


@pytest.mark.parametrize('vectors', [
    [], [[1.0] * 1024, [1.0] * 1024], [[1.0] * 1023], [[1.0] * 1025],
    [[0] * 1024], [[True] + [1] * 1023], [['1'] + [1] * 1023],
    [[float('nan')] + [1] * 1023], [[float('inf')] + [1] * 1023],
    [[-float('inf')] + [1] * 1023], [None], {'vector': [1] * 1024},
])
def test_embedding_rejects_invalid_cardinality_shape_and_nonfinite_output(vectors):
    fixture = OllamaFixture(config(), vectors=vectors)
    provider = fixture.provider()
    with pytest.raises(RagError) as failure:
        asyncio.run(provider.embed(['Costos de confección']))
    assert failure.value.code == 'RAG_PROVIDER_RESPONSE'
    assert provider.owned_model is True


@pytest.mark.parametrize('texts', [[], [''], [' \n\t'], ['a', 'b', 'c'], [None], ['😀' * 769]])
def test_embedding_input_limits_reject_before_contacting_ollama(texts):
    fixture = OllamaFixture(config())
    with pytest.raises(RagError) as failure:
        asyncio.run(fixture.provider().embed(texts))
    assert failure.value.code == 'RAG_INPUT_CONTEXT'
    assert failure.value.status == 422
    assert fixture.requests == []


@pytest.mark.parametrize('kind,code,uncertain', [
    ('http', 'RAG_PROVIDER_UNAVAILABLE', False),
    ('json_error', 'RAG_PROVIDER_RESPONSE', False),
    ('malformed', 'RAG_PROVIDER_UNAVAILABLE', False),
    ('timeout', 'RAG_PROVIDER_TIMEOUT', True),
    ('connect', 'RAG_PROVIDER_UNAVAILABLE', True),
    ('context', 'RAG_INPUT_CONTEXT', False),
])
def test_provider_errors_never_echo_secret_payloads_and_distinguish_uncertain_inference(kind, code, uncertain):
    secret = 'C:/private/token=synthetic-secret-document'
    fixture = OllamaFixture(config())
    def fail(request):
        if kind == 'timeout': raise httpx.ReadTimeout(secret, request=request)
        if kind == 'connect': raise httpx.ConnectError(secret, request=request)
        if kind == 'http': return httpx.Response(500, text=secret)
        if kind == 'context': return httpx.Response(400, text=secret)
        if kind == 'malformed': return httpx.Response(200, text=secret)
        return httpx.Response(200, json={'error': secret})
    fixture.embed_override = fail
    with pytest.raises(RagError) as failure:
        asyncio.run(fixture.provider().embed(['Texto empresarial']))
    assert failure.value.code == code and failure.value.uncertain is uncertain
    assert secret not in str(failure.value) and secret not in failure.value.message


def test_digest_identity_allows_explicit_sha256_prefix_without_changing_approved_hash():
    fixture = OllamaFixture(config())
    fixture.digest = 'sha256:' + fixture.digest
    assert asyncio.run(fixture.provider().verify())['dimension'] == 1024


def unit(text, source_type='DOCX_PARAGRAPH', **locator):
    return {'text': text, 'source_type': source_type, 'locator': locator or {'paragraph': 1}}


def test_unicode_fragmentation_is_deterministic_bounded_and_reconstructible_by_provenance():
    text = ('Confeccio\u0301n Bs 1.250,50; margen 25%\tPED-007 😀\r\n' * 100)
    settings = config(leny_rag_chunk_target=100, leny_rag_chunk_chars=200, leny_rag_chunk_bytes=1024, leny_rag_overlap_chars=20)
    inputs = [unit(text, 'PDF_TEXT', page=3)]
    chunks = fragment_units(inputs, settings)
    assert chunks == fragment_units(inputs, settings)
    normalized = normalize_text(text)
    coverage = set()
    for ordinal, chunk in enumerate(chunks):
        start, end = chunk['locator']['start'], chunk['locator']['end']
        assert chunk['ordinal'] == ordinal
        assert chunk['text'] == normalized[start:end]
        assert chunk['locator']['page'] == 3 and chunk['locator']['unit'] == 0
        assert chunk['locator']['offset_basis'] == 'NFC_CHARACTERS'
        assert chunk['char_count'] <= 200 and chunk['byte_count'] <= 1024
        assert chunk['sha256'] == hashlib.sha256(chunk['text'].encode()).hexdigest()
        coverage.update(range(start, end))
    assert all(index in coverage for index, char in enumerate(normalized) if not char.isspace())
    joined = ''.join(item['text'] for item in chunks)
    assert '1.250,50' in joined and '25%' in joined and 'PED-007' in joined and 'Confección' in joined
    assert inputs[0]['locator'] == {'page': 3}


def test_multibyte_text_obeys_context_byte_limit_without_losing_forward_progress():
    settings = config(leny_rag_chunk_target=1600, leny_rag_chunk_chars=2000, leny_rag_chunk_bytes=1024)
    text = '😀' * 3000
    chunks = fragment_units([unit(text, 'IMAGE_OCR', image=1)], settings)
    assert len(chunks) > 1
    assert all(chunk['byte_count'] <= 1024 for chunk in chunks)
    assert chunks[0]['locator']['start'] == 0 and chunks[-1]['locator']['end'] == len(text)
    assert all(left['locator']['start'] < right['locator']['start'] for left, right in zip(chunks, chunks[1:]))


def test_equal_text_at_distinct_sources_is_preserved_with_real_docx_locations():
    text = 'Stock\tCódigo 001\tBs 50,00\nTOTAL\t2\tBs 100,00'
    chunks = fragment_units([unit(text, 'DOCX_TABLE', table=2, row=1), unit(text, 'DOCX_TABLE', table=4, row=1)], config())
    assert len(chunks) == 2 and chunks[0]['sha256'] == chunks[1]['sha256']
    assert [chunk['locator']['table'] for chunk in chunks] == [2, 4]
    assert all('page' not in chunk['locator'] for chunk in chunks)
    assert all(chunk['text'] == text for chunk in chunks)


@pytest.mark.parametrize('units,settings,code', [
    ([unit('x' * 1100)], {'leny_rag_max_text_bytes': 1024}, 'RAG_TEXT_LIMIT'),
    ([unit('x' * 1100)], {'leny_rag_chunk_target': 100, 'leny_rag_chunk_chars': 200, 'leny_rag_max_chunks': 1}, 'RAG_FRAGMENT_LIMIT'),
    ([unit(' \n\t')], {}, 'RAG_NO_TEXT'),
    ([unit('text', 'UNTRUSTED_ROLE')], {}, 'RAG_EXTRACTION_INVALID'),
    ([{'text': 'text', 'source_type': 'PDF_TEXT', 'locator': 'page 1'}], {}, 'RAG_EXTRACTION_INVALID'),
])
def test_fragmentation_fails_explicitly_instead_of_silently_truncating(units, settings, code):
    with pytest.raises(DocumentError) as failure:
        fragment_units(units, config(**settings))
    assert failure.value.code == code


def test_policy_fingerprint_ignores_mapping_order_but_tracks_meaningful_changes():
    first = {'model': 'qwen3-embedding:0.6b', 'pipeline': {'cpu_only': True, 'dimension': 1024}}
    assert canonical_hash(first) == canonical_hash({'pipeline': {'dimension': 1024, 'cpu_only': True}, 'model': 'qwen3-embedding:0.6b'})
    assert canonical_hash(first) != canonical_hash({**first, 'dimension': 512})


# Exercise real JWT dependencies, Casbin and document_actor. Only business work
# is stubbed; fake sessions cannot connect to PostgreSQL or commit real data.
@pytest.fixture
def rag_api(monkeypatch):
    from pathlib import Path
    from types import SimpleNamespace
    from unittest.mock import Mock
    import casbin
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.routers import leny_contextualizations as api
    from app.api.routers import leny_documents as document_api
    from app.core.database import get_db
    from app.core.security import create_access_token
    from app.deps import auth

    monkeypatch.setattr(document_api.settings, 'leny_documents_enabled', True)
    model = Path(__file__).resolve().parents[1] / 'app/security/model.conf'
    enforcer = casbin.Enforcer(str(model))
    enforcer.add_policy('ADMIN', 'leny:admin', 'use')
    account = SimpleNamespace(id=12, usuario_id=34, username='synthetic-admin', is_active=True,
                              rol=SimpleNamespace(codigo='ADMIN', activo=True), must_change_password=False,
                              usuario=SimpleNamespace(id=34, activo=True))
    db = Mock()
    db.execute.return_value.scalar_one_or_none.return_value = account
    doc_id, version_id, job_id = uuid4(), uuid4(), uuid4()
    job = dict(id=job_id, document_id=doc_id, version_id=version_id,
               source_document_id=doc_id, source_version_id=version_id,
               status='queued', stage='queued', progress={}, attempts=0,
               cancel_requested=False, indexation_id=None, retry_of=None,
               error_code=None, safe_message=None, created_at='2026-10-20T01:00:00Z',
               updated_at='2026-10-20T01:00:00Z', finished_at=None,
               model='qwen3-embedding:0.6b', dimension=1024)
    service = Mock()
    service.submit.return_value = (job, True)
    service.history.return_value = dict(items=[job], total=1, page=1, page_size=5)
    service.get.return_value = job
    service.cancel.return_value = {**job, 'cancel_requested': True}
    service.status.return_value = dict(enabled=True, ready=True, worker_available=True,
                                      model='qwen3-embedding:0.6b', dimension=1024, cpu_only=True,
                                      dependencies={'vector': True, 'ocr': True}, code=None, message=None)
    app = FastAPI()
    app.include_router(api.router, prefix='/leny')
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[auth.get_enforcer] = lambda: enforcer
    app.dependency_overrides[api.get_rag_service] = lambda: service
    headers = {'Authorization': 'Bearer ' + create_access_token(subject=str(account.id), role_code='ADMIN')}
    routes = [
        ('POST', f'/leny/documents/{doc_id}/versions/{version_id}/contextualizations'),
        ('GET', f'/leny/documents/{doc_id}/versions/{version_id}/contextualizations'),
        ('GET', f'/leny/contextualizations/{job_id}'),
        ('POST', f'/leny/contextualizations/{job_id}/cancel'),
        ('GET', '/leny/admin/rag/status'),
    ]
    with TestClient(app) as client:
        yield SimpleNamespace(client=client, app=app, account=account, enforcer=enforcer, db=db,
                              service=service, routes=routes, headers=headers, job=job)


@pytest.mark.parametrize('route', range(5))
def test_rag_routes_require_real_access_authentication_before_business_work(rag_api, route):
    method, path = rag_api.routes[route]
    result = rag_api.client.request(method, path, json={'model': 'privileged-secret'})
    assert result.status_code == 401
    assert 'privileged-secret' not in result.text
    assert not rag_api.service.mock_calls
    rag_api.db.execute.assert_not_called()


@pytest.mark.parametrize('route', range(5))
def test_rag_routes_require_casbin_permission_before_business_work(rag_api, route):
    rag_api.enforcer.remove_policy('ADMIN', 'leny:admin', 'use')
    method, path = rag_api.routes[route]
    result = rag_api.client.request(method, path, headers=rag_api.headers)
    assert result.status_code == 403
    assert not rag_api.service.mock_calls


@pytest.mark.parametrize('role', ['CAJA', 'INV_BOUTIQUE', 'INV_TALLER', 'MODISTA', 'DOC'])
@pytest.mark.parametrize('route', range(5))
def test_rag_routes_deny_non_admin_even_when_casbin_permission_is_manipulated(rag_api, role, route):
    rag_api.account.rol.codigo = role
    rag_api.enforcer.add_policy(role, 'leny:admin', 'use')
    method, path = rag_api.routes[route]
    result = rag_api.client.request(method, path, headers=rag_api.headers)
    assert result.status_code == 403
    assert not rag_api.service.mock_calls
    rag_api.db.close.assert_called_once()


@pytest.mark.parametrize('restriction', ['account_disabled', 'user_disabled', 'role_disabled', 'password_change', 'wrong_owner', 'no_individual'])
def test_rag_routes_require_enabled_individual_account(rag_api, restriction):
    if restriction == 'account_disabled': rag_api.account.is_active = False
    if restriction == 'user_disabled': rag_api.account.usuario.activo = False
    if restriction == 'role_disabled': rag_api.account.rol.activo = False
    if restriction == 'password_change': rag_api.account.must_change_password = True
    if restriction == 'wrong_owner': rag_api.account.usuario.id = 999
    if restriction == 'no_individual':
        # The global auth service assumes its persisted relationship exists.
        # Isolate that upstream assumption to exercise the library's additional
        # individual-ownership guard, without weakening it or mocking the actor.
        from app.deps import auth
        rag_api.account.usuario = None
        rag_api.app.dependency_overrides[auth.get_current_account] = lambda: rag_api.account
    result = rag_api.client.get('/leny/admin/rag/status', headers=rag_api.headers)
    assert result.status_code == 403
    assert not rag_api.service.mock_calls


@pytest.mark.parametrize('field', ['model', 'owner_id', 'system', 'tools', 'options'])
def test_rag_admission_rejects_privileged_fields_without_reflecting_input(rag_api, field):
    method, path = rag_api.routes[0]
    result = rag_api.client.request(method, path, headers=rag_api.headers,
                                    json={'request_id': str(uuid4()), field: 'synthetic-internal-secret'})
    assert result.status_code == 422
    assert result.json()['detail']['code'] == 'DOCUMENT_INVALID_INPUT'
    assert 'synthetic-internal-secret' not in result.text
    rag_api.service.submit.assert_not_called()


@pytest.mark.parametrize('route', [0, 3])
def test_rag_json_body_size_is_bounded_before_mutation(rag_api, route):
    method, path = rag_api.routes[route]
    result = rag_api.client.request(method, path, headers=rag_api.headers,
                                    content=json.dumps({'oversized': 'secret' * 3000}))
    assert result.status_code == 413
    assert result.json()['detail']['code'] == 'DOCUMENT_BODY_LIMIT'
    assert 'secret' not in result.text
    assert not rag_api.service.mock_calls


def test_rag_rate_limit_returns_safe_retry_after_without_running_a_job(rag_api):
    rag_api.service.submit.side_effect = RagError('RAG_RATE_LIMITED', 429)
    method, path = rag_api.routes[0]
    result = rag_api.client.request(method, path, headers=rag_api.headers,
                                    json={'request_id': str(uuid4())})
    assert result.status_code == 429
    assert result.json()['detail']['code'] == 'RAG_RATE_LIMITED'
    assert int(result.headers['Retry-After']) > 0


def test_rag_cancel_bounds_chunked_body_without_content_length(rag_api):
    method, path = rag_api.routes[3]

    def chunks():
        yield b'{"oversized":"'
        yield b'x' * 17000
        yield b'"}'

    response = rag_api.client.request(method, path, headers=rag_api.headers, content=chunks())
    assert response.status_code == 413
    assert response.json()['detail']['code'] == 'DOCUMENT_BODY_LIMIT'
    rag_api.service.cancel.assert_not_called()


def test_authorized_rag_transport_preserves_backend_identity_and_response_contract(rag_api):
    request_id = uuid4()
    method, path = rag_api.routes[0]
    result = rag_api.client.request(method, path, headers=rag_api.headers,
                                    json={'request_id': str(request_id)})
    assert result.status_code == 202
    actor, document_id, version_id, data = rag_api.service.submit.call_args.args
    assert (actor.account_id, actor.user_id) == (12, 34)
    assert str(document_id) == str(rag_api.job['document_id'])
    assert str(version_id) == str(rag_api.job['version_id']) and data.request_id == request_id
    assert result.json()['status'] == 'queued' and result.json()['dimension'] == 1024
    rag_api.service.submit.return_value = (rag_api.job, False)
    replay = rag_api.client.request(method, path, headers=rag_api.headers, json={'request_id': str(request_id)})
    assert replay.status_code == 200 and replay.json()['id'] == result.json()['id']
    for method, path in rag_api.routes[1:]:
        response = rag_api.client.request(method, path, headers=rag_api.headers,
                                         **({'json': {}} if method == 'POST' else {}))
        assert response.status_code == 200
        assert 'C:\\' not in response.text and 'storage_key' not in response.text and 'embedding' not in response.json()
    assert rag_api.service.status.call_count == 1
    assert rag_api.db.close.call_count == 6
