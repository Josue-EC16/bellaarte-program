"""Functional adapter contracts with SDK doubles and fictitious credentials.

These tests do not establish Google access, quota entitlement or semantic quality.
"""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import httpx
import pytest

from app.core.config import Settings
from app.services.leny_gemini import GeminiProvider
from app.services.leny_gemini_safety import check_runtime_secrets, check_user_context
from app.services.leny_llm_budget import input_budget
from app.services.leny_llm_contracts import LenyError


MESSAGES = [{'role':'system','content':'Responde con evidencia.'},
            {'role':'user','content':'Explica cómo organizar un manual.'}]
SCHEMA = {'type':'object','properties':{'answer':{'type':'string'}},'required':['answer']}


@pytest.fixture(autouse=True)
def external_http_forbidden(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError('Real external HTTP is forbidden in provider contract tests')
    monkeypatch.setattr(httpx.Client,'send',blocked)
    monkeypatch.setattr(httpx.AsyncClient,'send',blocked)


def config(**changes):
    base = dict(environment='test',leny_llm_provider='gemini',leny_gemini_enabled=True,
                leny_gemini_free_tier_confirmed=True,gemini_api_key='SYNTHETIC_PROVIDER_KEY',
                database_url='postgresql+psycopg2://unit_only@127.0.0.1:1/unit_only')
    return Settings(_env_file=None,**(base | changes))


def response(value='{"answer":"Revisa el propósito y organiza las etapas."}', *, reason='STOP', parts=None):
    if parts is None:
        parts=[SimpleNamespace(text=value,thought=False,function_call=None,executable_code=None)]
    return SimpleNamespace(candidates=[SimpleNamespace(finish_reason=reason,
        content=SimpleNamespace(parts=parts))],usage_metadata=SimpleNamespace(
            prompt_token_count=120,candidates_token_count=35,thoughts_token_count=40))


def environment(*,result=None,authorize=None,**changes):
    usage=SimpleNamespace(reserve=Mock(side_effect=lambda *args:uuid4()),finish=Mock())
    models=SimpleNamespace(generate_content=AsyncMock(return_value=result or response()),
                           count_tokens=AsyncMock(return_value=SimpleNamespace(total_tokens=100)),
                           get=AsyncMock(return_value=SimpleNamespace(name='models/gemini-3.1-flash-lite')))
    client=SimpleNamespace(aio=SimpleNamespace(models=models,aclose=AsyncMock()),close=Mock())
    factory=Mock(return_value=client)
    provider=GeminiProvider(config(**changes),usage=usage,client_factory=factory,authorize=authorize)
    return SimpleNamespace(provider=provider,usage=usage,models=models,client=client,factory=factory)


def test_lazy_client_and_medium_structured_request_reuse_and_close():
    e=environment()
    e.factory.assert_not_called()
    async def scenario():
        await e.provider.available()
        e.factory.assert_not_called()
        first=await e.provider.structured(MESSAGES,SCHEMA)
        second=await e.provider.classify(MESSAGES,SCHEMA)
        await e.provider.aclose();await e.provider.aclose()
        return first,second
    first,second=asyncio.run(scenario())
    assert json.loads(first)==json.loads(second)
    assert e.factory.call_count==1 and e.models.generate_content.await_count==2
    assert e.models.count_tokens.await_count==0  # Small payload: conservative local estimate.
    kwargs=e.models.generate_content.call_args.kwargs
    assert kwargs['model']=='gemini-3.1-flash-lite'
    options=kwargs['config']
    assert options.max_output_tokens==8192
    assert str(options.thinking_config.thinking_level).lower().endswith('medium')
    assert options.thinking_config.include_thoughts is False
    assert options.temperature is None and not options.tools
    assert options.automatic_function_calling.disable is True
    assert options.response_mime_type=='application/json' and options.response_json_schema==SCHEMA
    assert e.factory.call_args.kwargs['http_options'].retry_options.attempts==1
    assert e.factory.call_args.kwargs['vertexai'] is False
    assert e.factory.call_args.kwargs['enterprise'] is False
    assert e.provider.metrics==dict(prompt_eval_count=120,eval_count=35,thinking_tokens=40)
    assert e.usage.reserve.call_count==2 and e.usage.finish.call_count==2
    assert [call.args[0] for call in e.usage.reserve.call_args_list]==['generate','classifier']
    assert all(call.args[1]>0 for call in e.usage.reserve.call_args_list)
    e.client.aio.aclose.assert_awaited_once();e.client.close.assert_called_once()


@pytest.mark.parametrize('changes,code',[
    ({'leny_gemini_enabled':False},'LENY_GEMINI_DISABLED'),
    ({'leny_gemini_free_tier_confirmed':False},'LENY_GEMINI_TIER'),
    ({'gemini_api_key':None},'LENY_GEMINI_KEY_MISSING'),
    ({'gemini_api_key':' '},'LENY_GEMINI_KEY_MISSING'),
    ({'leny_gemini_model':'another-paid-model'},'LENY_GEMINI_MODEL'),
])
def test_server_gates_prevent_sdk_and_quota_calls(changes,code):
    e=environment(**changes)
    with pytest.raises(LenyError) as caught:
        asyncio.run(e.provider.structured(MESSAGES,SCHEMA))
    assert caught.value.code==code
    e.factory.assert_not_called();e.usage.reserve.assert_not_called()
    e.models.generate_content.assert_not_awaited()


@pytest.mark.parametrize('model',['gemini-3.8-flash','gemini-3.5-flash-lite','gemini-3.1-flash-lite'])
def test_explicit_model_does_not_change_quota_or_fall_back(model):
    e=environment(leny_gemini_model=model)
    asyncio.run(e.provider.structured(MESSAGES,SCHEMA))
    assert e.models.generate_content.call_args.kwargs['model']==model
    assert (e.provider.config.leny_gemini_rpm,e.provider.config.leny_gemini_tpm,e.provider.config.leny_gemini_rpd)==(15,250000,500)
    assert e.provider.config.leny_gemini_thinking_level=='medium'
    assert e.provider.config.leny_gemini_input_token_budget==32678
    assert e.provider.config.leny_gemini_output_tokens==8192


def test_native_schema_normalization_preserves_the_server_contract():
    e=environment()
    schema={'type':'object','$schema':'https://json-schema.org/draft/2020-12/schema',
            'properties':{'sources':{'type':'array','uniqueItems':True,'items':{'type':'string'}}}}
    original=json.loads(json.dumps(schema))
    asyncio.run(e.provider.classify(MESSAGES,schema))
    native=e.models.generate_content.call_args.kwargs['config'].response_json_schema
    assert '$schema' not in native and 'uniqueItems' not in native['properties']['sources']
    assert schema==original
    assert e.usage.reserve.call_args.args[0]=='classifier'


def test_native_synthesis_schema_binds_each_source_to_its_own_passages():
    from app.services.leny_rag_synthesis import schema_for
    rows=[dict(text='Revisa las medidas antes del corte.',fragment_id=uuid4()),
          dict(text='Organiza las piezas después de revisar.',fragment_id=uuid4())]
    schema=schema_for(rows,allow_general=True,linked_support=True,bind_sources=True)
    original=json.loads(json.dumps(schema))
    e=environment()
    asyncio.run(e.provider.structured(MESSAGES,schema))
    native=e.models.generate_content.call_args.kwargs['config'].response_json_schema
    variants=native['properties']['blocks']['items']['anyOf']
    assert len(variants)==3 and schema==original
    for variant in variants:
        fields=variant['properties'];label=fields['source']['enum'][0]
        if label:
            assert fields['kind']['enum']==['documented'] and fields['support']['minItems']==1
            assert all(pid.startswith('P'+label[1:]+'_') for pid in fields['support']['items']['enum'])
        else:assert fields['support']['maxItems']==0 and 'documented' not in fields['kind']['enum']


def test_bound_synthesis_preserves_heading_body_support_from_same_index():
    from app.services.leny_rag_synthesis import schema_for
    index=uuid4()
    rows=[dict(text='Funciones de la modista.',fragment_id=uuid4(),indexation_id=index),
          dict(text='Comprobar las medidas.',fragment_id=uuid4(),indexation_id=index),
          dict(text='Orientar a la clienta.',fragment_id=uuid4(),indexation_id=uuid4())]
    schema=schema_for(rows,linked_support=True,bind_sources=True)
    branches=schema['properties']['blocks']['items']['anyOf']
    for branch in branches[:2]:
        ids=branch['properties']['support']['items']['enum']
        assert any(pid.startswith('P1_') for pid in ids) and any(pid.startswith('P2_') for pid in ids)
        assert not any(pid.startswith('P3_') for pid in ids)


def test_token_reservation_counts_the_expanded_native_schema():
    from app.services.leny_rag_selection import plan_schema
    e=environment();schema=plan_schema(5)
    asyncio.run(e.provider.classify(MESSAGES,schema))
    native=e.models.generate_content.call_args.kwargs['config'].response_json_schema
    system,contents=e.provider._parts(MESSAGES)
    expected=len(json.dumps(dict(system=system,contents=contents,schema=native),ensure_ascii=False,separators=(',',':')).encode())+512
    assert e.usage.reserve.call_args.args[1]==expected
    assert len(json.dumps(native))>len(json.dumps(schema))


def test_native_plan_schema_cannot_cite_absent_or_unmatched_evidence():
    from app.services.leny_rag_selection import plan_schema
    schema=plan_schema(4);original=json.loads(json.dumps(schema))
    e=environment();asyncio.run(e.provider.classify(MESSAGES,schema))
    variants=e.models.generate_content.call_args.kwargs['config'].response_json_schema['anyOf']
    assert schema==original and len(variants)==3
    for variant in variants:
        fields=variant['properties']
        if fields['sources'].get('minItems')==1:
            assert fields['scope']['enum']==['matched']
            assert set(fields['relation']['enum'])=={'direct','partial','contradictory'}
        else:assert fields['sources']['maxItems']==0


def test_revalidation_occurs_before_every_attempt_and_revocation_stops_emission():
    ordering=[]
    async def authorize():ordering.append('authorize')
    e=environment(authorize=authorize)
    e.usage.reserve.side_effect=lambda *args:(ordering.append('reserve') or uuid4())
    async def generate(**kwargs):ordering.append('http');return response()
    e.models.generate_content.side_effect=generate
    asyncio.run(e.provider.structured(MESSAGES,SCHEMA))
    assert ordering==['authorize','reserve','authorize','http']
    e.provider.authorize=AsyncMock(side_effect=LenyError('LENY_RAG_REVOKED','Fuente no disponible.',403))
    with pytest.raises(LenyError) as caught:
        asyncio.run(e.provider.structured(MESSAGES,SCHEMA))
    assert caught.value.code=='LENY_RAG_REVOKED'
    assert e.models.generate_content.await_count==1 and e.usage.reserve.call_count==1


@pytest.mark.parametrize('result,code',[
    (response('not JSON'),'LENY_GEMINI_JSON'),
    (response(reason='MAX_TOKENS'),'LENY_GEMINI_INCOMPLETE'),
    (response('  '),'LENY_GEMINI_EMPTY'),
    (SimpleNamespace(candidates=[],usage_metadata=None),'LENY_GEMINI_EMPTY'),
    (response(parts=[SimpleNamespace(text=None,thought=False,function_call={'name':'change_stock'},executable_code=None)]),'LENY_GEMINI_TOOLS_BLOCKED'),
])
def test_unusable_output_never_becomes_successful_stream_or_retry(result,code):
    e=environment(result=result)
    async def scenario():return await e.provider.structured(MESSAGES,SCHEMA)
    with pytest.raises(LenyError) as caught:asyncio.run(scenario())
    assert caught.value.code==code
    assert e.models.generate_content.await_count==1 and e.usage.reserve.call_count==1


def test_stream_buffers_output_and_drops_thought_parts():
    thought=SimpleNamespace(text='PRIVATE_THOUGHT_TRACE',thought=True,function_call=None,executable_code=None)
    final=SimpleNamespace(text='Respuesta pública.',thought=False,function_call=None,executable_code=None)
    e=environment(result=response(parts=[thought,final]))
    async def scenario():return [part async for part in e.provider.stream(MESSAGES)]
    assert asyncio.run(scenario())==['Respuesta pública.']
    assert e.provider.response_complete and e.provider.finish_reason=='stop'


@pytest.mark.parametrize('result',[
    response('PARTIAL_PRIVATE_TEXT',reason='MAX_TOKENS'),
    response(parts=[SimpleNamespace(text='UNVERIFIED_TEXT',thought=False,
        function_call={'name':'write_data'},executable_code=None)]),
])
def test_rejected_stream_never_emits_partial_text(result):
    e=environment(result=result);emitted=[]
    async def scenario():
        async for part in e.provider.stream(MESSAGES):emitted.append(part)
    with pytest.raises(LenyError):asyncio.run(scenario())
    assert emitted==[] and e.models.generate_content.await_count==1


@pytest.mark.parametrize('status,expected',[(400,'LENY_GEMINI_REQUEST'),(401,'LENY_GEMINI_AUTH'),
    (403,'LENY_GEMINI_AUTH'),(404,'LENY_GEMINI_MODEL'),(429,'LENY_GEMINI_QUOTA')])
def test_provider_errors_hide_google_body_and_never_fail_over(status,expected):
    from google.genai.errors import APIError
    e=environment()
    e.models.generate_content.side_effect=APIError(status,{'error':{'message':'PRIVATE_GOOGLE_BODY SYNTHETIC_PROVIDER_KEY'}})
    with pytest.raises(LenyError) as caught:asyncio.run(e.provider.structured(MESSAGES,SCHEMA))
    assert caught.value.code==expected
    assert 'PRIVATE_GOOGLE_BODY' not in str(caught.value) and 'SYNTHETIC_PROVIDER_KEY' not in str(caught.value)
    assert e.models.generate_content.await_count==1
    assert e.usage.finish.call_args.kwargs['error']==expected


def test_503_retry_is_bounded_and_each_attempt_reserves_again(monkeypatch):
    from google.genai.errors import APIError
    from app.services import leny_gemini
    e=environment(authorize=AsyncMock())
    e.models.generate_content.side_effect=[APIError(503,{'error':{'message':'synthetic overload'}}),response()]
    sleep=AsyncMock();monkeypatch.setattr(leny_gemini.asyncio,'sleep',sleep)
    asyncio.run(e.provider.structured(MESSAGES,SCHEMA))
    assert e.models.generate_content.await_count==2 and e.usage.reserve.call_count==2
    assert e.provider.authorize.await_count==4 and e.usage.finish.call_count==2
    sleep.assert_awaited_once()


def test_timeout_and_cancellation_retain_consumption_without_auto_retry():
    for error,expected in ((asyncio.TimeoutError(),'LENY_GEMINI_TIMEOUT'),(asyncio.CancelledError(),'LENY_GEMINI_CANCELLED')):
        e=environment();e.models.generate_content.side_effect=error
        with pytest.raises(asyncio.CancelledError if isinstance(error,asyncio.CancelledError) else LenyError):
            asyncio.run(e.provider.structured(MESSAGES,SCHEMA))
        assert e.models.generate_content.await_count==1 and e.usage.reserve.call_count==1
        assert e.usage.finish.call_args.kwargs['error']==expected


def test_large_count_is_cached_but_over_budget_never_generates():
    e=environment()
    messages=[{'role':'system','content':'Política.'},{'role':'user','content':'x'*34000}]
    e.models.count_tokens.return_value=SimpleNamespace(total_tokens=32700)
    async def scenario():
        a=await e.provider.measure_prompt(messages,SCHEMA)
        b=await e.provider.measure_prompt(messages,SCHEMA)
        assert a==b and a>32678
        with pytest.raises(LenyError) as caught:await e.provider.structured(messages,SCHEMA)
        assert caught.value.code=='LENY_CONTEXT_LIMIT'
    asyncio.run(scenario())
    assert e.models.count_tokens.await_count==1 and e.models.generate_content.await_count==0
    assert e.usage.reserve.call_args.args[0]=='count'


@pytest.mark.parametrize('count',[None,0,'100'])
def test_missing_or_invalid_external_count_is_not_treated_as_available_budget(count):
    e=environment();e.models.count_tokens.return_value=SimpleNamespace(total_tokens=count)
    with pytest.raises(LenyError) as caught:
        asyncio.run(e.provider.structured([{'role':'user','content':'x'*34000}],SCHEMA))
    assert caught.value.code=='LENY_GEMINI_TOKEN_COUNT'
    e.models.generate_content.assert_not_awaited()


def test_missing_or_exhausted_ledger_prevents_http_and_external_key_leak():
    e=environment();e.provider.usage=None
    with pytest.raises(LenyError) as caught:asyncio.run(e.provider.structured(MESSAGES,SCHEMA))
    assert caught.value.code=='LENY_GEMINI_QUOTA_UNAVAILABLE'
    e.models.generate_content.assert_not_awaited()
    e=environment()
    full=LenyError('LENY_GEMINI_QUOTA','Cuota agotada.',429);full.retry_after=3600
    e.usage.reserve.side_effect=full
    with pytest.raises(LenyError):asyncio.run(e.provider.structured(MESSAGES,SCHEMA))
    e.models.generate_content.assert_not_awaited()
    e=environment()
    with pytest.raises(LenyError) as caught:
        asyncio.run(e.provider.structured([{'role':'user','content':'SYNTHETIC_PROVIDER_KEY'}],SCHEMA))
    assert caught.value.code=='LENY_GEMINI_SENSITIVE'
    e.usage.reserve.assert_not_called();e.models.generate_content.assert_not_awaited()


def test_user_history_privacy_and_owner_approved_document_scope_remain_distinct():
    for text in ('Mi correo es persona@example.invalid','CI: 12345678','cuenta bancaria: 123456789'):
        with pytest.raises(LenyError):check_user_context(text)
        with pytest.raises(LenyError):check_user_context('Explica el proceso',[{'content':text}])
    # Owner-approved documentary content is not blanket-redacted for PII;
    # runtime secrets remain forbidden even there.
    check_runtime_secrets(config(),'Manual publicado: contacto persona@example.invalid')
    with pytest.raises(LenyError):check_runtime_secrets(config(),'Manual SYNTHETIC_PROVIDER_KEY')
    assert input_budget(config())==32678
    local=config(leny_llm_provider='ollama')
    assert input_budget(local)==local.leny_num_ctx-local.leny_num_predict-256
