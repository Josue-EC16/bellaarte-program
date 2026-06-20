from __future__ import annotations

import hashlib
import os
import shutil
import socket
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy.engine import make_url

from app.core.backup_runtime import resolve_backup_dir
from app.core.config import settings


@dataclass(frozen=True)
class BackupResult:
    success: bool
    file_name: str
    file_path: str
    file_size_bytes: int | None = None
    sha256_hash: str | None = None
    pg_dump_version: str | None = None
    database_name: str | None = None
    finished_at: datetime | None = None
    error: str | None = None


def _timezone_now() -> datetime:
    return datetime.now(ZoneInfo(settings.backup_timezone))


def resolve_pg_dump_path() -> str:
    if settings.pg_dump_path:
        candidate = Path(settings.pg_dump_path)
        if candidate.exists():
            return str(candidate)
    detected = shutil.which("pg_dump")
    if detected:
        return detected
    raise RuntimeError("NO SE ENCONTRÓ PG_DUMP. AGREGA POSTGRESQL/BIN AL PATH O CONFIGURA PG_DUMP_PATH.")


def get_pg_dump_version(pg_dump_path: str) -> str:
    process = subprocess.run(
        [pg_dump_path, "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    version = (process.stdout or process.stderr or "").strip()
    if process.returncode != 0 or not version:
        raise RuntimeError("NO FUE POSIBLE OBTENER LA VERSIÓN DE PG_DUMP.")
    return version


def build_backup_filename(now: datetime | None = None) -> str:
    current = now or _timezone_now()
    timestamp = current.strftime("%Y_%m_%d_%H%M%S")
    system_name = socket.gethostname().strip().replace(" ", "_").lower() or "local"
    prefix = settings.backup_filename_prefix.strip().lower().replace(" ", "_")
    return f"{prefix}_{timestamp}_{system_name}.dump"


def build_backup_file_path(file_name: str, now: datetime | None = None) -> Path:
    current = now or _timezone_now()
    target_dir = resolve_backup_dir() / str(current.year)
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / file_name


def calculate_file_sha256(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _database_connection_parts() -> tuple[str | None, str | None, str | None, str | None, str | None]:
    url = make_url(settings.effective_database_url)
    return (
        url.host,
        str(url.port) if url.port is not None else None,
        url.username,
        url.password,
        url.database,
    )


def generate_backup() -> BackupResult:
    now = _timezone_now()
    file_name = build_backup_filename(now)
    file_path = build_backup_file_path(file_name, now)
    try:
        pg_dump_path = resolve_pg_dump_path()
        pg_dump_version = get_pg_dump_version(pg_dump_path)
        host, port, username, password, database_name = _database_connection_parts()
        if not username or not database_name:
            raise RuntimeError("NO FUE POSIBLE RESOLVER LAS CREDENCIALES DE CONEXIÓN DE LA BASE DE DATOS.")

        command = [pg_dump_path]
        if host:
            command.extend(["-h", host])
        if port:
            command.extend(["-p", port])
        command.extend(["-U", username, "-d", database_name, "-Fc", "-f", str(file_path)])

        environment = os.environ.copy()
        if password:
            environment["PGPASSWORD"] = password

        process = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        if process.returncode != 0:
            stderr = (process.stderr or process.stdout or "").strip()
            raise RuntimeError(stderr or "PG_DUMP FINALIZÓ CON ERROR.")
        if not file_path.exists():
            raise RuntimeError("PG_DUMP FINALIZÓ SIN GENERAR EL ARCHIVO DE BACKUP.")

        size_bytes = file_path.stat().st_size
        sha256_hash = calculate_file_sha256(file_path)
        return BackupResult(
            success=True,
            file_name=file_name,
            file_path=str(file_path),
            file_size_bytes=size_bytes,
            sha256_hash=sha256_hash,
            pg_dump_version=pg_dump_version,
            database_name=database_name,
            finished_at=_timezone_now(),
        )
    except Exception as exc:
        return BackupResult(
            success=False,
            file_name=file_name,
            file_path=str(file_path),
            finished_at=_timezone_now(),
            error=str(exc).strip().upper(),
        )


if __name__ == "__main__":
    result = generate_backup()
    if result.success:
        print(result.file_path)
    else:
        print(result.error or "ERROR DESCONOCIDO GENERANDO BACKUP.")
