"""Synthetic paired contracts; not a claim of real-model semantic accuracy."""
import json
from uuid import uuid4

import pytest

from app.services.leny_rag_synthesis import schema_for, validate
from app.services.leny_rag_retrieval import section_packets, explicit_source_summary
from app.services.leny_rag_selection import verify_plan


def output(text, source='S1', support=None, limitation=''):
    return json.dumps({'blocks': [{'kind': 'documented', 'text': text, 'source': source,
                                  'support': support or ['P1_1']}], 'limitation': limitation})


def test_linked_heading_body_preserve_both_references_and_actor():
    rows = [{'text': 'Funciones de la modista', 'indexation_id': 'i'},
            {'text': 'Comprobar las medidas antes de cortar.', 'indexation_id': 'i'}]
    result = validate(output('La modista revisa las medidas antes del corte.', 'S2', ['P1_1', 'P2_1']),
                      rows, linked_support=True, verdict='sufficient')
    assert '[S1]' in result and '[S2]' in result
    rows[0]['indexation_id'] = 'other'
    with pytest.raises(ValueError, match='Invalid passage reference'):
        validate(output('La modista revisa medidas.', 'S2', ['P1_1', 'P2_1']), rows, linked_support=True)


def test_swapped_quantities_are_never_published_as_synthesized_facts():
    rows = [{'text': 'El tul requiere 5 metros.\n\nLa seda requiere 8 metros.', 'indexation_id': 'i'}]
    swapped = 'El tul requiere 8 metros y la seda 5 metros.'
    answer = validate(output(swapped, support=['P1_1', 'P1_2']), rows, linked_support=True)
    assert swapped not in answer
    assert 'El tul requiere 5 metros.' in answer and 'La seda requiere 8 metros.' in answer
    assert 'Datos exactos documentados' in answer


def test_quantity_in_uncited_passage_does_not_support_claim():
    rows = [{'text': 'Revisar el tul.\n\nLa seda requiere 8 metros.'}]
    with pytest.raises(ValueError, match='Unsupported claim'):
        validate(output('El tul requiere 8 metros.'), rows, linked_support=True)


def test_faithful_paraphrase_without_literal_markers_is_accepted():
    rows = [{'text': 'La modista corta únicamente después de aprobar las medidas.'}]
    answer = validate(output('La modista realiza el corte tras la aprobación de medidas.'), rows, linked_support=True)
    assert 'tras la aprobación' in answer
    with pytest.raises(ValueError, match='Unsupported actor'):
        validate(output('La asesora realiza el corte tras aprobar medidas.'), rows, linked_support=True)


def test_generation_cannot_invent_conflict_or_missing_details():
    rows = [{'text': 'La encargada coordina las pruebas de vestidos.'}]
    for invented in ('conflicting', 'missing_details'):
        answer = validate(output('La encargada organiza las pruebas.', limitation=invented), rows,
                          linked_support=True, verdict='sufficient')
        assert '**Alcance:**' not in answer
    answer = validate(output('La encargada organiza las pruebas.'), rows, linked_support=True, verdict='partial')
    assert 'solo parte' in answer


def test_linked_schema_is_bounded_and_compact():
    rows = [{'text': 'Comprobar medidas.', 'indexation_id': 'i'}, {'text': 'Preparar tela.', 'indexation_id': 'i'}]
    block = schema_for(rows, linked_support=True)['properties']['blocks']['items']
    assert 'anyOf' not in block
    assert block['properties']['support']['maxItems'] == 4
    assert set(block['properties']['support']['items']['enum']) == {'P1_1', 'P2_1'}


def test_section_dependency_consumes_slot_and_rejects_foreign_index():
    seed = dict(fragment_id=uuid4(), indexation_id='i', document_id='d', text='Comprobar medidas.',
                ordinal=1, source_type='DOCX_PARAGRAPH', locator={'block': 1})
    heading = dict(fragment_id=uuid4(), indexation_id='i', document_id='d', text='Funciones de la modista',
                   ordinal=0, source_type='DOCX_PARAGRAPH', locator={'block': 0, 'style': 'Heading2'})
    rows = section_packets([seed], [dict(heading, seed_id=seed['fragment_id'])])
    plan = json.dumps(dict(aspect='general', scope='matched', relation='direct', sources=[1]))
    chosen, _, _ = verify_plan(plan, rows)
    assert len(chosen) == 2
    assert section_packets([seed], [dict(heading, seed_id=seed['fragment_id'])], 1) == [seed]
    heading['indexation_id'] = 'foreign'
    assert section_packets([seed], [dict(heading, seed_id=seed['fragment_id'])]) == [seed]


