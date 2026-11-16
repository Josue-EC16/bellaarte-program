"""Synthetic V1.1 retrieval contracts: no database, provider or private corpus."""
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services import leny_rag_retrieval as retrieval
from app.services.leny_rag_selection import plan_payload, preselect, evidence_scope_matches
from app.services.leny_ollama import LenyError


def row(**values):
    return dict(fragment_id=uuid4(), document_id=uuid4(), indexation_id=uuid4(),
                ordinal=0, text='Revisar medidas antes del corte.', title='Manual de confección',
                locator={'page': 1}, **values)


@pytest.mark.parametrize('question,title', [
    ('Documento EJEMPLO DE COMO INICIAR EL MANUAL, dime cómo iniciar.', 'EJEMPLO DE COMO INICIAR EL MANUAL'),
    ('Consulta el manual «Confección de vestidos».', 'Confección de vestidos'),
    ('Según el documento "Guía del taller", explica el corte.', 'Guía del taller'),
    ('Quiero un ejemplo de cómo iniciar un manual', None),
    ('Explícame el fuste de can-can según el manual', None),
])
def test_explicit_title_does_not_require_exact_case(question, title):
    assert retrieval.explicit_document_title(question) == title


def test_contextual_pool_does_not_discard_fourth_ranked_document():
    rows = [row() for _ in range(4)]
    assert len(preselect(rows)) == 3
    assert preselect(rows, contextual=True) == rows
    legacy = plan_payload('Responsabilidades', rows)
    improved = plan_payload('Responsabilidades', rows, contextual=True)
    assert 'title' not in legacy['candidates'][0]
    assert improved['candidates'][0]['title'] == rows[0]['title']
    assert improved['candidates'][0]['locator'] == rows[0]['locator']


def test_neighbors_respect_known_section_and_next_heading():
    seed = row()
    following = row()
    following.update(ordinal=1, locator={'style': 'Heading 2'})
    preceding = row()
    preceding.update(ordinal=-1, locator={'style': 'Heading 2'})
    neighbors = [following | {'seed_id': seed['fragment_id']}, preceding | {'seed_id': seed['fragment_id']}]
    result = retrieval._interleave_neighbors([seed], neighbors, 20, contextual=True)
    assert result == [seed, preceding]
    assert len(retrieval._interleave_neighbors([seed], neighbors, 20)) == 3
    assert not retrieval._same_section(seed | {'locator': {'section': 'MODISTA'}},
                                       following | {'locator': {'section': 'ASESORA'}})


class Result:
    def __init__(self, rows=()):
        self.rows = rows

    def mappings(self):
        return self.rows


class Database:
    def __init__(self, titles, hits):
        self.titles, self.hits, self.calls = titles, hits, []

    def execute(self, query, args):
        query = str(query)
        self.calls.append((query, args))
        if 'set_config' in query:
            return Result()
        return Result(self.titles if 'AS exact FROM eligible' in query else self.hits)


def service(monkeypatch, titles=(), hits=()):
    database = Database(titles, hits)

    @contextmanager
    def sessions():
        yield database

    config = SimpleNamespace(leny_rag_response_mode='controlled-synthesis-v1', leny_rag_profile='rag4_v1',
        leny_rag_ranking='hybrid', leny_rag_neighbor_chunks=False, leny_rag_candidates=20,
        leny_rag_search_timeout_seconds=2, leny_rag_model='existing', leny_rag_model_digest='existing')
    monkeypatch.setattr(retrieval, 'reader', lambda db, actor: None)
    return retrieval.RetrievalService(config, sessions), database


def test_unknown_or_inaccessible_title_never_falls_back_to_unrelated_hits(monkeypatch):
    instance, db = service(monkeypatch, hits=[row()])
    actor = SimpleNamespace(account_id=uuid4(), user_id=uuid4())
    assert instance.search(actor, [1.] * 1024, 'Documento Manual de corte, explica.') == []
    assert len(db.calls) == 2
    query, args = db.calls[-1]
    assert query.startswith(retrieval.ELIGIBLE)
    assert args['title_key'] == 'manual de corte'
    assert 'documento_roles_lectura' in query and "i.status='validated'" in query


def test_ambiguous_authorized_title_does_not_disclose_candidates(monkeypatch):
    instance, db = service(monkeypatch, titles=[{'document_id': uuid4(), 'exact': False} for _ in range(2)])
    actor = SimpleNamespace(account_id=uuid4(), user_id=uuid4())
    with pytest.raises(LenyError) as error:
        instance.search(actor, [1.] * 1024, 'Documento Manual de corte, explica.')
    assert error.value.code == 'LENY_RAG_TITLE_AMBIGUOUS'
    assert len(db.calls) == 2


@pytest.mark.parametrize('with_followup', [False, True])
def test_title_resolution_narrows_rrf_and_keeps_eligibility(monkeypatch, with_followup):
    identity = uuid4()
    hit = row()
    instance, db = service(monkeypatch, titles=[{'document_id': identity, 'exact': True}], hits=[hit])
    actor = SimpleNamespace(account_id=uuid4(), user_id=uuid4())
    ids = [identity] if with_followup else None
    assert instance.search(actor, [1.] * 1024, 'Documento Manual de corte, explica.', document_ids=ids) == [hit]
    query, args = db.calls[-1]
    assert args['title_documents'] == [str(identity)]
    assert ':title_documents' in query and "i.config->'query_policy'" in query
    assert 'semantic_hits' in query and '60+rank' in query
    if with_followup:
        assert ':topic_documents' in query


def test_title_key_normalizes_accents_whitespace_and_punctuation():
    assert retrieval._title_key('  GUÍA:   Confección / Taller ') == 'guia confeccion taller'


@pytest.mark.parametrize('question,text,expected', [
    ('Explica el inventario', 'Tarifa del servicio: Bs 250.', False),
    ('Explica el stock', 'Registrar las existencias antes de reponer.', True),
    ('Responsabilidades de la modista', 'Funciones de la asesora de moda: atender clientes.', False),
    ('Responsabilidades de la modista', 'Responsabilidades de la modista: revisar medidas.', True),
    ('Funciones de la modista', 'La asesora de moda debe coordinar con la modista.', False),
    ('Funciones de la modista', 'La modista debe revisar medidas.', True),
    ('Explica el bordado con hilo de oro', 'Procedimiento general: cortar y coser.', False),
    ('Explica el bordado con hilo de oro', 'Bordar con hilo de oro siguiendo el patrón.', True),
    ('Explica con fuentes el corte', 'Revisar las medidas antes de cortar.', True),
])
def test_scope_veto_catches_subject_actor_and_material_mismatch(question, text, expected):
    source = row()
    source.update(text=text, title='MODISTA Y ASESORA DE MODA')
    assert evidence_scope_matches(question, [source]) is expected


def test_role_attribution_requires_heading_or_subject_not_shared_title():
    source = row()
    source.update(text='Revisar las medidas.', title='FUNCIONES MODISTA Y ASESORA')
    assert not evidence_scope_matches('Responsabilidades de la modista', [source])
    source['locator'] = {'heading': 'MODISTA'}
    assert evidence_scope_matches('Responsabilidades de la modista', [source])
    source['locator'] = {'heading': 'ASESORA DE MODA'}
    assert not evidence_scope_matches('Responsabilidades de la modista', [source])
