"""Evidence references/limits, independently of Qwen's semantic judgment."""
import json
from uuid import uuid4

import pytest

from app.services.leny_rag_selection import preselect, verify_plan
from app.services.leny_rag_grounding import unsupported_request


def rows():
    return [dict(document_id=uuid4(), fragment_id=uuid4(), ordinal=0, text=text) for text in
            ['Reposición: mínimo 17 unidades. Registrar diferencias.',
             'Precio Bs 315.50; anticipo 27%.', 'Duración: dos días laborables.',
             'Organizar paquetes por pedido.']]


def test_preselection_bounds_distinct_documents_not_parts_and_does_not_mutate():
    source = rows()
    part = dict(source[0], fragment_id=uuid4(), ordinal=1, text='No contar unidades dañadas.')
    assert preselect([*source, part]) == [source[0], part, source[1], source[2]]
    assert len(source) == 4


def test_selector_only_returns_bounded_source_identities_never_generated_facts():
    source = rows()
    selected, verdict, relation = verify_plan(json.dumps(dict(aspect='general', scope='matched', relation='direct', sources=[1])), source)
    assert selected == source[:1] and verdict == 'sufficient' and relation == 'direct'
    for ids in [[8], [True], [1, 1], [{}], [1, 2, 3, 4, 5, 6]]:
        with pytest.raises(ValueError): verify_plan(json.dumps(dict(aspect='general', scope='matched', relation='direct', sources=ids)), source)
    with pytest.raises(ValueError):
        verify_plan(json.dumps(dict(aspect='general', scope='matched', relation='direct', sources=[1], answer='mínimo 23 unidades')), source)


@pytest.mark.parametrize('relation', ['absent', 'tangential'])
def test_tangential_evidence_is_not_a_partial_answer(relation):
    assert verify_plan(json.dumps(dict(aspect='general', scope='matched', relation=relation, sources=[])), rows()) == ([], 'none', relation)
    with pytest.raises(ValueError): verify_plan(json.dumps(dict(aspect='general', scope='matched', relation=relation, sources=[2])), rows())


def test_duration_needs_time_units_and_cannot_be_inferred_from_money_or_list_numbers():
    assert unsupported_request('Indica el plazo exacto de ajuste', rows()[:2])
    assert not unsupported_request('Indica el plazo exacto de ajuste', rows()[2:3])


def test_comparison_keeps_both_sides_even_when_one_ranks_after_third_document():
    source = rows()
    assert preselect(source, question='Compara los documentos vigentes') == source
    assert preselect(source) == source[:3]


def test_contradiction_requires_distinct_documents_but_not_certified_just_by_that():
    source = rows()
    with pytest.raises(ValueError):
        verify_plan(json.dumps(dict(aspect='general', scope='matched', relation='contradictory', sources=[2])), source)
    source[1]['document_id'] = source[0]['document_id']
    with pytest.raises(ValueError):
        verify_plan(json.dumps(dict(aspect='general', scope='matched', relation='contradictory', sources=[1, 2])), source)


@pytest.mark.parametrize('aspect', ['price', 'quantity', 'timing', 'condition', 'procedure', 'specialty', 'general'])
def test_requested_aspect_is_typed_and_never_adds_facts(aspect):
    source = rows()
    selected, verdict, _ = verify_plan(json.dumps(dict(aspect=aspect, scope='matched',
        relation='partial', sources=[1])), source)
    assert selected == source[:1] and verdict == 'partial'


@pytest.mark.parametrize('scope', ['broader', 'missing', 'unclear'])
def test_broader_scope_cannot_be_rendered_as_partial_evidence(scope):
    raw = dict(aspect='specialty', scope=scope, relation='partial', sources=[])
    assert verify_plan(json.dumps(raw), rows()) == ([], 'none', 'partial')
    raw['sources'] = [1]
    with pytest.raises(ValueError):
        verify_plan(json.dumps(raw), rows())


@pytest.mark.parametrize('field,value', [('aspect', 'execute_sql'), ('scope', 'admin'), ('aspect', []), ('scope', {})])
def test_unknown_aspect_or_scope_is_invalid_not_semantic_absence(field, value):
    raw = dict(aspect='general', scope='matched', relation='direct', sources=[1])
    raw[field] = value
    with pytest.raises((ValueError, TypeError)):
        verify_plan(json.dumps(raw), rows())
