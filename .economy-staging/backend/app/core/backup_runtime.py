from __future__ import annotations

import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator
from zoneinfo import ZoneInfo

from app.core.config import settings


BACKUP_LOCK_FILE = ".backup_runtime.lock"
BACKUP_BLOCKED_MESSAGE = "EL SISTEMA ESTÁ GENERANDO UN BACKUP. ESPERE A QUE FINALICE."
BACKUP_EXEMPT_PATHS = {
    "/health",
    "/api/v1/auth/login",
    "/api/v1/auth/logout",
    "/api/v1/auth/refresh",
    "/api/v1/auth/me",
}


class BackupLockActiveError(RuntimeError):
    pass


def backend_root_path() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_backup_dir() -> Path:
    candidate = Path(settings.backup_dir)
    if not candidate.is_absolute():
        candidate = backend_root_path() / candidate
    return candidate.resolve()


def backup_lock_path() -> Path:
    return resolve_backup_dir() / BACKUP_LOCK_FILE


def is_backup_exempt_request(path: str, method: str) -> bool:
    normalized_path = (path or "").rstrip("/") or "/"
    if normalized_path in BACKUP_EXEMPT_PATHS:
        return True
    if normalized_path.startswith("/api/v1/backups") and method.upper() == "GET":
        return True
    if normalized_path.startswith("/docs") or normalized_path.startswith("/redoc") or normalized_path.startswith("/openapi.json"):
        return True
    return False


def read_backup_lock() -> dict[str, Any] | None:
    lock_file = backup_lock_path()
    if not lock_file.exists():
        return None
    try:
        return json.loads(lock_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"message": BACKUP_BLOCKED_MESSAGE}


def is_backup_lock_active() -> bool:
    return backup_lock_path().exists()


def release_backup_lock() -> None:
    lock_file = backup_lock_path()
    try:
        if lock_file.exists():
            lock_file.unlink()
    except OSError:
        return


def update_backup_lock(payload: dict[str, Any]) -> None:
    lock_file = backup_lock_path()
    if not lock_file.exists():
        return
    current_payload = read_backup_lock() or {}
    merged_payload = {**current_payload, **payload}
    try:
        lock_file.write_text(json.dumps(merged_payload, ensure_ascii=True), encoding="utf-8")
    except OSError:
        return


def release_stale_lock_if_safe(has_backup_in_progress: bool) -> None:
    if has_backup_in_progress:
        return
    release_backup_lock()


@dataclass(frozen=True)
class BackupLockContext:
    lock_path: Path
    payload: dict[str, Any]


def acquire_backup_lock(payload: dict[str, Any]) -> BackupLockContext:
    backup_dir = resolve_backup_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)
    lock_file = backup_dir / BACKUP_LOCK_FILE
    normalized_payload = {
        "message": BACKUP_BLOCKED_MESSAGE,
        "created_at": datetime.now(ZoneInfo(settings.backup_timezone)).isoformat(),
        **payload,
    }
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(str(lock_file), flags)
    except FileExistsError as exc:
        raise BackupLockActiveError(BACKUP_BLOCKED_MESSAGE) from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(normalized_payload, handle, ensure_ascii=True)
    except Exception:
        try:
            lock_file.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return BackupLockContext(lock_path=lock_file, payload=normalized_payload)


@contextmanager
def backup_lock(payload: dict[str, Any]) -> Iterator[BackupLockContext]:
    context = acquire_backup_lock(payload)
    try:
        yield context
    finally:
        release_backup_lock()
