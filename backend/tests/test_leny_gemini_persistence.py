"""Provider persistence/API and migration contracts; no live DB or inference."""
from contextlib import nullcontext
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import SecretStr, ValidationError

from app.models.leny import LenyConversation
from app.schemas.leny import ConversationCreateRequest, ConversationResponse, LenyChatRequest
from app.services.leny_llm_contracts import LenyError
from app.services.leny_store import LenyActor, LenyStore
from test_leny import api


def conversation(provider='ollama', model='qwen3.5:4b-q4_K_M'):
    now = datetime.now(timezone.utc)
    return dict(id=uuid4(), title='Synthetic chat', created_at=now, updated_at=now,
                llm_provider=provider, llm_model=model)


def test_provider_is_creation_only_not_a_message_override():
    assert ConversationCreateRequest().provider == 'ollama'
    assert ConversationCreateRequest(provider='gemini').provider == 'gemini'
    for data in ({'provider':'unknown'}, {'provider':'gemini','model':'browser-model'}):
        with pytest.raises(ValidationError):
            ConversationCreateRequest(**data)
    with pytest.raises(ValidationError):
        LenyChatRequest(conversation_id=uuid4(), request_id=uuid4(), message='Hola', provider='gemini')


def test_legacy_conversation_response_defaults_to_original_provider():
    data = conversation()
    data.pop('llm_provider');data.pop('llm_model')
    result = ConversationResponse(**data)
    assert result.llm_provider == 'ollama' and result.llm_model == 'qwen3.5:4b-q4_K_M'


def test_store_create_persists_provider_and_model_without_other_mutations():
    db = Mock()
    def flush():
        item = db.add.call_args.args[0]
        item.created_at = item.updated_at = datetime.now(timezone.utc)
    db.flush.side_effect = flush
    store = object.__new__(LenyStore)
    store.transaction = lambda: nullcontext(db)
    store.audit = Mock()
    actor = LenyActor(7, 9, 'synthetic-event')
    result = store.create(actor, provider='gemini', model='gemini-3.8-flash')
    stored = db.add.call_args.args[0]
    assert isinstance(stored, LenyConversation)
    assert stored.user_id == 9 and stored.account_id == 7
    assert result['llm_provider'] == 'gemini' and result['llm_model'] == 'gemini-3.8-flash'
    store.audit.assert_called_once()
    db.execute.assert_not_called()


def test_provider_resolution_checks_conversation_owner():
    db = Mock()
    store = object.__new__(LenyStore)
    store.transaction = lambda: nullcontext(db)
    actor = LenyActor(7, 9, 'synthetic-event')
    identity = uuid4()
    db.scalar.return_value = SimpleNamespace(llm_provider='gemini', llm_model='gemini-3.8-flash')
    assert store.provider_for(actor, identity) == ('gemini','gemini-3.8-flash')
    sql = db.scalar.call_args.args[0]
    assert sql.compile().params['user_id_1'] == actor.user_id
    db.scalar.return_value = None
    with pytest.raises(LenyError) as caught:
        store.provider_for(actor, identity)
    assert caught.value.code == 'LENY_NOT_FOUND'


def test_sensitive_history_finalizes_the_created_assistant_as_failed():
    import asyncio
    from app.core.config import Settings
    from app.schemas.leny import LenyChatRequest
    from app.services.leny_service import LenyService
    config=Settings(_env_file=None,environment='test',leny_gemini_enabled=True,
        leny_gemini_free_tier_confirmed=True,gemini_api_key='SYNTHETIC_KEY',
        leny_rag_profile='rag4_v1',leny_rag_response_mode='controlled-synthesis-v1')
    store=LenyStore(None)
    store.provider_for=Mock(return_value=('gemini','gemini-3.8-flash'))
    store.quality_profile_for=Mock(return_value='baseline')
    store.duplicate=Mock();store.reconcile=Mock();store.topic_history=Mock(return_value=[])
    store.begin_turn=Mock(return_value=(uuid4(),[{'role':'user','content':'cliente@example.invalid'},
                                              {'role':'assistant','content':'Respuesta previa.'}]))
    store.save=Mock()
    coordinator=Mock();service=LenyService(config,store,coordinator)
    actor=LenyActor(7,9,'synthetic-event')
    payload=LenyChatRequest(conversation_id=uuid4(),request_id=uuid4(),message='Quiero iniciar un manual')
    with pytest.raises(LenyError) as caught:asyncio.run(service.prepare(actor,payload))
    assert caught.value.code=='LENY_GEMINI_SENSITIVE'
    assert store.save.call_args.args[4]=='failed'
    coordinator.acquire.return_value.close.assert_called_once()


