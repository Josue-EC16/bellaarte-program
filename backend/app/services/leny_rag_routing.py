"""Candidate routing separates safety, business scope and documentary capability.

Every approval still passes SQL ACL. Previous user questions are topic hints,
never old evidence, privileges, rewritten instructions or assistant answers.
"""
from __future__ import annotations

import json
import re

from app.services.leny_guard import normalized
from app.services.leny_policy import (
    PolicyDecision, capability_decision, contextual_decision, document_intent,
    clauses,
)

# Old candidate selections may have anchored a tangential document. Keep their
# history visible, but never treat those references as the new policy's topic.
RAG4_POLICY_VERSION = 'rag4-v4'
FOLLOWUP = re.compile(
    r'^(?:y\s+)?(?:despu[eé]s|luego|qu[eé] sigue|cu[aá]l es la siguiente etapa|'
    r'(?:expl[ií]came|describe|contin[uú]a con) (?:la )?siguiente (?:etapa|fase)|'
    r'res[uú]melo(?: en (?:cinco|5) pasos)?|contin[uú]a(?: con (?:ese|el|este) (?:procedimiento|proceso))?|'
    r'qu[eé] ocurre antes de entregarlo|si hay diferencias en la prueba|'
    r'sigue siendo v[aá]lido despu[eé]s del cambio de permisos|'
    r'contin[uú]a (?:la tarifa|el procedimiento) despu[eé]s de (?:revocar la acl|retirar su publicaci[oó]n)|'
    r'y el siguiente paso)[\s¿?¡!.,]*$', re.I)
FORMAT = re.compile(
    r'^(?:(?:por favor|y|adem[aá]s)[, ]+)*(?:responde|contesta|presenta|organiza|explica|'
    r'expr[eé]salo|res[uú]melo|resume (?:lo anterior|la respuesta))\s+'
    r'(?:brevemente|con (?:sus |las |tus )?fuentes|con citas|en (?:una tabla|tabla|'
    r'cinco pasos|5 pasos|una lista|vi[nñ]etas|espa[nñ]ol)|de forma breve)'
    r'(?:\s+(?:y|con|en)\s+(?:sus fuentes|fuentes|citas|cinco pasos|5 pasos|tabla|una tabla))*[.!?]*$', re.I)
GARMENT = re.compile(r'\b(?:vestidos?|faldas?|prendas?|ropa|encajes?|ajustes?|confecci[oó]n|confecciona\w*|costura|'
                     r'costurera|modista|medidas|patrones?|pruebas|telas?|corte|bordad[oa]s?)\b', re.I)
PROCEDURE = re.compile(r'\b(?:c[oó]mo|pasos?|proceso|etapas?|plazo|qu[eé] (?:se hace|hago|hacemos|viene entre)|'
                       r'prepara\w*|entrega\w*|ajusta\w*|hacen|confecciona\w*)\b', re.I)
GENERAL = re.compile(r'\b(?:qu[eé] (?:es|significa)|definici[oó]n|concepto|f[oó]rmula|'
                     r'calcula\w*|recomendaciones generales|orientaci[oó]n general|'
                     r'hipot[eé]tic[oa]s?|margen de utilidad|punto de equilibrio|descuento porcentual|'
                     r'[ií]ndice en postgresql|proteger el erp|redacta|escribe un ejemplo)\b', re.I)
DOCUMENT_REFERENCE = re.compile(r'\b(?:gu[ií]as?|tarifas?|circulares?|instructivos?|normativa|'
                                 r'reglamento|publicaci[oó]n|pol[ií]tica interna|fragmentos?)\b', re.I)
FINANCIAL_REFERENCE = re.compile(r'\b(?:tarifas?|anticipos?|saldos?|precios?)\b', re.I)
OPERATIONAL_REFERENCE = re.compile(r'\b(?:registr\w*.{0,25}diferencias|umbral de reposici[oó]n|'
                                   r'cuentas individuales)\b', re.I)


def candidate_enabled(config):
    return getattr(config, 'leny_rag_profile', 'legacy') == 'rag4_v1'


