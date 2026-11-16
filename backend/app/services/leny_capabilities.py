"""Backend-owned capability routing. No tools, SQL generation or dynamic dispatch."""
import re
import unicodedata
from difflib import get_close_matches

from app.services.leny_policy import PolicyDecision
from app.services.leny_rag_routing import candidate_decision, is_followup, document_intent

DOCUMENTARY = 'CONSULTA_DOCUMENTAL'
ADVICE = 'ASESORAMIENTO_EMPRESARIAL'
DRAFTING = 'REDACCIÓN_DOCUMENTAL'
MIXED = 'CONSULTA_MIXTA'
UNAVAILABLE = 'CAPACIDAD_NO_DISPONIBLE'
AMBIGUOUS = 'CONSULTA_REALMENTE_AMBIGUA'
CAPABILITIES = {'documents': True, 'advice': True, 'drafting': True,
                'transactional_sql': False, 'bi': False, 'ml': False, 'automl': False}


def normalize_business_question(message):
    """Search hint only. Original input still owns safety, history and identity."""
    vocabulary = ('primera', 'prueba', 'boutique', 'modista', 'encargada', 'confeccion', 'fecha', 'agendar')
    def correct(match):
        word = match.group()
        key = ''.join(c for c in unicodedata.normalize('NFKD', word.casefold()) if not unicodedata.combining(c))
        if len(key) < 5 or key in vocabulary:
            return word
        alternatives = get_close_matches(key, vocabulary, n=1, cutoff=.84)
        return alternatives[0] if alternatives else word
    hint = re.sub(r'\b[^\W\d_]+\b', correct, message)
    hint = re.sub(r'\bquedar\s+(la\s+)?fecha\b', r'acordar \1fecha', hint, flags=re.I)
    return hint


def appointment_question(message):
    hint = normalize_business_question(message)
    return (bool(re.search(r'\b(?:fecha|agend\w*|program\w*|coordinar|acordar)\b', hint, re.I)
        and re.search(r'\bprueba\b', hint, re.I))
        and not re.search(r'\b(?:examen|laboratorio|acad[eé]mic\w*|software|hack\w*|credencial\w*|contrase\w*|sql|permisos|ignora|elud\w*)\b', hint, re.I))


def synthesis_enabled(config):
    return (getattr(config, 'leny_rag_response_mode', '') == 'controlled-synthesis-v1'
            and getattr(config, 'leny_rag_profile', '') == 'rag4_v1')


def intent(message, history=()):
    drafting = bool(re.search(r'\b(?:hacer|crear|elaborar|iniciar|comenzar|redact\w*|escrib\w*|organizar|mejorar)\s+'
        r'(?:(?:un|el|mi|otro|este|ese)\s+)?(?:ejemplo de\s+)?(?:manual\w*|documento\w*|instrucciones|procedimiento\w*)\b', message, re.I))
    reference = bool(re.search(r'\b(?:según|segun|documento|publicado|publicada)\b|\b(?:el|del|ese|este) manual\b', message, re.I))
    if drafting:
        return MIXED if reference else DRAFTING
    if document_intent(message) and re.search(r'\b(?:recomienda\w*|aconseja\w*|sugiere|orientación general|ideas)\b', message, re.I):
        return MIXED
    if is_followup(message) and history:
        return DOCUMENTARY if history[-1].get('documentary', False) else ADVICE
    if (re.search(r'\b(?:resume|resumir|resumen|qu[eé] hace|funciones|responsabilidades)\b', message, re.I)
            and re.search(r'\b(?:encargad[ao]|modista|asesor(?:a)?|cargo)\b', message, re.I)):
        return DOCUMENTARY
    if document_intent(message) or re.search(r'\b(?:confecciona\w*|confección|vestidos?|fuste|can-can)\b', message, re.I):
        return DOCUMENTARY
    if appointment_question(message):
        return DOCUMENTARY
    return ADVICE


