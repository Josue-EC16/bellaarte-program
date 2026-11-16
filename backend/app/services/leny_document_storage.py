"""Private immutable originals. No user filename is ever a filesystem path."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
from uuid import uuid4


class DocumentError(Exception):
    def __init__(self, code, message, status=409):
        self.code, self.message, self.status = code, message, status
        super().__init__(code)


def document_root(settings):
    base = os.environ.get('LOCALAPPDATA')
    if not settings.leny_documents_root and not base:
        raise DocumentError('DOCUMENT_STORAGE_CONFIG', 'Configura el almacenamiento privado.', 503)
    root = Path(settings.leny_documents_root) if settings.leny_documents_root else Path(base) / 'BAB_VDOS' / 'leny-documents'
    if str(root).startswith(('\\\\', '//')):
        raise DocumentError('DOCUMENT_STORAGE_CONFIG', 'El almacenamiento documental requiere un disco local.', 503)
    root = root.absolute()
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        get_type = ctypes.WinDLL('kernel32', use_last_error=True).GetDriveTypeW
        get_type.argtypes = [wintypes.LPCWSTR]
        if get_type(root.anchor) != 3:  # DRIVE_FIXED; no network or removable roots
            raise DocumentError('DOCUMENT_STORAGE_CONFIG', 'El almacenamiento documental requiere un disco local fijo.', 503)
    repository = Path(__file__).resolve().parents[3]
    webroot = repository.parent
    if not root.is_absolute() or root.resolve().is_relative_to(webroot.resolve()):
        raise DocumentError('DOCUMENT_STORAGE_CONFIG', 'El almacenamiento debe estar fuera del directorio web.', 503)
    return root


def _check_path(path):
    for part in (path, *path.parents):
        if part.exists() or part.is_symlink():
            info = part.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise DocumentError('DOCUMENT_UNSAFE_PATH', 'Almacenamiento no disponible.', 503)
            if part.is_file() and info.st_nlink != 1:
                raise DocumentError('DOCUMENT_UNSAFE_PATH', 'Almacenamiento no disponible.', 503)


def protect_directory(path):
    """Owner/SYSTEM/Administrators only; no shell, elevation or global changes."""
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    api = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    api.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    api.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    api.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
    api.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p]
    api.SetFileSecurityW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p]
    token, descriptor, sid_string = wintypes.HANDLE(), ctypes.c_void_p(), wintypes.LPWSTR()
    try:
        if not api.OpenProcessToken(kernel.GetCurrentProcess(), 0x8, ctypes.byref(token)):
            raise OSError('token')
        needed = wintypes.DWORD()
        api.GetTokenInformation(token, 1, None, 0, ctypes.byref(needed))
        buffer = ctypes.create_string_buffer(needed.value)
        if not api.GetTokenInformation(token, 1, buffer, needed, ctypes.byref(needed)):
            raise OSError('token information')
        sid = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p)).contents.value
        if not api.ConvertSidToStringSidW(sid, ctypes.byref(sid_string)):
            raise OSError('sid')
        sddl = f'D:P(A;OICI;FA;;;{sid_string.value})(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)'
        if not api.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, ctypes.byref(descriptor), None):
            raise OSError('descriptor')
        if not api.SetFileSecurityW(str(path), 0x80000004, descriptor):
            raise OSError('dacl')
    except OSError:
        raise DocumentError('DOCUMENT_STORAGE_ACL', 'No se pudieron aplicar los permisos privados.', 503) from None
    finally:
        if descriptor:
            kernel.LocalFree(descriptor)
        if sid_string:
            kernel.LocalFree(sid_string)
        if token:
            kernel.CloseHandle(token)


class DocumentStorage:
    def __init__(self, settings):
        self.settings = settings
        self.root = document_root(settings)

    def initialize(self):
        _check_path(self.root)
        created = not self.root.exists()
        self.root.mkdir(parents=True, exist_ok=True)
        marker = self.root / '.leny-private-root'
        if not created and not marker.exists() and any(self.root.iterdir()):
            raise DocumentError('DOCUMENT_STORAGE_CONFIG', 'La raíz documental requiere un directorio privado propio.', 503)
        if os.name == 'nt':
            protect_directory(self.root)
        else:
            raise DocumentError('DOCUMENT_PLATFORM_UNSUPPORTED', 'El almacenamiento requiere Windows.', 503)
        marker.touch(exist_ok=True)
        for name in ('staging', 'versions', 'previews', 'backups'):
            path = self.root / name
            _check_path(path)
            path.mkdir(exist_ok=True)

    def path(self, key):
        if not isinstance(key, str) or not re.fullmatch(r'(staging|versions|previews)/[a-f0-9]{32}\.(blob|json|png|jpg)', key):
            raise DocumentError('DOCUMENT_UNSAFE_PATH', 'Archivo no disponible.', 503)
        result = self.root.joinpath(*key.split('/'))
        _check_path(result)
        if not result.resolve().is_relative_to(self.root.resolve()):
            raise DocumentError('DOCUMENT_UNSAFE_PATH', 'Archivo no disponible.', 503)
        return result

    def new_stage(self):
        key = f'staging/{uuid4().hex}.blob'
        path = self.path(key)
        with path.open('xb'):
            pass
        return key

    def promote(self, source, destination):
        first, second = self.path(source), self.path(destination)
        if second.exists():
            raise DocumentError('DOCUMENT_FILE_CONFLICT', 'La versión ya existe.')
        # Exclusive library lease prevents another promoter targeting this UUID.
        os.rename(first, second)

    def remove(self, key):
        self.path(key).unlink(missing_ok=True)

    @contextmanager
    def open(self, key):
        path = self.path(key)
        try:
            handle = path.open('rb')
        except FileNotFoundError:
            raise DocumentError('DOCUMENT_FILE_MISSING', 'El archivo no está disponible.', 503) from None
        try:
            info = os.fstat(handle.fileno())
            if info.st_nlink != 1 or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise DocumentError('DOCUMENT_UNSAFE_PATH', 'El archivo no está disponible.', 503)
            if os.name == 'nt':
                import ctypes
                import msvcrt
                from ctypes import wintypes
                get_path = ctypes.WinDLL('kernel32', use_last_error=True).GetFinalPathNameByHandleW
                get_path.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
                get_path.restype = wintypes.DWORD
                output = ctypes.create_unicode_buffer(32768)
                if not get_path(msvcrt.get_osfhandle(handle.fileno()), output, len(output), 0):
                    raise DocumentError('DOCUMENT_UNSAFE_PATH', 'El archivo no está disponible.', 503)
                actual = Path(output.value.removeprefix('\\\\?\\')).resolve()
                if actual != path.resolve() or not actual.is_relative_to(self.root.resolve()):
                    raise DocumentError('DOCUMENT_UNSAFE_PATH', 'El archivo no está disponible.', 503)
            yield handle
        finally:
            handle.close()

    def sha256(self, key):
        digest = hashlib.sha256()
        with self.open(key) as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(chunk)
        return digest.hexdigest()

    def free_space(self):
        return shutil.disk_usage(self.root).free