def test_remote_progress_keeps_frozen_ids_and_checks_current_publication(monkeypatch):
    from app.services import leny_rag_retrieval
    actor=LenyActor(7,9,'synthetic-event');identity=uuid4();ids=[uuid4(),uuid4()]
    db=Mock();db.scalar.return_value=SimpleNamespace(id=uuid4(),content='Progreso sintético.')
    db.scalars.side_effect=[ids,ids]
    store=LenyStore(None);store.transaction=lambda:nullcontext(db);store.own=Mock()
    store.sources=SimpleNamespace(config=SimpleNamespace())
    monkeypatch.setattr(leny_rag_retrieval,'reader',Mock())
    monkeypatch.setattr(leny_rag_retrieval,'parameters',lambda *_:{})
    progress=store.followup_progress(actor,identity,'synthetic',binding=True)
    assert progress==dict(content='Progreso sintético.',fragment_ids=sorted(map(str,ids)))
    db.scalars.side_effect=None;db.scalars.return_value=ids
    store.revalidate_progress(actor,identity,progress['fragment_ids'])
    db.scalars.return_value=ids[:1]
    with pytest.raises(LenyError) as caught:store.revalidate_progress(actor,identity,progress['fragment_ids'])
    assert caught.value.code=='LENY_RAG_ACCESS_REVOKED'
    assert set(db.scalars.call_args.args[1]['ids'])==set(map(str,ids))
    assert 'published_indexation_id' in str(db.scalars.call_args.args[0])


@pytest.mark.parametrize('body',[None,{}])
def test_old_create_endpoint_remains_ollama(api, body):
    api.service.config = SimpleNamespace(leny_model='qwen3.5:4b-q4_K_M')
    api.service.store.create.return_value = conversation()
    options = {'headers':api.headers}
    if body is not None:options['json'] = body
    result = api.client.post('/leny/conversations', **options)
    assert result.status_code == 201 and result.json()['llm_provider'] == 'ollama'
    assert api.service.store.create.call_args.kwargs == dict(provider='ollama', model='qwen3.5:4b-q4_K_M')


@pytest.mark.parametrize('role',['ADMIN','CAJA','INV_BOUTIQUE','INV_TALLER','MODISTA'])
def test_existing_permission_allows_configured_gemini_for_each_role(api, role):
    api.actor.rol.codigo = role
    api.service.config = SimpleNamespace(leny_gemini_enabled=True, gemini_api_key=SecretStr('SYNTHETIC_KEY'),
        leny_gemini_free_tier_confirmed=True, leny_gemini_model='gemini-3.8-flash')
    api.service.store.create.return_value = conversation('gemini','gemini-3.8-flash')
    result = api.client.post('/leny/conversations', json={'provider':'gemini'}, headers=api.headers)
    assert result.status_code == 201
    assert result.json()['llm_provider'] == 'gemini' and 'SYNTHETIC_KEY' not in result.text
    assert api.service.store.create.call_args.kwargs == dict(provider='gemini', model='gemini-3.8-flash')


@pytest.mark.parametrize('role',['DOC','UNKNOWN'])
def test_ungranted_role_cannot_create_a_gemini_chat(api, role):
    api.actor.rol.codigo = role
    result = api.client.post('/leny/conversations', json={'provider':'gemini'}, headers=api.headers)
    assert result.status_code == 403
    api.service.store.create.assert_not_called()


@pytest.mark.parametrize('enabled,key,confirmed,code',[
    (False,None,False,'LENY_GEMINI_DISABLED'),
    (True,None,True,'LENY_GEMINI_KEY_MISSING'),
    (True,SecretStr(' '),True,'LENY_GEMINI_KEY_MISSING'),
    (True,SecretStr('SYNTHETIC_KEY'),False,'LENY_GEMINI_TIER_UNCONFIRMED'),
])
def test_create_gemini_is_server_gated_without_network(api, enabled, key, confirmed, code):
    api.service.config = SimpleNamespace(leny_gemini_enabled=enabled, gemini_api_key=key,
        leny_gemini_free_tier_confirmed=confirmed)
    result = api.client.post('/leny/conversations', json={'provider':'gemini'}, headers=api.headers)
    assert result.status_code == 503 and result.json()['detail']['code'] == code
    assert 'SYNTHETIC_KEY' not in result.text
    api.service.store.create.assert_not_called()


def migration():
    path=Path(__file__).parents[1]/'alembic/versions/20261105_0024_leny_conversation_providers.py'
    spec=importlib.util.spec_from_file_location('synthetic_0024',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_migration_only_changes_leny_and_refuses_unreviewed_history(monkeypatch):
    module=migration();operations=Mock();operations.get_bind.return_value.scalar.return_value=True
    monkeypatch.setattr(module,'op',operations)
    with pytest.raises(RuntimeError,match='Historical'):
        module.upgrade()
    operations.add_column.assert_not_called()
    operations.get_bind.return_value.scalar.return_value=False
    module.upgrade()
    assert module.down_revision == '20261104_0023'
    for name in ('add_column','create_check_constraint','create_table','create_index'):
        for call in getattr(operations,name).call_args_list:
            assert call.kwargs['schema']=='leny'
    columns=operations.create_table.call_args.args[1:]
    assert not any(getattr(column,'foreign_keys',set()) for column in columns)


@pytest.mark.parametrize('checks',[[True],[False,True]])
def test_downgrade_never_erases_gemini_conversations_or_usage(monkeypatch,checks):
    module=migration();operations=Mock();operations.get_bind.return_value.scalar.side_effect=checks
    monkeypatch.setattr(module,'op',operations)
    with pytest.raises(RuntimeError,match='preserved'):
        module.downgrade()
    operations.drop_table.assert_not_called()
    operations.drop_column.assert_not_called()
