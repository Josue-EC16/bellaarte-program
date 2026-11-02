"""Deploy the reviewed additive 0019 migration to the authorized local ERP.

Read-only by default. --apply verifies a private database dump, migrates only
0018 -> 0019, checks public definitions/roles/grants, then enables the library.
Never seeds, restores, downgrades, creates accounts, or changes existing roles.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from deploy_leny_storage import public_structure

TABLES = ("carpetas", "carpeta_roles_lectura", "documentos",
          "documento_roles_lectura", "documento_versiones", "documento_operaciones")
SOURCE, TARGET = "20261019_0018", "20261019_0019"


def enable_configuration(original: bytes, root: Path) -> None:
    """Change only the two library settings, retaining other bytes and values."""
    path = BACKEND / ".env"
    if path.read_bytes() != original:
        raise RuntimeError("Configuration changed during deployment; library was not enabled.")
    content = original.decode("utf-8")
    newline = "\r\n" if "\r\n" in content else "\n"
    for key, value in (("LENY_DOCUMENTS_ROOT", root.as_posix()), ("LENY_DOCUMENTS_ENABLED", "true")):
        pattern = re.compile(r"^" + key + r"\s*=.*$", re.MULTILINE | re.IGNORECASE)
        replacement = key + "=" + value
        if pattern.search(content):
            content = pattern.sub(replacement, content)
        else:
            content = content.rstrip("\r\n") + newline + replacement + newline
    # Existing .env keeps its filesystem permissions; no plaintext backup copy.
    with path.open("wb") as handle:
        handle.write(content.encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    from app.core.config import Settings, settings
    from app.services.leny_document_storage import DocumentStorage
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url

    original_env = (BACKEND / ".env").read_bytes()
    configured = Settings(_env_file=BACKEND / ".env")
    url = make_url(configured.effective_database_url)
    if (url.host not in {"localhost", "127.0.0.1"} or (url.port or 5432) != 5432
            or url.database != "bellaarte_db" or url.query):
        raise RuntimeError("Unexpected target; refusing deployment.")
    engine = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 5,
                           "options": "-c lock_timeout=5000 -c statement_timeout=30000"})
    try:
        with engine.connect() as connection:
            identity = connection.execute(text("SELECT current_database(),current_user,inet_server_port()")).one()
            if (identity[0], identity[2]) != ("bellaarte_db", 5432) or identity[1] != url.username:
                raise RuntimeError("Connected identity mismatch.")
            if args.apply and not connection.execute(text("SELECT pg_try_advisory_lock(83998045405465)")).scalar_one():
                raise RuntimeError("Another deployment is active.")
            try:
                revision = connection.execute(text("SELECT version_num FROM public.alembic_version")).scalar_one()
                before = public_structure(connection)
                roles = list(connection.execute(text("SELECT codigo FROM public.roles ORDER BY codigo")).scalars())
                found = list(connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='leny' ORDER BY tablename")).scalars())
                if revision not in {SOURCE, TARGET}:
                    raise RuntimeError("Unexpected starting revision.")
                print(json.dumps({"database": "bellaarte_db", "port": 5432, "revision": revision,
                                  "document_tables": [name for name in found if name in TABLES],
                                  "library_enabled": configured.leny_documents_enabled}), flush=True)
                if not args.apply:
                    return
                if revision != SOURCE or configured.leny_documents_enabled or any(name in found for name in TABLES):
                    raise RuntimeError("Apply requires revision0018 with the library disabled and its tables absent.")
                storage = DocumentStorage(configured)
                storage.initialize()
                directory = storage.root / "backups" / ("deployment-0019-" + uuid4().hex)
                directory.mkdir(exist_ok=False)
                pg_root = Path(r"C:\laragon\bin\postgresql\postgresql-17.9-1\bin")
                dump_tool, restore_tool = pg_root / "pg_dump.exe", pg_root / "pg_restore.exe"
                if not dump_tool.is_file() or not restore_tool.is_file():
                    raise RuntimeError("Installed PostgreSQL backup tools are required.")
                dump = directory / "before-0019.dump"
                environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("PG")}
                environment.update(PGPASSWORD=url.password or "", PGCONNECT_TIMEOUT="5")
                with (directory / "backup-errors.log").open("wb") as errors:
                    subprocess.run([str(dump_tool), "--host", url.host, "--port", "5432", "--username", url.username,
                                    "--dbname", "bellaarte_db", "--format=custom", "--file", str(dump)],
                                   env=environment, stdout=subprocess.DEVNULL, stderr=errors, check=True, timeout=120)
                    subprocess.run([str(restore_tool), "--list", str(dump)], stdout=subprocess.DEVNULL,
                                   stderr=errors, check=True, timeout=60)
                    subprocess.run([str(restore_tool), "--file", os.devnull, str(dump)],
                                   stdout=subprocess.DEVNULL, stderr=errors, check=True, timeout=120)
                if not dump.stat().st_size:
                    raise RuntimeError("Empty backup; migration refused.")
                report = {"time_utc": datetime.now(timezone.utc).isoformat(), "database": "bellaarte_db", "port": 5432,
                          "revision_before": revision, "revision_after": None, "backup_bytes": dump.stat().st_size,
                          "backup_sha256": hashlib.sha256(dump.read_bytes()).hexdigest(), "backup_offline_read": True,
                          "business_restore_executed": False, "state": "backup_verified"}
                report_file = directory / "deployment.json"
                def record():
                    report_file.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
                record()
                print("Private backup verified; applying only revision0019.", flush=True)
                # End the inspection transaction while retaining this session's deployment lease.
                connection.rollback()
                from alembic import command
                from alembic.config import Config
                settings.database_url = configured.effective_database_url
                configuration = Config(str(BACKEND / "alembic.ini"))
                configuration.set_main_option("script_location", str(BACKEND / "alembic"))
                previous_options = os.environ.get("PGOPTIONS")
                try:
                    os.environ["PGOPTIONS"] = "-c lock_timeout=5000 -c statement_timeout=30000"
                    command.upgrade(configuration, TARGET)
                finally:
                    if previous_options is None:
                        os.environ.pop("PGOPTIONS", None)
                    else:
                        os.environ["PGOPTIONS"] = previous_options
                revision = connection.execute(text("SELECT version_num FROM public.alembic_version")).scalar_one()
                if revision != TARGET or before != public_structure(connection):
                    raise RuntimeError("Post-migration mismatch; inspect without automatically restoring.")
                if roles != list(connection.execute(text("SELECT codigo FROM public.roles ORDER BY codigo")).scalars()):
                    raise RuntimeError("Role definitions changed during deployment; inspect.")
                if not connection.execute(text("SELECT has_schema_privilege('leny','USAGE')")).scalar_one():
                    raise RuntimeError("Runtime schema access missing.")
                for table in TABLES:
                    for permission in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                        if not connection.execute(text("SELECT has_table_privilege(:table,:permission)"),
                                                  {"table": "leny." + table, "permission": permission}).scalar_one():
                            raise RuntimeError("Runtime table access missing.")
                    connection.execute(text("SELECT 1 FROM leny." + table + " LIMIT 0"))
                report.update(revision_after=revision, public_structure_unchanged=True, role_codes_unchanged=True,
                              runtime_schema_and_dml_permissions=True, document_tables=list(TABLES), state="schema_verified")
                record()
                enable_configuration(original_env, storage.root)
                activated = Settings(_env_file=BACKEND / ".env")
                if not activated.leny_documents_enabled or Path(activated.leny_documents_root) != storage.root:
                    raise RuntimeError("Library configuration verification failed.")
                report.update(library_enabled_in_env=True, private_storage_outside_webroot=True, state="enabled_restart_required")
                record()
                print("Migration0019 verified; public structure and roles unchanged; library enabled in .env.")
                print("Private deployment report: " + str(report_file))
            finally:
                if args.apply:
                    connection.rollback()
                    connection.execute(text("SELECT pg_advisory_unlock(83998045405465)"))
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("Document deployment stopped: " + (str(error) if type(error) is RuntimeError else type(error).__name__), file=sys.stderr)
        raise SystemExit(1) from None