def route(message, history, enabled):
    # Keep the complete original message in the security classifier. An allowed
    # drafting clause never overrides a dangerous/unavailable/mixed request.
    from app.services.leny_policy import deterministic_decision, clauses
    for clause in [message, *clauses(message)]:
        safety = deterministic_decision(clause, history)
        if safety and safety.category in {'dangerous', 'manipulation', 'unavailable'}:
            # Reading documents is available; mutations/current data are not.
            if safety.category != 'unavailable' or safety.reason == 'private_current_data_unavailable' or re.search(
                    r'\b(?:elimina|borra|modifica|actualiza|ejecuta|desactiva|internet|base de datos)\b', clause, re.I):
                return safety
    if re.search(r'^\s*(?:por favor[, ]*)?(?:actualiza|registra|crea|elimina|borra|modifica|anula|cobra)\b.{0,100}\b(?:inventario|venta|pedido|pago|cliente|stock|cuenta|usuario)\w*\b', message, re.I):
        return PolicyDecision('unavailable', 'v11_capability_unavailable')
    if re.search(r'\b(?:predice|pronostica|entrena|ejecuta\s+(?:automl|sql|un modelo)|consulta\s+las\s+tablas)\b', message, re.I):
        return PolicyDecision('unavailable', 'v11_capability_unavailable')
    decision = candidate_decision(message, history, enabled)
    if enabled and (decision is None or decision.category == 'ambiguous'):
        if (intent(message, history) == DOCUMENTARY
                and re.search(r'\b(?:resume|resumen|funciones|responsabilidades|qu[eé] hace)\b', message, re.I)
                and re.search(r'\b(?:encargad[ao]|modista|asesor(?:a)?)\b', message, re.I)):
            return PolicyDecision('business', 'v11_documentary', documents=True)
    if enabled and (decision is None or decision.category == 'ambiguous'):
        from app.services.leny_rag_retrieval import explicit_document_title
        if explicit_document_title(message):
            # SQL must resolve publication/ACL before any source is exposed.
            # An unresolved title alone does not authorize general knowledge.
            return PolicyDecision('business', 'v11_named_document', documents=True)

    if decision is not None and (decision.category != 'business' or decision.mixed):
        return decision
    kind = intent(message, history)
    if decision is None and appointment_question(message) and len(clauses(message)) == 1:
        decision = PolicyDecision('business', 'boutique_fitting_appointment')
    if decision is None:
        return None
    return PolicyDecision('business', {
        DOCUMENTARY: 'v11_documentary', ADVICE: 'v11_advice',
        DRAFTING: 'v11_drafting', MIXED: 'v11_mixed'}[kind],
        documents=bool(enabled and decision.reason != 'identity_or_greeting'))


async def contextual_route(provider, message, history, *, documents=False):
    preflight = route(message, history, documents)
    if preflight is not None and preflight.category != 'business':
        return preflight
    from app.services.leny_policy import contextual_decision
    decision = await contextual_decision(provider, message, history, documents=documents,
        business_context=' Elaborar, iniciar o redactar un manual, procedimiento o ejemplo adaptable '
        'para la boutique es finalidad empresarial, aunque no mencione BELLAARTE. No requiere '
        'un documento existente. Confección, modista, fuste y can-can son actividades del taller. '
        'Prueba significa prueba de vestido por defecto en este asistente de confección: '
        'acordar/quedar la fecha o programar la primera prueba es consulta empresarial. '
        'Interpreta errores ortográficos y usa el tema del usuario, sin exigir el nombre de la empresa. '
        'No confundas falta de evidencia con falta de ámbito. Conserva todos los controles de seguridad.')
    if decision.category != 'business' or decision.mixed:
        return decision
    kind = intent(message, history)
    return PolicyDecision('business', 'v11_' + {
        DOCUMENTARY: 'documentary', ADVICE: 'advice', DRAFTING: 'drafting', MIXED: 'mixed'}[kind],
        documents=bool(documents))


GENERAL_INSTRUCTION = ('Este turno es orientación general o un ejemplo adaptable, no una política interna. '
    'Responde directamente con estructura o ejemplo útil cuando lo pidan. Marca el ejemplo como adaptable. '
    'No inventes datos empresariales: usa campos por completar. No atribuyas al negocio normas no verificadas.')
