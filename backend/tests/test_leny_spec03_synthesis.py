import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from app.services.leny_spec03_synthesis import validate,synthesize
from app.services.leny_spec03_context import reference_kind,interpret,ConversationContext


EMPTY=dict(value='',unit='',subject='',condition='',quote='')
def claim(text,refs=('P1_1',),**quantity):
    return dict(kind='documented',text=text,support=list(refs),quantity=EMPTY|quantity)
def raw(*claims,coverage='documented'):
    return json.dumps(dict(claims=list(claims),coverage=coverage,missing=''))
def rows(*texts):return [dict(text=value,fragment_id=uuid4(),indexation_id=uuid4(),locator={}) for value in texts]


def test_faithful_paraphrase_is_interpreted_not_literal():
    source=rows('La modista comprueba las medidas antes del corte.')
    result=validate(raw(claim('La modista revisa las medidas antes de cortar.')),source)
    assert 'revisa las medidas' in result and '[S1]' in result and 'comprueba' not in result


def test_numeric_fact_keeps_its_subject_unit_and_quote_without_extract_fallback():
    source=rows('Se necesitan 5 metros de tul.')
    result=validate(raw(claim('Para el tul se necesitan 5 metros.',value='5',unit='metros',subject='tul',quote=source[0]['text'])),source)
    assert 'Para el tul se necesitan 5 metros.' in result
    assert 'Datos exactos documentados' not in result


def test_magnitude_is_distinct_from_day_unit():
    source=rows('La prueba se realiza en 5 días.')
    assert '[S1]' in validate(raw(claim('La prueba se realiza en 5 días.',value='5',unit='días',
        subject='prueba',quote=source[0]['text'])),source)


def test_nonnumeric_claim_does_not_emit_auxiliary_numeric_annotations():
    source=rows('Confirmar las medidas antes del corte.')
    result=validate(raw(claim('Revisar las medidas antes de cortar.',subject='medidas',quote=source[0]['text'])),source)
    assert '[S1]' in result


def test_role_comes_from_explicit_counted_heading_fragment_not_filename():
    source=rows('Funciones de la encargada','Coordinar las pruebas.')
    source[1]['indexation_id']=source[0]['indexation_id']
    source[1]['context_fragment_id']=source[0]['fragment_id']
    result=validate(raw(claim('La encargada organiza las pruebas.',refs=('P2_1',))),source)
    assert '[S1]' in result and '[S2]' in result
    source[1].pop('context_fragment_id')
    source[1]['title']='Funciones de la encargada'
    with pytest.raises(ValueError,match='Unsupported actor'):
        validate(raw(claim('La encargada organiza las pruebas.',refs=('P2_1',))),source)


@pytest.mark.parametrize('value,subject,quote',[
 ('8','tul','Se necesitan 8 metros de seda.'),
 ('5','seda','Se necesitan 5 metros de tul.'),
 ('5','tul','Se necesitan 5 metros de tul y 8 metros de seda.')])
def test_two_cited_passages_cannot_swap_material_quantities(value,subject,quote):
    source=rows('Se necesitan 5 metros de tul.','Se necesitan 8 metros de seda.',quote)
    with pytest.raises(ValueError,match='Unsupported claim'):
        validate(raw(claim(f'Para el {subject} se necesitan {value} metros.',refs=('P1_1','P2_1','P3_1'),value=value,unit='metros',subject=subject,quote=quote)),source)


def test_wrong_role_and_nonexistent_reference_remain_blocked():
    with pytest.raises(ValueError,match='Unsupported actor'):
        validate(raw(claim('La modista orienta a la clienta.')),rows('La asesora orienta a la clienta.'))
    with pytest.raises(ValueError,match='Invalid passage reference'):
        validate(raw(claim('Revisar las medidas.',refs=('P9_1',))),rows('Revisar las medidas.'))


def test_roles_cannot_exchange_a_quantity_by_citing_both():
    source=rows('La modista utiliza 5 metros de tela.','La encargada utiliza 8 metros de tela.')
    with pytest.raises(ValueError,match='Unsupported claim'):
        validate(raw(claim('La modista utiliza 8 metros de tela.',refs=('P1_1','P2_1'),
            value='8',unit='metros',subject='tela',quote=source[1]['text'])),source)


def test_distinct_roles_must_not_borrow_each_others_functions():
    source=rows('La modista cose.','La asesora coordina la prueba.')
    with pytest.raises(ValueError,match='Unsupported claim'):
        validate(raw(claim('La modista coordina la prueba.',refs=('P1_1','P2_1'))),source)
    assert '[S2]' in validate(raw(claim('La asesora organiza la prueba.',refs=('P2_1',))),source)


def test_temporal_dependency_accepts_paraphrase_but_not_omission():
    source=rows('La modista corta la tela solo después de confirmar las medidas.')
    with pytest.raises(ValueError,match='Unsupported claim'):
        validate(raw(claim('La modista corta la tela.')),source)
    assert '[S1]' in validate(raw(claim('La modista corta la tela una vez confirmadas las medidas.')),source)


def test_general_example_is_marked_without_company_sources():
    result=validate(raw(dict(kind='example',text='Puedes comenzar definiendo propósito y alcance.',support=[],quantity=EMPTY),coverage='general'),[],allow_general=True,verdict='none')
    assert result.response_scope=='general' and 'sin respaldo documental empresarial' in result and '[S' not in result


def test_negative_condition_is_not_silently_removed():
    with pytest.raises(ValueError,match='Unsupported claim'):
        validate(raw(claim('La modista debe cortar la tela.')),rows('La modista no debe cortar la tela.'))


@pytest.mark.parametrize('question,kind',[('¿Y después?','next'),('¿Quién se encarga de hacerlo?','responsible'),('¿Dónde está documentado eso?','sources'),('Explícame mejor ese último paso.','detail'),('Resúmeme todo el procedimiento.','summary'),('Resume las funciones de la modista.',None)])
def test_conversation_reference_presentation_is_not_a_permission(question,kind):
    assert reference_kind(question)==kind


def test_invalid_interpretation_cannot_replace_backend_scope():
    provider=SimpleNamespace(classify=AsyncMock(return_value='{"intent":"execute_sql"}'))
    from app.services.leny_llm_contracts import LenyError
    with pytest.raises(LenyError):asyncio.run(interpret(provider,'¿Y después?',ConversationContext()))


def test_synthesis_records_local_upper_estimates_and_validation_without_extra_calls():
    from app.services.leny_rag_diagnostics import RagDiagnostics
    provider=SimpleNamespace(measure_prompt=AsyncMock(return_value=1000),
        structured=AsyncMock(return_value=raw(claim('Revisar las medidas antes de cortar.'))),finish_reason='stop')
    config=SimpleNamespace(leny_llm_provider='gemini',leny_gemini_input_token_budget=32678)
    diagnostics=RagDiagnostics('rag4_v1')
    result=asyncio.run(synthesize(provider,config,'Cómo cortar',rows('Revisar las medidas antes del corte.'),
        'sufficient',diagnostics=diagnostics))
    assert '[S1]' in result
    provider.structured.assert_awaited_once()
    assert diagnostics.counts['synthesis_evidence_token_upper_estimate']>0
    assert diagnostics.durations['validation']>=0
