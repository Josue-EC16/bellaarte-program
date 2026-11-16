"""Documentary output contracts independent of the model's semantic judgment."""
import json
import asyncio
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.services.leny_rag_grounding import (
    document_review, grounded_reply, unsupported_request,
)
from app.core.config import Settings
from app.services.leny_service import PreparedTurn
from app.services.leny_ollama import LenyError
from test_leny_security import service_mocks


def turn_for(question='Consulta la tarifa'):
    env = service_mocks(question)
    env.service.config = Settings(_env_file=None, leny_rag_profile='rag4_v1')
    env.service.retrieval = Mock()
    turn = PreparedTurn(env.service, env.actor, env.payload, uuid4(), [], env.provider, env.lease)
    return env, turn


def rows():
    doc, index = uuid4(), uuid4()
    return [dict(fragment_id=uuid4(), document_id=doc, indexation_id=index, ordinal=0,
                 locator={'paragraph': 1}, source_type='DOCX_PARAGRAPH',
                 text='1. Confirmar el diseño aprobado. 2. Tomar medidas con consentimiento.'),
            dict(fragment_id=uuid4(), document_id=doc, indexation_id=index, ordinal=1,
                 locator={'paragraph': 2}, source_type='DOCX_PARAGRAPH',
                 text='3. Trazar el patrón. 4. Coser las piezas aprobadas. Si hay diferencias, corregir.')]


def test_document_review_preserves_all_parts_and_separates_source_documents():
    source = rows()
    other = dict(source[0], fragment_id=uuid4(), document_id=uuid4(), indexation_id=uuid4(), text='Anticipo 31%.')
    review, groups = document_review('Explica el procedimiento', [source[1], other, source[0]])
    assert [part for doc in review['documents'] for part in doc['parts']] == [source[0]['text'], source[1]['text'], other['text']]
    assert [row for _, row in groups['D1']] == source
    assert [row for _, row in groups['D2']] == [other]


def test_response_uses_verbatim_runtime_sources_without_new_actors_numbers_or_conditions():
    source = rows()
    text, clarification = grounded_reply(source, 'answer')
    assert not clarification
    assert 'cliente' not in text and '40%' not in text
    assert source[0]['text'] in text and source[1]['text'] in text
    assert '[S1]' in text and '[S2]' in text


def test_source_order_is_physical_not_relevance_order_and_documents_stay_separate():
    source = rows()
    text, _ = grounded_reply([source[1], source[0]], 'answer')
    assert text.index('1. Confirmar') < text.index('3. Trazar')
    assert source[0]['text']+' [S2]' in text
    assert source[1]['text']+' [S1]' in text


def test_five_group_summary_preserves_every_step_condition_and_original_words():
    source = rows()
    source[1]['text'] += ' 5. Revisar. 6. Entregar solo con aprobación; registrar entrega.'
    text, _ = grounded_reply(source, 'summary_five')
    assert text.count('**Grupo ') == 5
    for phrase in ['diseño aprobado', 'consentimiento', 'piezas aprobadas',
                   'Si hay diferencias, corregir.', 'solo con aprobación; registrar entrega.']:
        assert phrase in text
    assert 'cliente' not in text


def test_decimal_values_and_condition_scope_are_not_split_into_invented_steps():
    source = [dict(fragment_id=uuid4(), text='Tarifa: Bs 312.50; anticipo 27%; saldo antes de entregar.')]
    text, _ = grounded_reply(source, 'answer')
    assert 'Bs 312.50; anticipo 27%; saldo antes de entregar. [S1]' in text


def test_counting_numbered_points_is_not_evidence_of_a_requested_quantity():
    assert unsupported_request('¿Cuántas pruebas se exigen?', rows())
    assert not unsupported_request('¿Qué pasos aparecen en la guía?', rows())
    assert not unsupported_request('¿Qué anticipo se establece?', [dict(text='Anticipo 27%.')])


def test_semantic_specialization_is_not_a_brittle_lexical_filter():
    assert not unsupported_request('Tomar medidas con consentimiento', rows())
    assert not unsupported_request('Leer la guía con citas verificables', rows())
    assert not unsupported_request('Revisar un vestido con encaje', [dict(text='Revisar el encaje antes de entregar.')])


