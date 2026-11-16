"""Resource-isolated parsers using the existing interpreter, never another service."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from app.services.leny_document_storage import DocumentError


class ParserJob:
    def __init__(self, process, megabytes, max_processes=2):
        self.handle = None
        if os.name != 'nt':
            raise DocumentError('DOCUMENT_PLATFORM_UNSUPPORTED', 'El validador requiere el entorno Windows configurado.', 503)
        size_t = ctypes.c_size_t

        class Basic(ctypes.Structure):
            _fields_ = [('user', ctypes.c_int64), ('job', ctypes.c_int64), ('flags', wintypes.DWORD),
                        ('minimum', size_t), ('maximum', size_t), ('active', wintypes.DWORD),
                        ('affinity', size_t), ('priority', wintypes.DWORD), ('scheduling', wintypes.DWORD)]

        class Extended(ctypes.Structure):
            _fields_ = [('basic', Basic), ('io', ctypes.c_uint64 * 6), ('process_memory', size_t),
                        ('job_memory', size_t), ('peak_process', size_t), ('peak_job', size_t)]

        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel.CreateJobObjectW.restype = wintypes.HANDLE
        kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel = kernel
        self.name = 'Local\\BAB_LENY_PARSER_' + uuid4().hex
        self.handle = kernel.CreateJobObjectW(None, self.name)
        info = Extended()
        info.basic.flags = 0x200 | 0x2000 | 0x8  # total job memory, kill-on-close, process limit
        # Windows' venv redirector may launch the actual interpreter; both share
        # a single total memory budget. No parser code creates child processes.
        info.basic.active = max_processes
        info.process_memory = megabytes * 1024 * 1024
        info.job_memory = megabytes * 1024 * 1024
        if not self.handle or not kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)) or not kernel.AssignProcessToJobObject(self.handle, int(process._handle)):
            self.close()
            raise DocumentError('DOCUMENT_VALIDATOR_UNAVAILABLE', 'No se pudo aislar la validación.', 503)

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


def validate_document(storage, stage_key, extension, settings):
    preview_key = stage_key.replace('.blob', '.json' if extension == '.docx' else '.png')
    script = Path(__file__).resolve().parents[2] / 'scripts' / 'validate_leny_document.py'
    environment = {key: value for key, value in os.environ.items() if key.upper() in {
        'SYSTEMROOT', 'WINDIR', 'SYSTEMDRIVE', 'COMSPEC', 'USERPROFILE', 'LOCALAPPDATA', 'PROGRAMFILES',
    }}
    environment.update(PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1',
                       VIPS_CONCURRENCY='1', TEMP=str(storage.root / 'staging'), TMP=str(storage.root / 'staging'))
    config = {'path': str(storage.path(stage_key)), 'preview': str(storage.path(preview_key)),
              'extension': extension, 'limits': {name: getattr(settings, 'leny_documents_' + name) for name in (
                  'pdf_pages', 'zip_entries', 'zip_bytes', 'zip_entry_bytes', 'zip_ratio', 'max_pixels')}}
    process = subprocess.Popen([sys.executable, '-B', '-I', str(script)], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding='utf-8',
                               cwd=storage.root / 'staging', env=environment, creationflags=subprocess.CREATE_NO_WINDOW)
    job = None
    try:
        job = ParserJob(process, settings.leny_documents_validation_memory_mb)
        config['job_name'] = job.name
        output, _ = process.communicate(json.dumps(config), timeout=settings.leny_documents_validation_seconds)
        if process.returncode == 2 and 'DOCUMENT_VALIDATOR_MISSING' in output:
            raise DocumentError('DOCUMENT_VALIDATOR_MISSING', 'Los validadores documentales no están instalados.', 503)
        if process.returncode or len(output) > 4096:
            raise DocumentError('DOCUMENT_INVALID_FILE', 'Archivo inválido, no permitido o demasiado complejo.', 422)
        result = json.loads(output)
        if set(result) - {'media_type', 'preview_type', 'pages'} or 'media_type' not in result:
            raise DocumentError('DOCUMENT_INVALID_FILE', 'No se pudo validar el archivo.', 422)
        result['preview_stage_key'] = preview_key if result.get('preview_type') else None
        return result
    except subprocess.TimeoutExpired:
        raise DocumentError('DOCUMENT_VALIDATION_TIMEOUT', 'El archivo excede el tiempo de validación.', 422) from None
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate()
        if job:
            job.close()
