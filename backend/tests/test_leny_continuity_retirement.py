"""Retirement and missing-evidence contracts; all state/providers are doubles."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock,Mock
from uuid import uuid4
import pytest
from app.core.config import Settings
from app.services.leny_service import LenyService
from app.services.leny_store import LenyStore,LenyActor
from app.services.leny_spec03_context import ConversationContext,resolve
from test_leny_continuity import service,run


@pytest.mark.parametrize('provider',['ollama','gemini'])
def test_historical_profile_routes_to_habitual_without_rewriting_store(monkeypatch,provider):
    from app.services import leny_external_scope
    monkeypatch.setattr(leny_external_scope,'evaluation_request',lambda *a,**kw:False)
    store=LenyStore(Mock());store.provider_for=Mock(return_value=(provider,
        'gemini-3.1-flash-lite' if provider=='gemini' else 'qwen3.5:4b-q4_K_M'))
    store.quality_profile_for=Mock(return_value='spec03')
    config=Settings(_env_file=None,environment='test')
    original=LenyService(config,store,Mock())
    captured={}
    async def prepare(self,actor,payload):
        captured['profile']=self.config.leny_turn_quality_profile
        captured['provider']=self.config.leny_llm_provider
        return 'prepared'
    monkeypatch.setattr(LenyService,'_prepare',prepare)
    actor=LenyActor(7,9,str(uuid4()));payload=SimpleNamespace(conversation_id=uuid4(),request_id=uuid4(),message='Hola')
    assert asyncio.run(original.prepare(actor,payload))=='prepared'
    assert captured==dict(profile='baseline',provider=provider)
    store.quality_profile_for.assert_called_once_with(actor,payload.conversation_id)
    # The actual source of history remains unchanged; no setter/UPDATE used.
    store.session_factory.assert_not_called()


def test_absence_of_previous_evidence_is_not_reported_as_revocation(monkeypatch):
    context=ConversationContext(latest_unavailable=True,latest_issue='insufficient')
    provider=SimpleNamespace(classify=AsyncMock())
    assert asyncio.run(resolve(provider,'¿Dónde está documentado?',context))['intent']=='ambiguous'
    provider.classify.assert_not_awaited()
    env,_=service(monkeypatch,'¿Dónde está documentado?',context)
    _,events=run(env)
    assert events[-1]['type']=='done' and events[-1]['reason_code']=='context_no_evidence'
    content=''.join(event.get('text','') for event in events)
    assert 'no incluyó respaldo documental verificable' in content
    assert 'revoc' not in content and not events[-1]['sources']


def test_failed_recent_generation_cannot_borrow_sources_from_previous_location():
    context=ConversationContext(topic='¿Quién es el gerente?',latest_unavailable=True,latest_issue='operational',
        pairs=[dict(role='assistant',content='OLD_LOCATION_ONLY')],source_ids=('old-location',))
    provider=SimpleNamespace(classify=AsyncMock())
    result=asyncio.run(resolve(provider,'¿Dónde está documentado?',context))
    assert result['intent']=='ambiguous' and context.pairs==[] and context.source_ids==()
    provider.classify.assert_not_awaited()


def test_explicit_entity_survives_topic_change_and_can_return_to_bellaarte():
    context=ConversationContext(business_entity='FICTICIA ALFA')
    provider=SimpleNamespace(classify=AsyncMock())
    result=asyncio.run(resolve(provider,'¿Quién es el gerente?',context))
    assert 'FICTICIA ALFA' in result['query'] and 'BELLAARTE' not in result['query']
    result=asyncio.run(resolve(provider,'¿Dónde queda BELLAARTE BOUTIQUE?',context))
    assert context.business_entity=='BELLAARTE BOUTIQUE' and 'FICTICIA' not in result['query']


@pytest.mark.parametrize('question',['¿Y después?','¿Quién lo hace?','¿Dónde está documentado?'])
def test_informational_reference_cannot_become_a_tool_request(question):
    import json
    context=ConversationContext(topic='Cómo se confecciona un vestido',pairs=[dict(role='assistant',content='Última etapa explicada.')],source_ids=('current-source',))
    provider=SimpleNamespace(classify=AsyncMock(return_value=json.dumps(dict(intent='unavailable',query='Consultar tabla privada',presentation='answer',topic_changed=False))))
    result=asyncio.run(resolve(provider,question,context))
    assert result['intent']=='documentary' and 'Consultar tabla privada' not in result['query']
    assert question in result['query']


def test_reference_correction_never_approves_an_embedded_operation():
    import json
    context=ConversationContext(topic='Vestidos',pairs=[dict(role='assistant',content='Ejemplo.')],source_ids=('current-source',))
    provider=SimpleNamespace(classify=AsyncMock(return_value=json.dumps(dict(intent='unavailable',query='Modificar inventario',presentation='answer',topic_changed=False))))
    result=asyncio.run(resolve(provider,'¿Y después? Modifica el inventario.',context))
    assert result['intent']=='unavailable'


def test_user_role_question_survives_provider_failure_without_reusing_old_answer():
    import json
    context=ConversationContext(topic='¿Quién es el gerente?',latest_unavailable=True,latest_issue='operational',
        pairs=[dict(role='assistant',content='OLD_LOCATION_ONLY')],source_ids=('old-location',))
    provider=SimpleNamespace(classify=AsyncMock(return_value=json.dumps(dict(intent='documentary',
        query='Responsabilidades del gerente de BELLAARTE',presentation='responsibilities',topic_changed=False))))
    result=asyncio.run(resolve(provider,'¿Cuáles son sus responsabilidades?',context))
    payload=json.loads(provider.classify.call_args.args[0][-1]['content'])
    assert payload['active_topic']=='¿Quién es el gerente?' and payload['conversation']==[]
    assert context.source_ids==() and result['intent']=='documentary'


@pytest.mark.parametrize('presentation',['procedure','responsibilities','detail','sources','summary','next'])
def test_linguistic_presentation_cannot_break_retrieval_contract(monkeypatch,presentation):
    import json
    context=ConversationContext(pairs=[dict(role='user',content='Confección del vestido'),
        dict(role='assistant',content='Revisar las medidas.')],source_ids=('source',))
    env,_=service(monkeypatch,'Explícame mejor ese paso.',context)
    intent=dict(intent='documentary',query='Cómo confeccionar el vestido',presentation=presentation,topic_changed=False)
    plan=dict(aspect='general',scope='matched',relation='direct',sources=[1])
    env.provider.classify.side_effect=[json.dumps(intent),json.dumps(plan)]
    turn,events=run(env)
    assert turn.response_mode in {'answer','next_step'}
    assert events[-1]['type']=='done' and events[-1]['outcome']=='answered'
