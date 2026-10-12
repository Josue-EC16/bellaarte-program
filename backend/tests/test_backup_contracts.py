from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.core.backup_runtime import backup_lock, is_backup_lock_active, read_backup_lock
from app.core.config import settings
from app.core.permissions import build_permissions_for_role
from app.main import create_app
from app.models.boutique_enums import TipoBackupBdEnum
from app.schemas.backup import BackupQueryFilters
from scripts import backup_manager


def test_admin_permissions_include_backup_module() -> None:
    permissions = set(build_permissions_for_role("ADMIN"))
    assert {"backups:list", "backups:view", "backups:create", "backups:download"}.issubset(permissions)


def test_non_admin_roles_do_not_receive_backup_permissions() -> None:
    for role_code in ("CAJA", "MODISTA", "INV_BOUTIQUE", "INV_TALLER"):
        permissions = set(build_permissions_for_role(role_code))
        assert "backups:list" not in permissions
        assert "backups:view" not in permissions
        assert "backups:create" not in permissions
        assert "backups:download" not in permissions


def test_backup_query_filters_normalize_text_values() -> None:
    filters = BackupQueryFilters.model_validate(
        {
            "origen": " manual ",
            "search": " respaldo semanal ",
        }
    )
    assert filters.origen == "MANUAL"
    assert filters.search == "RESPALDO SEMANAL"


def test_backup_lock_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "backup_dir", str(tmp_path))
    assert not is_backup_lock_active()
    with backup_lock({"origin": "MANUAL", "tipo": TipoBackupBdEnum.MANUAL.value}):
        assert is_backup_lock_active()
        payload = read_backup_lock()
        assert payload is not None
        assert payload["origin"] == "MANUAL"
        assert payload["tipo"] == "MANUAL"
    assert not is_backup_lock_active()


def test_generate_backup_creates_dump_metadata(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "backup_dir", str(tmp_path))
    monkeypatch.setattr(settings, "backup_filename_prefix", "bellaarte_backup")
    monkeypatch.setattr(backup_manager, "resolve_pg_dump_path", lambda: "pg_dump")
    monkeypatch.setattr(backup_manager, "get_pg_dump_version", lambda _path: "pg_dump (PostgreSQL) 17.0")
    monkeypatch.setattr(backup_manager, "_database_connection_parts", lambda: ("localhost", "5432", "postgres", "secret", "bellaarte_db"))
    monkeypatch.setattr(backup_manager.socket, "gethostname", lambda: "srv-app")

    def fake_run(command, **_kwargs):
        output_path = Path(command[-1])
        output_path.write_bytes(b"BELLAARTE-BACKUP")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(backup_manager.subprocess, "run", fake_run)

    result = backup_manager.generate_backup()

    assert result.success is True
    assert result.database_name == "bellaarte_db"
    assert result.pg_dump_version == "pg_dump (PostgreSQL) 17.0"
    assert result.file_name.endswith("_srv-app.dump")
    assert Path(result.file_path).exists()
    assert result.file_size_bytes == len(b"BELLAARTE-BACKUP")
    assert result.sha256_hash


def test_generate_backup_returns_failure_when_pg_dump_errors(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "backup_dir", str(tmp_path))
    monkeypatch.setattr(backup_manager, "resolve_pg_dump_path", lambda: "pg_dump")
    monkeypatch.setattr(backup_manager, "get_pg_dump_version", lambda _path: "pg_dump (PostgreSQL) 17.0")
    monkeypatch.setattr(backup_manager, "_database_connection_parts", lambda: ("localhost", "5432", "postgres", "secret", "bellaarte_db"))

    def fake_run(_command, **_kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="pg_dump fatal error")

    monkeypatch.setattr(backup_manager.subprocess, "run", fake_run)

    result = backup_manager.generate_backup()

    assert result.success is False
    assert result.error == "PG_DUMP FATAL ERROR"


def test_backup_middleware_blocks_non_exempt_requests(monkeypatch) -> None:
    app = create_app()
    client = TestClient(app)
    monkeypatch.setattr("app.main.is_backup_lock_active", lambda: True)

    blocked = client.get("/api/v1/clientes")
    assert blocked.status_code == 503
    assert blocked.json()["detail"] == "EL SISTEMA ESTÁ GENERANDO UN BACKUP. ESPERE A QUE FINALICE."

    allowed = client.get("/health")
    assert allowed.status_code == 200
