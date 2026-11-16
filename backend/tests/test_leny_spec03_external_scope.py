"""External approval is version-bound and does not replace SQL ACL."""
import json
from types import SimpleNamespace
from uuid import uuid4
import pytest
from app.services.leny_external_scope import approved_versions,require_approved
from app.services.leny_llm_contracts import LenyError


def configuration(tmp_path,monkeypatch):
    from app.services import leny_document_storage
    monkeypatch.setattr(leny_document_storage,'_check_path',lambda _:None)
    row=dict(document_id=str(uuid4()),version_id=str(uuid4()),indexation_id=str(uuid4()),sha256='a'*64)
    path=tmp_path/'approved.json';path.write_text(json.dumps(dict(format_version=1,versions=[row])),encoding='utf-8')
    return SimpleNamespace(leny_gemini_corpus_manifest=str(path)),row


@pytest.mark.parametrize('field',['document_id','version_id','indexation_id','sha256'])
def test_new_document_version_index_or_content_never_inherits_external_permission(tmp_path,monkeypatch,field):
    config,row=configuration(tmp_path,monkeypatch)
    require_approved(config,[row])
    changed=dict(row);changed[field]='b'*64 if field=='sha256' else str(uuid4())
    with pytest.raises(LenyError) as caught:require_approved(config,[changed])
    assert caught.value.code=='LENY_EXTERNAL_NOT_APPROVED'


def test_external_filter_is_applied_before_title_and_ranking(tmp_path,monkeypatch):
    from app.services.leny_rag_retrieval import eligible_for,ELIGIBLE
    assert eligible_for(SimpleNamespace(leny_llm_provider='ollama'))==ELIGIBLE
    query=eligible_for(SimpleNamespace(leny_llm_provider='gemini'))
    assert 'jsonb_to_recordset(CAST(:external_grants AS jsonb))' in query
    assert 'g.version_id=v.id' in query and 'g.indexation_id=i.id' in query and 'g.sha256=v.sha256' in query
    assert 'documento_roles_lectura' in query and 'published_indexation_id' in query
    narrowed=query.replace("WHERE d.state='active'","WHERE d.id=ANY(CAST(:title_documents AS uuid[])) AND d.state='active'")
    assert ':title_documents' in narrowed and ':external_grants' in narrowed


def test_missing_or_invalid_approval_fails_closed(tmp_path,monkeypatch):
    with pytest.raises(LenyError):approved_versions(SimpleNamespace(leny_gemini_corpus_manifest=None))
    config,row=configuration(tmp_path,monkeypatch)
    from pathlib import Path
    Path(config.leny_gemini_corpus_manifest).write_text('not json')
    with pytest.raises(LenyError) as caught:require_approved(config,[row])
    assert caught.value.code=='LENY_EXTERNAL_APPROVAL_INVALID'


@pytest.mark.parametrize('payload',[
    {'evidence':[{'text':'Contacto: persona@example.invalid'}]},
    {'metadata':{'description':'CI: 12345678'}},
    {'conversation':[{'content':'teléfono: 71234567'}]},
])
def test_sensitive_evidence_metadata_and_history_never_reach_google(payload):
    import asyncio
    from unittest.mock import AsyncMock
    from test_leny_gemini_provider import environment
    env=environment();operation=AsyncMock()
    with pytest.raises(LenyError) as caught:
        asyncio.run(env.provider._call(operation,'generate',100,json.dumps(payload,ensure_ascii=False)))
    assert caught.value.code=='LENY_GEMINI_SENSITIVE'
    operation.assert_not_awaited();env.usage.reserve.assert_not_called()