def test_unrelated_price_does_not_supply_a_required_count_and_one_is_a_quantity():
    assert unsupported_request('¿Cuántas pruebas exige la guía?', [dict(text='1. Realizar prueba. Anticipo 40%.')])
    assert not unsupported_request('¿Cuántas pruebas exige la guía?', [dict(text='Se requiere una prueba de ajuste.')])


def test_source_markup_cannot_hide_conditions_or_supply_a_clickable_link():
    source = [dict(fragment_id=uuid4(), text='<!-- No entregar sin aprobación. --> [Entregar](https://example.invalid).')]
    text, _ = grounded_reply(source)
    assert '<!--' not in text and '\\<\\!--' in text
    assert '\\[Entregar\\]' in text
    assert 'No entregar sin aprobación.' in text and text.endswith('[S1]')


def test_joint_review_does_not_let_unrelated_document_dilute_the_direct_answer():
    env, turn = turn_for()
    source = rows()
    price = dict(source[0], fragment_id=uuid4(), document_id=uuid4(), text='Tarifa: Bs 312.50; anticipo 27%.')
    env.provider.classify.return_value = json.dumps({'aspect': 'price', 'scope': 'matched', 'relation': 'direct', 'sources': [3]})
    selected, _, verdict = asyncio.run(turn.review_candidates([*source, price]))
    assert selected == [price] and verdict == 'sufficient'
    assert env.provider.classify.await_count == 1
    payloads = [json.loads(call.args[0][-1]['content']) for call in env.provider.classify.await_args_list]
    assert len(payloads[0]['candidates']) == 3
    env.provider.stream.assert_not_called()


@pytest.mark.parametrize('raw', ['{}', '{"verdict":"unknown"}', '{"verdict":"sufficient","role":"ADMIN"}', '[]'])
def test_malformed_review_is_operational_error_not_missing_documentation(raw):
    env, turn = turn_for()
    env.provider.classify.return_value = raw
    with pytest.raises(LenyError) as error: asyncio.run(turn.review_candidates(rows()))
    assert error.value.code == 'LENY_RAG_REVIEW_INVALID'


def test_complete_procedure_cannot_silently_omit_unretrieved_parts():
    env, turn = turn_for('Explica todos los pasos del procedimiento')
    source = [dict(item, document_fragment_count=6) for item in rows()]
    env.provider.classify.return_value = '{"aspect":"procedure","scope":"matched","relation":"direct","sources":[1]}'
    with pytest.raises(LenyError) as error: asyncio.run(turn.review_candidates(source))
    assert error.value.code == 'LENY_RAG_CONTEXT_LIMIT'


def test_irrelevant_large_document_does_not_turn_actual_absence_into_context_error():
    env, turn = turn_for('Explica todos los pasos del procedimiento')
    env.provider.classify.return_value = '{"aspect":"general","scope":"missing","relation":"absent","sources":[]}'
    selected, _, verdict = asyncio.run(turn.review_candidates([dict(item, document_fragment_count=6) for item in rows()]))
    assert selected == [] and verdict == 'none'


def test_exact_reviewer_payload_is_measured_twice_when_outside_conservative_byte_bound():
    env, turn = turn_for()
    env.service.config.leny_rag_evidence_mode = 'adaptive'
    env.service.config.leny_rag_adaptive_token_probe = True
    env.service.config.leny_keep_alive = '0'
    source = [dict(item, text='Contenido documental autorizado. '*65) for item in rows()]
    turn.select_evidence = AsyncMock(return_value=(source, []))
    turn.measured_context = True
    env.provider.measure_prompt = AsyncMock(side_effect=[1700, 1701])
    with pytest.raises(LenyError) as error: asyncio.run(turn.review_candidates(source))
    assert error.value.code == 'LENY_RAG_CONTEXT_LIMIT'
    calls = env.provider.measure_prompt.await_args_list
    assert len(calls) == 2 and calls[0].args[0] == calls[1].args[0]
    assert [r['text'] for r in json.loads(calls[0].args[0][-1]['content'])['candidates']] == [item['text'] for item in source]
    env.provider.classify.assert_not_awaited()
