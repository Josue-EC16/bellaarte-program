"""Service/provider integration with mocks only: no live database or models."""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import httpx
import pytest

from app.core.config import Settings
from app.services.leny_inference_state import ManagedProvider
from app.services.leny_ollama import LenyError, OllamaProvider
from app.services.leny_rag_synthesis import SCHEMA
from test_leny_rag_quality import candidate_service


SOURCE = 'La modista comprueba las medidas antes del corte.'
ANSWER = 'La modista revisa las medidas antes de cortar.'


def environment(monkeypatch, *, enabled=True, message='¿Cómo se hacen los vestidos?'):
    from app.services import leny_rag_common
    env = candidate_service(message)
    if enabled:
        env.service.config.leny_rag_response_mode = 'controlled-synthesis-v1'
    env.service.retrieval, env.service.sources = Mock(), Mock()
    env.service.retrieval.ready.return_value = True
    env.service.retrieval.search.return_value = [dict(fragment_id=uuid4(), text=SOURCE,
        locator={'page': 1}, source_type='PDF_TEXT')]
    env.service.sources.for_messages.return_value = {}
    env.service.embedding_factory = lambda _: SimpleNamespace(embed=AsyncMock(return_value=[[1.0]+[0.0]*1023]),
        owned_model=False, response_complete=True)
    env.provider.classify.return_value = '{"aspect":"general","scope":"matched","relation":"direct","sources":[1]}'
    env.provider.structured = AsyncMock(return_value=json.dumps({'blocks': [dict(kind='documented',
        text=ANSWER, source='S1', support='P1_1')], 'limitation': ''}))
    env.provider.finish_reason = 'stop'
    monkeypatch.setattr(leny_rag_common, 'available_ram', lambda: 4*1024**3)
    return env


def run(env):
    async def collect():
        turn = await env.service.prepare(env.actor, env.payload)
        return turn, [json.loads(event) async for event in turn.events()]
    return asyncio.run(collect())


@pytest.mark.parametrize('enabled', [False, True])
def test_mode_selects_structured_synthesis_or_literal_legacy(monkeypatch, enabled):
    env = environment(monkeypatch, enabled=enabled)
    turn, events = run(env)
    assert events[-1]['type'] == 'done'
    text = ''.join(event.get('text', '') for event in events)
    assert (ANSWER if enabled else SOURCE) in text
    assert env.provider.structured.await_count == int(enabled)
    env.provider.stream.assert_not_called()
    env.lease.close.assert_called_once()


@pytest.mark.parametrize('raw', ['INVALID_PRIVATE_GENERATION', json.dumps({'blocks': [dict(kind='documented',
    text='La asesora revisa las medidas antes de cortar.', source='S1', support=SOURCE)], 'limitation': ''})])
def test_invalid_synthesis_requests_clarification_without_returning_extracts(monkeypatch, raw):
    env = environment(monkeypatch)
    env.provider.structured.return_value = raw
    turn, events = run(env)
    text = ''.join(event.get('text', '') for event in events)
    assert events[-1]['type'] == 'done'
    assert SOURCE not in text and 'INVALID_PRIVATE_GENERATION' not in text
    assert events[-1]['outcome'] == 'clarification'
    assert events[-1]['reason_code'] == 'rag_synthesis_unverified'
    assert not events[-1]['sources']
    env.service.sources.persist.assert_not_called()
    assert turn.diagnostics.counts['synthesis_fallback'] == 1


def test_revocation_after_synthesis_prevents_any_content_emission(monkeypatch):
    env = environment(monkeypatch)
    original = env.provider.structured.return_value
    async def revoke(*_):
        env.service.retrieval.revalidate.side_effect = LenyError('LENY_RAG_SOURCE_REVOKED', 'Fuente no disponible.', 403)
        return original
    env.provider.structured.side_effect = revoke
    turn, events = run(env)
    assert events[-1]['type'] == 'error'
    assert not any(event['type'] == 'delta' for event in events)
    assert turn.content == ''
    assert turn.diagnostics.counts.get('synthesis_fallback', 0) == 0


@pytest.mark.parametrize('code', ['LENY_RAG_MEMORY_LIMIT', 'LENY_INFERENCE_UNCERTAIN', 'LENY_UNAVAILABLE'])
def test_operational_failure_is_not_replaced_with_literal_success(monkeypatch, code):
    env = environment(monkeypatch)
    env.provider.structured.side_effect = LenyError(code, 'Servicio no disponible.', 503)
    turn, events = run(env)
    assert events[-1]['type'] == 'error' and events[-1]['code'] == code
    assert not any(event['type'] == 'delta' for event in events)
    assert turn.diagnostics.counts.get('synthesis_fallback', 0) == 0
    env.lease.close.assert_called_once()


def test_ambiguous_authorized_title_requests_clarification(monkeypatch):
    env = environment(monkeypatch)
    env.service.retrieval.search.side_effect = LenyError('LENY_RAG_TITLE_AMBIGUOUS', 'Referencia ambigua.', 409)
    turn, events = run(env)
    assert events[-1]['type'] == 'done' and events[-1]['outcome'] == 'clarification'
    assert 'Precisa el título' in ''.join(event.get('text', '') for event in events)
    env.provider.structured.assert_not_awaited()


