"""Cancellable extraction in a bounded native Windows Job Object."""
from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

from app.services.leny_document_storage import DocumentError
from app.services.leny_document_validation import ParserJob
from app.services.leny_rag_chunking import SOURCE_TYPES


ERROR_MESSAGES = {
    'RAG_INVALID_DOCUMENT': 'No se pudo extraer el documento de forma segura.',
    'RAG_EXTRACTION_UNAVAILABLE': 'Los componentes de extracción no están disponibles.',
    'RAG_OCR_UNAVAILABLE': 'El OCR local no está instalado o no tiene los idiomas requeridos.',
    'RAG_OCR_TIMEOUT': 'Una página excedió el tiempo permitido para OCR.',
    'RAG_OCR_FAILED': 'El OCR de una página requerida no se pudo completar.',
    'RAG_OCR_PAGE_LIMIT': 'El documento requiere más páginas OCR de las permitidas.',
    'RAG_TEXT_LIMIT': 'El texto extraído excede el límite configurado.',
    'RAG_TEMP_LIMIT': 'El procesamiento excede el espacio temporal permitido.',
    'RAG_RENDER_LIMIT': 'Una página excede el tamaño de rasterización permitido.',
    'RAG_NO_TEXT': 'No se encontró texto utilizable en el documento.',
}


def _validate_result(result, settings):
    if not isinstance(result, dict) or set(result) != {'units', 'coverage'} or not isinstance(result['units'], list) or not isinstance(result['coverage'], dict) or len(result['units']) > 10000:
        raise DocumentError('RAG_EXTRACTION_INVALID', 'La extracción no tiene una estructura válida.', 422)
    total = 0
    for unit in result['units']:
        if not isinstance(unit, dict) or set(unit) != {'text', 'source_type', 'locator'} or not isinstance(unit['text'], str) or unit['source_type'] not in SOURCE_TYPES or not isinstance(unit['locator'], dict):
            raise DocumentError('RAG_EXTRACTION_INVALID', 'La extracción no tiene una estructura válida.', 422)
        total += len(unit['text'].encode('utf-8'))
        if len(json.dumps(unit['locator'], ensure_ascii=False).encode('utf-8')) > 8192:
            raise DocumentError('RAG_EXTRACTION_INVALID', 'Los localizadores exceden el límite permitido.', 422)
    if total > settings.leny_rag_max_text_bytes:
        raise DocumentError('RAG_TEXT_LIMIT', ERROR_MESSAGES['RAG_TEXT_LIMIT'], 422)
    if not any(unit['text'].strip() for unit in result['units']):
        raise DocumentError('RAG_NO_TEXT', ERROR_MESSAGES['RAG_NO_TEXT'], 422)
    return result