def test_summary_intent_does_not_replace_specific_question():
    assert explicit_source_summary('Documento MANUAL DE CONFECCION, resume su contenido')
    assert not explicit_source_summary('Documento MANUAL DE CONFECCION, resume las funciones de la modista')
    assert not explicit_source_summary('Resume las funciones de la encargada')


def test_planner_reserves_space_for_heading_and_rejects_foreign_dependency():
    from app.services.leny_rag_selection import plan_schema
    heading = dict(fragment_id=uuid4(), indexation_id='same', text='Funciones de la modista')
    bodies = [dict(fragment_id=uuid4(), indexation_id='same', text='Revisar las medidas.',
                   context_fragment_id=heading['fragment_id']) for _ in range(5)]
    assert plan_schema(6, reserved_context=1)['properties']['sources']['maxItems'] == 4
    plan = json.dumps(dict(aspect='general', scope='matched', relation='direct', sources=[2, 3, 4, 5]))
    chosen, _, _ = verify_plan(plan, [heading, *bodies])
    assert len(chosen) == 5 and heading in chosen
    with pytest.raises(ValueError, match='another index'):
        verify_plan(plan, [dict(heading, indexation_id='foreign'), *bodies])


def test_numbered_pdf_continuation_is_separate_evidence_and_requires_real_boundary():
    from app.services.leny_rag_retrieval import numbered_page_continuation
    seed = dict(fragment_id=uuid4(), indexation_id='same', ordinal=2, source_type='PDF_TEXT',
                text='PROCEDIMIENTO 01\nRevisión sintética\n1. Comprobar las piezas.\n2. Preparar la base.')
    following = dict(fragment_id=uuid4(), seed_id=seed['fragment_id'], indexation_id='same', ordinal=3,
                     source_type='PDF_TEXT', text='3. Revisar las uniones.\n4. Confirmar el resultado.')
    assert numbered_page_continuation(seed, following)
    packet = section_packets([seed], [following])
    assert len(packet) == 2 and packet[0]['text'] == seed['text']
    assert packet[0]['context_fragment_id'] == following['fragment_id']
    plan = json.dumps(dict(aspect='procedure', scope='matched', relation='partial', sources=[1]))
    assert len(verify_plan(plan, packet)[0]) == 2
    for changed in (dict(following, indexation_id='other'), dict(following, ordinal=4),
                    dict(following, text='1. Comenzar otro procedimiento.')):
        assert not numbered_page_continuation(seed, changed)
    assert not numbered_page_continuation(dict(seed, text='1. Hacer algo.\n2. Revisarlo.'), following)


def test_uncertain_quantity_does_not_erase_independently_supported_answer():
    rows = [{'text': 'El tul requiere 5 metros.\n\nRevisar las medidas.'}]
    data = json.loads(output('El tul requiere 8 metros.'))
    data['blocks'].append({'kind': 'documented', 'text': 'Comprobar las medidas.', 'source': 'S1', 'support': ['P1_2']})
    answer = validate(json.dumps(data), rows, linked_support=True)
    assert '8 metros' not in answer and 'Comprobar las medidas' in answer
    assert 'No he podido verificar' in answer
    assert answer.response_scope == 'partial'
    assert 'cantidades' in answer


def test_changed_condition_is_not_emitted_as_documented_paraphrase():
    rows = [{'text': 'La modista corta solo después de aprobar las medidas.'}]
    wrong = 'La modista corta antes de aprobar las medidas.'
    with pytest.raises(ValueError, match='Unsupported claim'):
        validate(output(wrong), rows, linked_support=True)


def test_step_splitting_does_not_turn_entire_page_into_one_passage():
    from app.services.leny_rag_synthesis import source_passages
    row = {'text': 'Medidas estándar\n• Largo: 5 cm.\n• Ancho: 8 cm.\n1. Revisar las medidas.\n2. Preparar las piezas.'}
    pieces = source_passages(row, 1, structured=True)
    assert len(pieces) >= 4
    assert any(text.strip() == '• Largo: 5 cm.' for _, text in pieces)


