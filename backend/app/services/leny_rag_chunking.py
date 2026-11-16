"""Deterministic structural fragments. Text and provenance remain untrusted data."""
from __future__ import annotations

import hashlib
import re
import unicodedata

from app.services.leny_document_storage import DocumentError


SOURCE_TYPES = {'PDF_TEXT', 'PDF_OCR', 'DOCX_PARAGRAPH', 'DOCX_TABLE', 'IMAGE_OCR'}


def normalize_text(value):
    # Preserve tabs, table delimiters, digits and currency; only normalize line
    # endings, Unicode composition and decoder NULs. Never change casing.
    return unicodedata.normalize('NFC', value.replace('\r\n', '\n').replace('\r', '\n').replace('\x00', ''))


def _end(text, start, char_limit, byte_limit):
    end = min(len(text), start + char_limit)
    while end > start and len(text[start:end].encode('utf-8')) > byte_limit:
        end -= 1
    if end == start:
        raise DocumentError('RAG_FRAGMENT_LIMIT', 'Los límites no permiten fragmentar el documento.', 422)
    return end


def fragment_units(units, settings):
    """Split each source unit independently, retaining normalized source offsets.

    Offsets refer to NFC-normalized source text, never byte offsets or invented
    PDF/DOCX page numbers. Identical text in two source locations is retained.
    """
    target = settings.leny_rag_chunk_target
    maximum = settings.leny_rag_chunk_chars
    byte_limit = settings.leny_rag_chunk_bytes
    overlap = settings.leny_rag_overlap_chars
    result = []
    total_bytes = 0
    for unit_index, unit in enumerate(units):
        if not isinstance(unit, dict) or unit.get('source_type') not in SOURCE_TYPES or not isinstance(unit.get('text'), str) or not isinstance(unit.get('locator'), dict):
            raise DocumentError('RAG_EXTRACTION_INVALID', 'La extracción no tiene una estructura válida.', 422)
        text = normalize_text(unit['text'])
        total_bytes += len(text.encode('utf-8'))
        if total_bytes > settings.leny_rag_max_text_bytes:
            raise DocumentError('RAG_TEXT_LIMIT', 'El texto extraído excede el límite configurado.', 422)
        if not text.strip():
            continue
        start = 0
        while start < len(text):
            hard_end = _end(text, start, maximum, byte_limit)
            end = hard_end
            # Prefer source structure, then sentence/word boundaries, around
            # target size. Do not repeatedly split short table rows/paragraphs.
            if hard_end < len(text):
                preferred = _end(text, start, min(target, maximum), byte_limit)
                floor = start + max(1, (preferred - start) // 2)
                segment = text[floor:preferred]
                for pattern in (r'\n\n', r'\n', r'[.!?]\s+', r'\s+'):
                    matches = list(re.finditer(pattern, segment))
                    if matches:
                        end = floor + matches[-1].end()
                        break
                else:
                    end = preferred
            value = text[start:end]
            if value.strip():
                locator = dict(unit['locator'])
                locator.update(unit=unit_index, start=start, end=end, offset_basis='NFC_CHARACTERS')
                result.append({'text': value, 'sha256': hashlib.sha256(value.encode('utf-8')).hexdigest(),
                               'source_type': unit['source_type'], 'locator': locator,
                               'char_count': len(value), 'byte_count': len(value.encode('utf-8')),
                               'ordinal': len(result)})
                if len(result) > settings.leny_rag_max_chunks:
                    raise DocumentError('RAG_FRAGMENT_LIMIT', 'El documento excede el número de fragmentos permitido.', 422)
            if end == len(text):
                break
            next_start = max(start + 1, end - min(overlap, max(0, (end - start) // 4)))
            # Align overlap to the beginning of a word where possible. Keep a
            # strict forward progress guarantee for whitespace-free Unicode.
            boundary = re.search(r'\s+', text[next_start:end])
            start = next_start + boundary.end() if boundary else next_start
    if not result:
        raise DocumentError('RAG_NO_TEXT', 'No se encontró texto utilizable en el documento.', 422)
    return result
