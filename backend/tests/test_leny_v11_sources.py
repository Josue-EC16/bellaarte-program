"""Sparse citation identities stay stable; all selected evidence needs ACL."""
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.services.leny_ollama import LenyError
from app.services.leny_rag_sources import SourceService


def environment(monkeypatch):
    from app.services import leny_rag_sources
    monkeypatch.setattr(leny_rag_sources, 'reader', lambda *_: None)
    service = object.__new__(SourceService)
    service.config = SimpleNamespace(leny_rag_model='synthetic', leny_rag_model_digest='synthetic')
    rows = [{'fragment_id': uuid4()} for _ in range(3)]
    actor = SimpleNamespace(account_id=1, user_id=2)
    db = Mock()
    db.scalar.return_value = SimpleNamespace(id=uuid4())
    db.execute.return_value.scalars.return_value = [r['fragment_id'] for r in rows]
    service.documents = SimpleNamespace(lock=lambda: nullcontext(), transaction=lambda: nullcontext(db), audit=Mock())
    return service, actor, rows, db


def test_only_cited_sources_are_saved_without_renumbering(monkeypatch):
    service, actor, rows, db = environment(monkeypatch)
    service.persist(actor, uuid4(), rows, citation_ids={'S3'})
    saved = db.add.call_args.args[0]
    assert saved.ordinal == 3 and saved.fragment_id == rows[2]['fragment_id']
    assert db.add.call_count == 1


def test_uncited_but_selected_revoked_evidence_still_aborts(monkeypatch):
    service, actor, rows, db = environment(monkeypatch)
    db.execute.return_value.scalars.return_value = [rows[2]['fragment_id']]
    with pytest.raises(LenyError):
        service.persist(actor, uuid4(), rows, citation_ids={'S3'})
    db.add.assert_not_called()


def test_unknown_citation_cannot_be_persisted(monkeypatch):
    service, actor, rows, db = environment(monkeypatch)
    with pytest.raises(ValueError):
        service.persist(actor, uuid4(), rows, citation_ids={'S4'})
    db.add.assert_not_called()


@pytest.mark.parametrize('current_ids', ['all', 'partial', 'none'])
def test_followup_progress_requires_every_old_fragment_to_remain_authorized(monkeypatch, current_ids):
    from app.services import leny_rag_retrieval
    from app.services.leny_store import LenyStore
    actor = SimpleNamespace(account_id=1, user_id=2)
    previous_ids = [uuid4(), uuid4()]
    db = Mock()
    content = 'Previously synthesized wording. ' * 100
    db.scalar.return_value = SimpleNamespace(id=uuid4(), content=content)
    allowed = previous_ids if current_ids == 'all' else previous_ids[:1] if current_ids == 'partial' else []
    db.scalars.side_effect = [previous_ids, allowed]
    store = object.__new__(LenyStore)
    store.transaction = lambda: nullcontext(db)
    store.own = Mock()
    store.sources = SimpleNamespace(config=SimpleNamespace())
    reader = Mock()
    monkeypatch.setattr(leny_rag_retrieval, 'reader', reader)
    monkeypatch.setattr(leny_rag_retrieval, 'parameters', lambda *_: {'actor_account': 1})
    conversation = uuid4()
    result = store.followup_progress(actor, conversation, 'synthetic-v11')
    assert result == (content[:1200] if current_ids == 'all' else None)
    store.own.assert_called_once_with(db, actor, conversation)
    reader.assert_called_once_with(db, actor)
    sql, params = db.scalars.call_args.args
    assert 'published_indexation_id' in str(sql) and 'documento_roles_lectura' in str(sql)
    assert set(params['ids']) == {str(value) for value in previous_ids}


def test_followup_without_documentary_sources_does_not_reuse_old_wording(monkeypatch):
    from app.services import leny_rag_retrieval
    from app.services.leny_store import LenyStore
    db = Mock()
    db.scalar.return_value = SimpleNamespace(id=uuid4(), content='An ungrounded old answer.')
    db.scalars.return_value = []
    store = object.__new__(LenyStore)
    store.transaction = lambda: nullcontext(db)
    store.own = Mock()
    monkeypatch.setattr(leny_rag_retrieval, 'reader', lambda *_: None)
    assert store.followup_progress(SimpleNamespace(), uuid4(), 'synthetic-v11') is None
    assert db.scalars.call_count == 1


@pytest.mark.parametrize('anchor,allowed,expected', [
    ('¿Cómo se confecciona un vestido?', True, True),
    ('¿Cómo se confecciona un vestido?', False, False),
    ('¿Cómo organizar el inventario?', True, False),
    (None, True, False),
])
def test_followup_progress_requires_same_topic_as_well_as_current_acl(monkeypatch, anchor, allowed, expected):
    from app.services import leny_rag_retrieval
    from app.services.leny_store import LenyStore
    actor = SimpleNamespace(account_id=1, user_id=2)
    fragment_id = uuid4()
    db = Mock()
    db.scalar.return_value = SimpleNamespace(id=uuid4(), sequence=10, content='Previous documentary synthesis.')
    topic_result = Mock()
    topic_result.all.return_value = [SimpleNamespace(content='¿Y después?')] + (
        [SimpleNamespace(content=anchor)] if anchor else [])
    db.scalars.side_effect = [topic_result, [fragment_id], [fragment_id] if allowed else []]
    store = object.__new__(LenyStore)
    store.transaction = lambda: nullcontext(db)
    store.own = Mock()
    store.sources = SimpleNamespace(config=SimpleNamespace())
    monkeypatch.setattr(leny_rag_retrieval, 'reader', lambda *_: None)
    monkeypatch.setattr(leny_rag_retrieval, 'parameters', lambda *_: {})
    result = store.followup_progress(actor, uuid4(), 'synthetic-v11', topic_question='¿Cómo se confecciona un vestido?')
    assert result == ('Previous documentary synthesis.' if expected else None)
    assert db.scalars.call_count == (3 if anchor == '¿Cómo se confecciona un vestido?' else 1)