def test_uppercase_section_boundary_does_not_contaminate_previous_condition():
    from app.services.leny_rag_synthesis import source_passages
    row = {'text': '• El volumen debe ser uniforme.\nIMPORTANTE\nTodo personal nuevo deberá:\n1. Leer el procedimiento.'}
    pieces = source_passages(row, 1, structured=True)
    first = next(text for _, text in pieces if 'volumen' in text)
    assert 'IMPORTANTE' not in first and 'personal' not in first
    assert first.strip() in row['text']


def test_all_generation_counts_accumulate_and_embedding_does_not_borrow_them():
    from types import SimpleNamespace
    from app.services.leny_inference_state import ManagedProvider
    provider = SimpleNamespace(config=SimpleNamespace(leny_model='qwen'),
                               metrics={'prompt_eval_count': 30, 'eval_count': 8})
    wrapped = ManagedProvider(provider, None, None, None, lambda: 1)
    wrapped._record_metrics('qwen', 'classifier')
    wrapped._record_metrics('embedding', 'query_embedding')
    provider.metrics = {'prompt_eval_count': 70, 'eval_count': 12}
    wrapped._record_metrics('qwen', 'generation')
    assert wrapped.aggregate_metrics == dict(inference_calls_total=3, prompt_tokens_total=100,
        output_tokens_total=20, calls_without_token_counts=1)


def test_failed_generation_does_not_count_previous_call_metrics_again():
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import Mock
    from app.services.leny_inference_state import ManagedProvider
    provider = SimpleNamespace(config=SimpleNamespace(leny_model='qwen'),
                               metrics={'prompt_eval_count': 30, 'eval_count': 8})
    state = Mock()
    state.start.return_value = False
    wrapped = ManagedProvider(provider, state, None, None, lambda: 1)
    async def fail():
        raise ValueError('synthetic failed inference')
    with pytest.raises(ValueError):
        asyncio.run(wrapped.call(fail, 'qwen', 'generation', lambda: True))
    assert wrapped.aggregate_metrics == dict(inference_calls_total=1, prompt_tokens_total=0,
        output_tokens_total=0, calls_without_token_counts=1)


def test_general_single_pass_has_no_company_evidence_and_blocks_internal_claims():
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from app.services.leny_rag_synthesis import synthesize_general
    config = SimpleNamespace(leny_num_ctx=4096, leny_num_predict=768)
    raw = json.dumps(dict(blocks=[dict(kind='general', text='Como orientación general, revisa el diseño y prepara las piezas.',
        source='', support=[])], limitation=''))
    provider = SimpleNamespace(structured=AsyncMock(return_value=raw), finish_reason='stop')
    answer = asyncio.run(synthesize_general(provider, config, '¿Qué podría hacer una modista?'))
    assert answer.response_scope == 'general' and 'sin respaldo documental empresarial' in answer
    assert '[S1]' not in answer and provider.structured.await_count == 1
    internal = json.loads(raw)
    internal['blocks'][0]['text'] = 'En nuestra empresa, la modista revisa el diseño.'
    provider.structured.return_value = json.dumps(internal)
    with pytest.raises(ValueError, match='Internal claim'):
        asyncio.run(synthesize_general(provider, config, '¿Qué hace la modista?'))


def test_explicit_mutation_is_unavailable_but_how_to_guidance_is_not_a_mutation():
    from app.services.leny_capabilities import route
    assert route('Actualiza el inventario y registra una venta nueva en el ERP.', [], True).category == 'unavailable'
    result = route('¿Cómo puedo organizar el inventario?', [], True)
    assert result is None or result.category != 'unavailable'


def test_general_long_bounded_template_is_not_rejected_for_example_labels():
    text = ('Definir propósito y alcance. ' * 40)+'\\n\\nEjemplo 1: Título del manual [Nombre].\\nVersión: 1.0\\nPaso 1: [Descripción].'
    raw = json.dumps(dict(blocks=[dict(kind='example', text=text, source='', support=[])], limitation=''))
    result = validate(raw, [], allow_general=True, linked_support=True)
    assert result.response_scope == 'general' and '\\n' not in result
    assert 'Versión: [por definir]' in result and 'Paso 1:' in result
    unsupported = json.loads(raw)
    unsupported['blocks'][0]['text'] = 'Pagar 500 bolivianos por el manual.'
    with pytest.raises(ValueError):
        validate(json.dumps(unsupported), [], allow_general=True, linked_support=True)
    unsupported['blocks'][0]['text'] = 'No existe un documento oficial que describa ese procedimiento.'
    with pytest.raises(ValueError, match='Internal claim'):
        validate(json.dumps(unsupported), [], allow_general=True, linked_support=True)