def test_managed_structured_generation_keeps_durable_phase_and_lease():
    provider = SimpleNamespace(config=Settings(_env_file=None), structured=AsyncMock(return_value='{}'),
        response_complete=True, inference_started=False)
    state, lease, request_id = Mock(), Mock(), uuid4()
    state.start.return_value = True
    managed = ManagedProvider(provider, state, lease, request_id, lambda: 10)
    assert asyncio.run(managed.structured([], SCHEMA)) == '{}'
    state.start.assert_called_once_with(lease, request_id, provider.config.leny_model, 'generation')
    state.finish.assert_called_once_with(lease, request_id, True)
    lease.close.assert_not_called()


def test_ollama_structured_request_has_schema_and_generation_budget():
    requests = []
    def transport(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, content=b'{"message":{"content":"{}"},"done":true}\n')
    provider = OllamaProvider(Settings(_env_file=None, leny_rag_profile='rag4_v1'), httpx.MockTransport(transport))
    assert asyncio.run(provider.structured([{'role': 'user', 'content': 'Synthetic'}], SCHEMA)) == '{}'
    request = requests[0]
    assert request['format'] == SCHEMA
    assert request['options']['num_predict'] == 768 and request['options']['num_ctx'] == 4096
    assert request['options']['temperature'] == 0
    assert request['truncate'] is False and request['shift'] is False


@pytest.mark.parametrize('message', ['¿Qué es el margen de utilidad?',
    'Actualmente quiero hacer un manual, pero no sé de dónde comenzar',
    'Quiero un ejemplo de cómo iniciar un manual'])
def test_advice_and_drafting_search_before_giving_general_guidance(monkeypatch, message):
    env = environment(monkeypatch, message=message)
    env.service.retrieval.search.return_value = []
    env.provider.classify.return_value = '{"category":"business","mixed":false}'
    async def stream(context):
        assert env.service.retrieval.search.called
        assert SOURCE not in json.dumps(context)
        yield 'Puedes comenzar definiendo el objetivo del manual y sus destinatarios.'
    env.provider.stream = Mock(side_effect=stream)
    turn, events = run(env)
    text = ''.join(event.get('text', '') for event in events)
    assert events[-1]['type'] == 'done' and events[-1]['outcome'] == 'answered'
    assert 'sin respaldo documental empresarial' in text
    assert 'puede no ajustarse a tu caso' in text
    assert 'Puedes comenzar' in text
    assert not events[-1]['sources'] and '[S' not in text
    env.service.retrieval.search.assert_called_once()
    env.service.sources.persist.assert_not_called()
    env.provider.structured.assert_not_awaited()


def followup_environment(monkeypatch):
    env = environment(monkeypatch, message='¿Y después?')
    env.store.topic_history.return_value = [{'role': 'user', 'content': '¿Cómo se confecciona un vestido?', 'documentary': True}]
    env.store.topic_document_ids.return_value = []
    env.store.followup_progress.return_value = 'Se explicó la revisión de las medidas.'
    return env


def test_followup_uses_validated_progress_as_data_with_fresh_evidence(monkeypatch):
    env = followup_environment(monkeypatch)
    calls = []
    def progress(*_, **kwargs):
        assert kwargs['topic_question'] == '¿Cómo se confecciona un vestido?'
        calls.append('progress')
        return 'Se explicó la revisión de las medidas.'
    env.store.followup_progress.side_effect = progress
    env.service.retrieval.revalidate.side_effect = lambda *_: calls.append('revalidate')
    original = env.provider.structured.return_value
    async def structured(context, schema):
        calls.append('structured')
        assert calls[-2] == 'revalidate'
        body = json.loads(context[-1]['content'])
        question = json.loads(body['question'])
        assert question['previous_answer_for_progress_only'] == 'Se explicó la revisión de las medidas.'
        assert body['sources'][0]['passages'][0]['text'] == SOURCE
        return original
    env.provider.structured.side_effect = structured
    turn, events = run(env)
    assert events[-1]['type'] == 'done'
    assert calls.index('progress') < calls.index('structured')


def test_revoked_previous_progress_never_reaches_synthesis_context(monkeypatch):
    env = followup_environment(monkeypatch)
    env.store.followup_progress.return_value = None
    turn, events = run(env)
    assert events[-1]['type'] == 'done'
    assert 'previous_answer_for_progress_only' not in env.provider.structured.call_args.args[0][-1]['content']


def test_revocation_after_progress_read_prevents_model_call(monkeypatch):
    env = followup_environment(monkeypatch)
    def progress(*_, **kwargs):
        env.service.retrieval.revalidate.side_effect = LenyError('LENY_RAG_SOURCE_REVOKED', 'Fuente no disponible.', 403)
        return 'Previous wording must not enter model.'
    env.store.followup_progress.side_effect = progress
    turn, events = run(env)
    assert events[-1]['type'] == 'error'
    env.provider.structured.assert_not_awaited()
    assert not any(event['type'] == 'delta' for event in events)


def test_general_fallback_cannot_invent_documentary_citations(monkeypatch):
    env = environment(monkeypatch, message='¿Qué es el margen de utilidad?')
    env.service.retrieval.search.return_value = []
    async def stream(_):
        yield 'La política empresarial garantiza una devolución ilimitada [S1].'
    env.provider.stream = Mock(side_effect=stream)
    turn, events = run(env)
    assert events[-1]['type'] == 'error'
    assert 'devolución ilimitada' not in ''.join(event.get('text', '') for event in events)
    env.service.sources.persist.assert_not_called()
