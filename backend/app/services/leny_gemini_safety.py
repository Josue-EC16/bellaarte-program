"""Outgoing user/history boundary; published documents approved by owner.

This is deterministic detection, not a complete personal-data classifier.
Documents keep their existing ACL/publication controls and are not redacted.
"""
import re
from app.services.leny_guard import has_secret, normalized
from app.services.leny_llm_contracts import LenyError

SENSITIVE = re.compile(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|'
    r'\b(?:CI|cédula|cedula|teléfono|telefono|celular|cuenta bancaria|tarjeta|saldo personal)\s*[:#=]?\s*\d[\d .-]{5,}', re.I)


def check_user_context(question, history=()):
    values = [question, *(row.get('content', '') for row in history)]
    if any(has_secret(normalized(value)) or SENSITIVE.search(value) for value in values):
        raise LenyError('LENY_GEMINI_SENSITIVE', 'La pregunta o el historial contiene datos que no se pueden enviar a Google. Inicia otra conversación con Qwen.', 422)


def check_runtime_secrets(config, serialized):
    # Auth headers are separate. A literal runtime secret must never be prompt data.
    secrets = [config.gemini_api_key.get_secret_value() if config.gemini_api_key else '',
               config.jwt_secret_key, config.jwt_refresh_secret_key, config.db_pass or '']
    if any(len(value) >= 8 and value in serialized for value in secrets):
        raise LenyError('LENY_GEMINI_SENSITIVE', 'El contenido no puede enviarse al proveedor externo.', 422)
