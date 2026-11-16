"""Immutable quality profile contracts; fake API/DB, no production effects."""
from contextlib import nullcontext
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.leny import ConversationCreateRequest, ConversationResponse, LenyChatRequest
from app.services.leny_llm_contracts import LenyError
from app.services.leny_store import LenyActor, LenyStore
from test_leny import api


def row(profile='baseline'):
    return dict(id=uuid4(),title='Synthetic review',created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),quality_profile=profile)


def setup_api(api, *, default='baseline', evaluation=False, response='baseline'):
    api.service.config=SimpleNamespace(leny_model='qwen3.5:4b-q4_K_M',
        leny_quality_profile=default,leny_spec03_evaluation_enabled=evaluation)
    api.service.store.create.return_value=row(response)


def test_profile_only_exists_at_conversation_creation():
    assert ConversationCreateRequest().quality_profile is None
    for value in ('baseline','spec03'):
        assert ConversationCreateRequest(quality_profile=value).quality_profile==value
    with pytest.raises(ValidationError):ConversationCreateRequest(quality_profile='unknown')
    with pytest.raises(ValidationError):
        LenyChatRequest(conversation_id=uuid4(),request_id=uuid4(),message='Hola',quality_profile='spec03')
    legacy=row();legacy.pop('quality_profile')
    assert ConversationResponse(**legacy).quality_profile=='baseline'


@pytest.mark.parametrize('profile',['baseline','spec03'])
def test_store_create_persists_exact_profile(profile):
    db=Mock()
    def flush():
        item=db.add.call_args.args[0]
        item.created_at=item.updated_at=datetime.now(timezone.utc)
    db.flush.side_effect=flush
    store=object.__new__(LenyStore);store.transaction=lambda:nullcontext(db);store.audit=Mock()
    result=store.create(LenyActor(7,9,'synthetic'),quality_profile=profile)
    assert result['quality_profile']==profile
    assert db.add.call_args.args[0].quality_profile==profile
    with pytest.raises(LenyError):store.create(LenyActor(7,9,'synthetic'),quality_profile='unknown')


def test_profile_lookup_checks_owner_and_does_not_change_provider_contract():
    actor=LenyActor(7,9,'synthetic');identity=uuid4();db=Mock()
    store=object.__new__(LenyStore);store.transaction=lambda:nullcontext(db)
    db.scalar.return_value=SimpleNamespace(quality_profile='spec03',llm_provider='gemini',llm_model='gemini-3.1-flash-lite')
    assert store.quality_profile_for(actor,identity)=='spec03'
    assert db.scalar.call_args.args[0].compile().params['user_id_1']==actor.user_id
    assert store.provider_for(actor,identity)==('gemini','gemini-3.1-flash-lite')
    db.scalar.return_value=None
    with pytest.raises(LenyError) as caught:store.quality_profile_for(actor,identity)
    assert caught.value.code=='LENY_NOT_FOUND'


@pytest.mark.parametrize('body',[None,{}])
def test_legacy_creation_uses_server_baseline(api,body):
    setup_api(api)
    kwargs={'headers':api.headers}
    if body is not None:kwargs['json']=body
    result=api.client.post('/leny/conversations',**kwargs)
    assert result.status_code==201 and result.json()['quality_profile']=='baseline'
    assert 'quality_profile' not in api.service.store.create.call_args.kwargs


@pytest.mark.parametrize('role',['CAJA','INV_BOUTIQUE','INV_TALLER','MODISTA'])
def test_normal_roles_use_server_default_without_evaluation_permission(api,role):
    setup_api(api,default='spec03',response='baseline');api.actor.rol.codigo=role
    result=api.client.post('/leny/conversations',json={},headers=api.headers)
    assert result.status_code==201 and result.json()['quality_profile']=='baseline'
    assert 'quality_profile' not in api.service.store.create.call_args.kwargs


@pytest.mark.parametrize('role',['CAJA','INV_BOUTIQUE','INV_TALLER','MODISTA'])
@pytest.mark.parametrize('profile',['baseline','spec03'])
def test_profile_override_requires_effective_admin_permission(api,role,profile):
    setup_api(api,evaluation=True);api.actor.rol.codigo=role
    result=api.client.post('/leny/conversations',json={'quality_profile':profile},headers=api.headers)
    assert result.status_code==(409 if profile=='spec03' else 201)
    if profile=='spec03':api.service.store.create.assert_not_called()


@pytest.mark.parametrize('profile',['baseline','spec03'])
def test_admin_cannot_override_when_evaluation_disabled(api,profile):
    setup_api(api)
    result=api.client.post('/leny/conversations',json={'quality_profile':profile},headers=api.headers)
    assert result.status_code==(409 if profile=='spec03' else 201)
    if profile=='spec03':
        assert result.json()['detail']['code']=='LENY_PROFILE_RETIRED'
        api.service.store.create.assert_not_called()


@pytest.mark.parametrize('profile',['baseline','spec03'])
def test_admin_evaluation_can_create_review_profile(api,profile):
    setup_api(api,evaluation=True,response=profile)
    result=api.client.post('/leny/conversations',json={'quality_profile':profile},headers=api.headers)
    assert result.status_code==(409 if profile=='spec03' else 201)
    if profile=='spec03':api.service.store.create.assert_not_called()
    else:assert result.json()['quality_profile']=='baseline'


def migration():
    p=Path(__file__).parents[1]/'alembic/versions/20261105_0025_leny_quality_profile.py'
    spec=importlib.util.spec_from_file_location('synthetic_0025',p)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_migration_changes_only_leny_with_historical_baseline_and_safe_downgrade(monkeypatch):
    module=migration();operations=Mock();monkeypatch.setattr(module,'op',operations)
    module.upgrade()
    assert module.down_revision=='20261105_0024'
    for name in ('add_column','create_check_constraint'):
        assert getattr(operations,name).call_args.kwargs['schema']=='leny'
    column=operations.add_column.call_args.args[1]
    assert column.name=='quality_profile' and column.server_default.arg=='baseline' and not column.nullable
    operations.get_bind.return_value.scalar.return_value=True
    with pytest.raises(RuntimeError,match='retain'):module.downgrade()
    operations.drop_column.assert_not_called()
    operations.get_bind.return_value.scalar.return_value=False
    module.downgrade()
    assert operations.drop_column.call_args.kwargs['schema']=='leny'