def retrieval_question(message):
    """Remove a trailing claimed role from search intent, never from authorization.

    The original message still passes every security classifier. A role label
    is not business subject matter and must not dominate a query embedding or
    cause the evidence reviewer to perform a fictitious permission check.
    """
    return re.sub(r'\s+(?:como|con el rol)\s+(?:ADMIN|CAJA|INV_BOUTIQUE|INV_TALLER|MODISTA)\s*[.!?]*$',
                  '', message, flags=re.I)


def policy_version(config):
    from app.services.leny_policy import POLICY_VERSION
    return RAG4_POLICY_VERSION if candidate_enabled(config) else POLICY_VERSION


def is_followup(message):
    return bool(FOLLOWUP.fullmatch(normalized(message).strip(' ¿¡')))


def without_format(message):
    """Only discard recognized presentation-only clauses from scope analysis."""
    parts = clauses(message)
    substantive = [part for part in parts if not FORMAT.fullmatch(part)]
    return '\n'.join(substantive) if substantive else message


def documentary_route(message, history=()):
    text = normalized(message)
    if document_intent(message) or DOCUMENT_REFERENCE.search(text):
        return True
    if is_followup(message):
        return bool(history)
    if GENERAL.search(text):
        return False
    # Called only after independent business approval, never as an authorization
    # or scope classifier. Specific business requests may have useful evidence
    # even without matching a procedural verb, document noun or exact title.
    return True


def candidate_decision(message, history, enabled):
    text = normalized(message)
    # Critical integrity restrictions precede semantic scope analysis. These
    # recognize explicit directives, not every mention of ACL, prompts or SQL.
    override = re.search(r'(?:saltarte|s[aá]ltate|ignora|omite|elude|desactiva).{0,55}(?:la acl|permisos|autorizaci[oó]n)|'
        r'\[(?:system|developer|tool)\].{0,90}(?:cambia|ejecuta|ignora|revela)|'
        r'(?:usa|cita|inventa|fabrica).{0,50}(?:fuente inventada|fuentes inventadas|citas falsas)|'
        r'(?:ahora soy|finge que soy|simula que soy).{0,25}admin.{0,70}(?:aunque|sin permiso)|'
        r'(?:revela|muestra|divulga).{0,40}(?:la contrase[nñ]a|credenciales|secretos).{0,40}(?:obed[eé]ce|ordena)', text)
    defensive = re.search(r'(?:c[oó]mo|para) (?:prevenir|evitar|detectar|proteger)|prevenci[oó]n de', text)
    if override and not defensive:
        return PolicyDecision('manipulation', 'suspected_authorization_or_evidence_override')
    unauthorized_read = re.search(r'\b(?:accede|entra|extrae|obt[eé]n|descarga)\b.{0,65}'
        r'(?:datos (?:privados )?de otros usuarios|cuentas ajenas|sin autorizaci[oó]n)', text)
    if unauthorized_read and not defensive:
        return PolicyDecision('dangerous', 'unauthorized_access_request')
    # Original content is checked first, including all apparent format clauses.
    original = capability_decision(message, history, enabled)
    if original and original.category in {'manipulation', 'dangerous', 'out_of_scope', 'unavailable'}:
        return original
    clean = without_format(message)
    decision = capability_decision(clean, history, enabled)
    if decision and decision.category in {'manipulation', 'dangerous', 'out_of_scope', 'unavailable'}:
        return decision
    if is_followup(clean):
        documentary = bool(enabled and history and history[-1].get('documentary', True))
        return (PolicyDecision('business', 'rag_followup' if documentary else 'general_followup', documents=documentary) if history
                else PolicyDecision('ambiguous', 'followup_without_topic'))
    # Clothing procedures are native business intent even without the ERP name.
    if decision is None and GARMENT.search(clean) and PROCEDURE.search(clean):
        # No automatic override of genuinely mixed or independently unknown clauses.
        if len(clauses(clean)) == 1:
            decision = PolicyDecision('business', 'garment_procedure')
    if (decision is None and (FINANCIAL_REFERENCE.search(clean) or OPERATIONAL_REFERENCE.search(clean)
            or document_intent(clean) and re.search(r'\breserva\b', clean, re.I))
            and not re.search(r'\b(?:hack\w*|vulner\w*|elud\w*|burl\w*|roba\w*|'
                              r'exfiltr\w*|contrase[nñ]a\w*|permisos?|acl|revoc\w*)\b', clean, re.I)
            and not re.search(r'\b(?:poema|cuento|novela|ficci[oó]n recreativa)\b', clean, re.I)
            and len(clauses(clean)) == 1):
        decision = PolicyDecision('business', 'operational_business_context')
    if decision and decision.category == 'business':
        return PolicyDecision('business', decision.reason, decision.mixed,
                              bool(enabled and decision.reason != 'identity_or_greeting' and documentary_route(clean, history)))
    return decision


