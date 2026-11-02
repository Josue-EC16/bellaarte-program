"""Versioned processing policy and safe failures; never includes document text."""
from __future__ import annotations

import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path

from app.services.leny_document_storage import DocumentError

PIPELINE_VERSION = 'rag2-v1'
CHUNKING_VERSION = 'structure-nfc-v1'
OCR_VERSION = 'tesseract-5.5.3-spa-eng-v1'
QUERY_POLICY = {'version': 'qwen-query-v1', 'template': 'Instruct: Given an internal business question about BELLAARTE BOUTIQUE, retrieve relevant document passages that answer it.\nQuery: {query}'}
TERMINAL = {'completed', 'failed', 'cancelled', 'invalidated'}
MESSAGES = {
    'RAG_WORKER_SHUTDOWN': 'El backend está cerrando el procesador. El trabajo permanece en espera para continuar al iniciarlo.',
    'RAG_DISABLED': 'La contextualización todavía no está habilitada.',
    'RAG_NOT_READY': 'Las dependencias del procesamiento no están listas.',
    'RAG_MODEL_MISSING': 'El modelo local de embeddings no está disponible.',
    'RAG_MODEL_CHANGED': 'El modelo instalado no coincide con el manifest aprobado.',
    'RAG_PROVIDER_UNAVAILABLE': 'No se pudo comunicar con Ollama local.',
    'RAG_PROVIDER_TIMEOUT': 'El lote excedió el tiempo permitido.',
    'RAG_PROVIDER_RESPONSE': 'El proveedor devolvió embeddings incompatibles.',
    'RAG_CPU_REQUIRED': 'No se pudo confirmar la ejecución de embeddings en CPU.',
    'RAG_EXTERNAL_MODEL': 'El modelo de embeddings está ocupado por otro uso local.',
    'RAG_INPUT_CONTEXT': 'Un fragmento excede el contexto admitido por el modelo.',
    'RAG_CANCELLED': 'La contextualización fue cancelada.',
    'RAG_INVALIDATED': 'El documento, sus permisos o su versión ya no permiten finalizar este trabajo.',
    'RAG_JOB_TIMEOUT': 'El trabajo excedió su tiempo máximo de procesamiento.',
    'RAG_LOCK_LOST': 'Se interrumpió la coordinación del procesamiento.',
    'RAG_INFERENCE_UNCERTAIN': 'Una inferencia interrumpida requiere reconciliación operativa antes de continuar.',
    'RAG_RATE_LIMITED': 'Espera antes de solicitar otra contextualización.',
    'RAG_QUEUE_FULL': 'La cola de contextualización está completa.',
    'RAG_REQUEST_CONFLICT': 'El identificador corresponde a otra solicitud.',
    'RAG_REQUEST_TERMINAL': 'La solicitud anterior terminó sin éxito. Usa Reintentar con una nueva solicitud.',
    'RAG_ALREADY_ACTIVE': 'Esta versión ya tiene un trabajo pendiente o en curso.',
    'RAG_ALREADY_VALIDATED': 'Esta versión ya fue contextualizada. Confirma Contextualizar de nuevo.',
    'RAG_RETRY_INVALID': 'El reintento no corresponde a un trabajo terminado de esta versión.',
    'RAG_NOT_FOUND': 'Trabajo o versión no encontrados.',
    'RAG_INTEGRITY': 'No se pudo verificar la integridad de la contextualización.',
    'RAG_CAPACITY': 'El procesamiento supera los límites de capacidad configurados.',
    'RAG_MEMORY': 'No hay memoria disponible suficiente para procesar el siguiente lote.',
    'RAG_OPERATION_FAILED': 'No se pudo completar la contextualización.',
}


class RagError(DocumentError):
    def __init__(self, code, status=503, *, uncertain=False):
        super().__init__(code, MESSAGES.get(code, 'No se pudo procesar el documento dentro de los límites configurados.'), status)
        self.uncertain = uncertain


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()).hexdigest()


def runtime_root():
    return Path(os.environ['LOCALAPPDATA']) / 'BAB_VDOS' / 'leny-rag-runtime'


def ocr_paths(settings):
    root = runtime_root()
    return (Path(settings.leny_rag_tesseract_path) if settings.leny_rag_tesseract_path else root / 'tesseract/tesseract.exe',
            Path(settings.leny_rag_tessdata_path) if settings.leny_rag_tessdata_path else root / 'tessdata')


def pipeline_config(settings):
    keys = ('num_ctx', 'max_text_bytes', 'max_chunks', 'chunk_target', 'chunk_chars', 'chunk_bytes',
            'overlap_chars', 'ocr_pages', 'ocr_dpi', 'render_pixels')
    config = {key: getattr(settings, 'leny_rag_' + key) for key in keys}
    _, tessdata = ocr_paths(settings)
    config['ocr_languages'] = 'spa+eng'
    config['ocr_data_hashes'] = {lang: hashlib.sha256((tessdata / (lang + '.traineddata')).read_bytes()).hexdigest()
                                  if (tessdata / (lang + '.traineddata')).is_file() else None for lang in ('spa', 'eng', 'osd')}
    config.update(pipeline_version=PIPELINE_VERSION, chunking_version=CHUNKING_VERSION, ocr_version=OCR_VERSION,
                  model=settings.leny_rag_model, model_digest=settings.leny_rag_model_digest, dimension=1024,
                  document_policy='raw-structured-text-v1', query_policy=QUERY_POLICY, cpu_only=True,
                  extractor_versions={name: version(name) for name in ('pypdf', 'defusedxml', 'pyvips', 'pypdfium2')})
    return config


def available_ram():
    import ctypes
    from ctypes import wintypes
    class Memory(ctypes.Structure):
        _fields_ = [('length', wintypes.DWORD), ('load', wintypes.DWORD),
                    *[(name, ctypes.c_ulonglong) for name in ('total', 'available', 'page_total', 'page_available', 'virtual_total', 'virtual_available', 'extended')]]
    memory = Memory()
    memory.length = ctypes.sizeof(memory)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
        raise RagError('RAG_MEMORY')
    return memory.available