def extract_document(path: Path, work_dir: Path, settings, check, progress) -> dict:
    """Input must be an already verified immutable copy in a unique private dir.

    check() may raise cancellation/lease exceptions. They propagate unchanged;
    the finally block still closes the job and kills all parser descendants.
    """
    path, work_dir = Path(path).resolve(), Path(work_dir).resolve()
    if path.parent != work_dir or path.suffix.lower() not in {'.pdf', '.docx', '.png', '.jpg', '.jpeg'} or path.is_symlink() or not path.is_file():
        raise DocumentError('RAG_INVALID_DOCUMENT', ERROR_MESSAGES['RAG_INVALID_DOCUMENT'], 422)
    result_path = work_dir / 'extraction.json'
    if result_path.exists():
        raise DocumentError('RAG_INVALID_DOCUMENT', 'El directorio de extracción ya contiene un resultado.', 422)
    local = Path(os.environ.get('LOCALAPPDATA', '')) / 'BAB_VDOS' / 'leny-rag-runtime'
    tesseract = settings.leny_rag_tesseract_path or str(local / 'tesseract' / 'tesseract.exe')
    tessdata = settings.leny_rag_tessdata_path or str(local / 'tessdata')
    config = {'path': str(path), 'work_dir': str(work_dir), 'result': str(result_path),
              'tesseract': tesseract, 'tessdata': tessdata,
              'limits': {name: getattr(settings, 'leny_documents_' + name) for name in (
                  'pdf_pages', 'zip_entries', 'zip_bytes', 'zip_entry_bytes', 'zip_ratio', 'max_pixels')},
              'rag': {name: getattr(settings, 'leny_rag_' + name) for name in (
                  'max_text_bytes', 'ocr_pages', 'ocr_dpi', 'render_pixels', 'ocr_seconds', 'temp_bytes')}}
    environment = {key: value for key, value in os.environ.items() if key.upper() in {
        'SYSTEMROOT', 'WINDIR', 'SYSTEMDRIVE', 'COMSPEC', 'USERPROFILE', 'LOCALAPPDATA', 'PROGRAMFILES'}}
    environment.update(PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1',
                       VIPS_CONCURRENCY='1', OMP_THREAD_LIMIT='2', TEMP=str(work_dir), TMP=str(work_dir))
    script = Path(__file__).resolve().parents[2] / 'scripts' / 'extract_leny_document.py'
    check()
    process = subprocess.Popen([sys.executable, '-B', '-I', str(script)], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding='utf-8',
                               cwd=work_dir, env=environment, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    job, reader = None, None
    events = queue.Queue(maxsize=128)
    broken = threading.Event()

    def read_events():
        try:
            count = 0
            while True:
                line = process.stdout.readline(4097)
                if not line:
                    break
                count += 1
                if len(line) > 4096 or count > 10000:
                    broken.set()
                    break
                events.put(line, timeout=2)
        except (OSError, ValueError, queue.Full):
            broken.set()

    def drain():
        while True:
            try:
                value = json.loads(events.get_nowait())
            except queue.Empty:
                break
            except (TypeError, ValueError):
                raise DocumentError('RAG_EXTRACTION_INVALID', ERROR_MESSAGES['RAG_INVALID_DOCUMENT'], 422) from None
            if isinstance(value, dict) and set(value) <= {'stage', 'current', 'total'} and value.get('stage') in {'extraction', 'ocr'}:
                if all(isinstance(value.get(key, 0), int) and 0 <= value.get(key, 0) <= 10000 for key in ('current', 'total')):
                    progress(value)

    try:
        job = ParserJob(process, settings.leny_rag_parser_memory_mb, max_processes=3)
        config['job_name'] = job.name
        reader = threading.Thread(target=read_events, daemon=True)
        reader.start()
        process.stdin.write(json.dumps(config))
        process.stdin.close()
        deadline = time.monotonic() + settings.leny_rag_job_seconds
        while process.poll() is None:
            check()
            drain()
            if broken.is_set():
                raise DocumentError('RAG_EXTRACTION_INVALID', ERROR_MESSAGES['RAG_INVALID_DOCUMENT'], 422)
            if time.monotonic() >= deadline:
                raise DocumentError('RAG_EXTRACTION_TIMEOUT', 'El documento excedió el tiempo de procesamiento.', 422)
            size = sum(item.stat().st_size for item in work_dir.rglob('*') if item.is_file())
            if size > settings.leny_rag_temp_bytes:
                raise DocumentError('RAG_TEMP_LIMIT', ERROR_MESSAGES['RAG_TEMP_LIMIT'], 422)
            time.sleep(0.2)
        reader.join(timeout=2)
        drain()
        check()
        if broken.is_set() or not result_path.is_file() or result_path.stat().st_size > 2 * 1024**2:
            raise DocumentError('RAG_EXTRACTION_INVALID', ERROR_MESSAGES['RAG_INVALID_DOCUMENT'], 422)
        try:
            result = json.loads(result_path.read_text(encoding='utf-8'))
        except (ValueError, OSError):
            raise DocumentError('RAG_EXTRACTION_INVALID', ERROR_MESSAGES['RAG_INVALID_DOCUMENT'], 422) from None
        if process.returncode or 'error' in result:
            code = result.get('error', 'RAG_INVALID_DOCUMENT') if isinstance(result, dict) else 'RAG_INVALID_DOCUMENT'
            code = code if code in ERROR_MESSAGES else 'RAG_INVALID_DOCUMENT'
            raise DocumentError(code, ERROR_MESSAGES[code], 503 if code.endswith('UNAVAILABLE') else 422)
        return _validate_result(result, settings)
    except (OSError, subprocess.SubprocessError):
        raise DocumentError('RAG_EXTRACTION_UNAVAILABLE', ERROR_MESSAGES['RAG_EXTRACTION_UNAVAILABLE'], 503) from None
    finally:
        if job:
            job.close()  # KILL_ON_JOB_CLOSE also terminates Tesseract descendants.
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        for pipe in (process.stdin, process.stdout):
            if pipe and not pipe.closed:
                pipe.close()
        if reader:
            reader.join(timeout=2)