async def contextual_route(provider, message, history, *, documents=False):
    # Reuse the conservative scope reviewer; do not let a routing classifier
    # authorize tools or replace the original user question.
    business_context = (' BELLAARTE BOUTIQUE confecciona y ajusta vestidos: prenda, patronaje, medidas, '
        'hilvanado, pruebas, retoques y entrega son contexto operativo empresarial, aunque no mencione ERP o empresa. '
        'Clasifica la finalidad, no si sabes la respuesta: las consultas sobre guías operativas, tarifas, anticipos, '
        'saldos, organización de taller o cuentas individuales tienen finalidad empresarial. '
        'No hace falta conocer el título ni el texto de una guía para reconocer esa finalidad; '
        'la recuperación posterior comprobará si existe evidencia autorizada. Un ejemplo ficticio empresarial '
        'no equivale a literatura recreativa. '
        'Los pedidos de formato (tabla, lista, brevedad, cinco pasos, fuentes) no son un tema ajeno adicional. '
        'Esta información describe el negocio, no concede permisos ni herramientas.')
    decision = await contextual_decision(provider, without_format(message), history, documents=documents,
                                         business_context=business_context)
    if decision.category != 'business':
        return decision
    return PolicyDecision('business', decision.reason, decision.mixed,
                          bool(documents and documentary_route(without_format(message), history)))


def question_with_topic(message, history):
    """Pass bounded *user* topic anchors as JSON data, not privileged messages."""
    if not is_followup(without_format(message)):
        return message
    anchors = [row['content'][:400] for row in history if row.get('role') == 'user'
               and not is_followup(row['content']) and not FORMAT.fullmatch(row['content'])][-1:]
    if not anchors:
        return message
    data = {'question': message, 'previous_user_questions': anchors}
    if response_mode(message, history) in {'next_step', 'continuation'}:
        # Exact user substring, not an inferred step or an old documentary
        # answer. Keeping the last coordinated clause reduces first-action
        # anchoring when the question mentions several actions in order.
        data['last_user_focus'] = re.split(r'\s+(?:y|luego)\s+', anchors[-1], flags=re.I)[-1]
    return json.dumps(data, ensure_ascii=False, separators=(',', ':'))


def response_mode(message, history):
    """Backend-owned presentation intent, never an authorization or new fact."""
    text = normalized(message)
    if re.search(r'(?:en|a) (?:cinco|5) (?:pasos|grupos)\b', text):
        return 'summary_five'
    if history and is_followup(message):
        if re.search(r'despu[eé]s|siguiente|qu[eé] sigue|qu[eé] luego', text) and not re.search(r'permisos|acl|publicaci[oó]n', text):
            return 'next_step'
        if re.search(r'contin[uú]a', text):
            return 'continuation'
    return 'answer'


def general_prompt():
    from app.services.leny_policy import SYSTEM_PROMPT
    return SYSTEM_PROMPT.replace(
        'No tienes acceso a datos del ERP, PostgreSQL, archivos, documentos internos, internet ni herramientas.',
        'Este turno ofrece orientación general, no hechos privados verificados. El backend puede recuperar '
        'documentación publicada autorizada en otros turnos; solo la evidencia explícita del turno permite citarla. '
        'No accedes directamente a PostgreSQL, archivos ni Internet y no ejecutas acciones.')
