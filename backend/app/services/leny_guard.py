"""Deterministic boundaries; model decisions never grant capabilities or privileges."""
import re
import unicodedata

from app.services.leny_ollama import LenyError


def normalized(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


SECRET_PATTERNS = (
    re.compile(r"-----begin (?:[a-z ]{0,20})private key", re.I),
    # Stop at a recognizable JWT prefix, before arbitrarily long segments leak.
    re.compile(r"\beyj[A-Za-z0-9_-]{8,}", re.I),
    re.compile(r"\b(?:postgres(?:ql)?|https?|mysql)://[^\s/:]{1,64}:[^\s/@]{1,128}@", re.I),
    re.compile(r"\b(?:password|passwd|contrase[nñ]a|api[_ -]?key|secret[_ -]?key|jwt[_ -]?secret|access[_ -]?token|refresh[_ -]?token)\s*[:=]\s*[\"']?[^\s\"']{6,}", re.I),
)
ROLE_MARKER = re.compile(r"<\|(?:im_start|system|developer|tool|start_header_id)\|>|\[/?INST\]|^\s*(?:SYSTEM|DEVELOPER|TOOL)\s*:", re.I | re.M)
FALSE_ACTION = re.compile(
    r"\b(?:he|hemos|ya he)\s+(?:eliminado|borrado|modificado|actualizado|registrado|ejecutado|consultado|accedido|le[ií]do|desactivado|cambiado)\b.{0,100}\b(?:ventas?|clientes?|inventarios?|base de datos|postgresql|sql|usuarios?|permisos?|roles?|archivos?|documentos? internos?|contrase[nñ]as?)\b", re.I | re.S)
CITATION_VARIANT = re.compile(r'\[(S\d{1,8}(?:\s{0,8},\s{0,8}S\d{1,8}){1,4})\]|'
                              r'\((S\d{1,8}(?:\s{0,8},\s{0,8}S\d{1,8}){0,4})\)')


def has_secret(value: str) -> bool:
    return any(pattern.search(value) for pattern in SECRET_PATTERNS)


def validate_input(value: str) -> str:
    if not value.strip() or any((ord(c) < 32 and c not in "\t\n\r") or 127 <= ord(c) <= 159 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise ValueError("Escribe un mensaje válido, sin caracteres de control.")
    if has_secret(normalized(value)):
        raise ValueError("Retira las credenciales o secretos del mensaje antes de enviarlo.")
    return value.strip()


class OutputGuard:
    """Review cumulative output with a bounded holdback before releasing text.

    Retaining the full cumulative text is bounded by the provider response limit.
    Semantic safety is not guaranteed; already emitted text cannot be retracted.
    """
    def __init__(self, protected_prompt: str, holdback: int = 256, *, citations=None, require_citation=False,
                 canonical_citations=False, max_bytes=None):
        if canonical_citations and holdback < 256:
            raise ValueError('Citation formatting requires the bounded256-character holdback.')
        self.text, self.sent, self.holdback = "", 0, holdback
        self.citations = citations
        self.require_citation = require_citation
        self.canonical_citations = canonical_citations
        self.max_bytes = max_bytes
        # Recognizable instruction fragments rather than ordinary identity words.
        self.protected = [normalized(part.strip()) for part in protected_prompt.split("\n")
                          if len(part.strip()) >= 45]

    def feed(self, text: str, *, final: bool = False) -> str:
        self.text += text
        if self.canonical_citations:
            def replace(match):
                labels = re.findall(r'S\d+', match.group(1) or match.group(2))
                if not set(labels).issubset(self.citations or set()):
                    raise LenyError('LENY_OUTPUT_BLOCKED', 'La respuesta contiene referencias no válidas.', 502)
                return ' '.join('['+label+']' for label in labels)
            # Only unsent text may change length. Bounded complete markers fit
            # within the configured256-character holdback. No missing identity
            # or semantic attribution is invented by this presentation step.
            self.text = self.text[:self.sent] + CITATION_VARIANT.sub(replace, self.text[self.sent:])
            if any(label not in (self.citations or set()) for label in re.findall(r'[\[(]\s*(S\d+)', self.text)):
                raise LenyError('LENY_OUTPUT_BLOCKED', 'La respuesta contiene referencias no válidas.', 502)
        if self.max_bytes is not None and len(self.text.encode('utf-8')) > self.max_bytes:
            raise LenyError('LENY_RESPONSE_LIMIT', 'La respuesta superó el tamaño permitido.', 502)
        checked = normalized(self.text)
        if self.citations is not None and any(citation not in self.citations for citation in re.findall(r'\[(S\d+)\]',self.text)):
            raise LenyError('LENY_OUTPUT_BLOCKED','La respuesta se interrumpió por contener referencias no válidas.',502)
        if final and self.require_citation and not any(citation in (self.citations or set()) for citation in re.findall(r'\[(S\d+)\]', self.text)):
            # Already emitted deltas cannot be retracted; never label this as a
            # completed sourced answer or fabricate a reference to repair it.
            raise LenyError('LENY_RAG_CITATION_MISSING', 'La respuesta no incluyó referencias verificables. No se pudo completar la consulta documental.', 502)
        if has_secret(checked) or ROLE_MARKER.search(self.text) or FALSE_ACTION.search(checked) or any(part[:70] in checked for part in self.protected):
            raise LenyError("LENY_OUTPUT_BLOCKED", "La respuesta se interrumpió por seguridad. Reformula tu consulta empresarial.", 502)
        end = len(self.text) if final else max(self.sent, len(self.text) - self.holdback)
        reviewed = self.text[self.sent:end]
        self.sent = end
        return reviewed
