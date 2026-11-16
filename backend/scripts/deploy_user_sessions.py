"""Deploy only reviewed 0022 to the explicitly authorized original Windows ERP.

Default inspection is read-only. --apply requires an identified original backend
PID, a verified private backup, idle LENY and a coordinated backend restart.
Never seeds, resets credentials, restores or downgrades the business database.
"""
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
SOURCE, TARGET = "20261020_0021", "20261103_0022"


def snapshot(connection):
    from sqlalchemy import text
    names = connection.execute(text("""SELECT schemaname,tablename FROM pg_tables
        WHERE schemaname IN ('public','leny') AND tablename <> 'alembic_version'
        AND tablename NOT IN ('sesion_cuenta','auth_login_bucket') ORDER BY 1,2""")).all()
    quote = connection.dialect.identifier_preparer.quote
    result = {}
    for schema, table in names:
        value = "to_jsonb(t) - 'auth_version' - 'security_version'" if (schema, table) == ("public", "cuentas") else "to_jsonb(t)"
        query = ("SELECT count(*),md5(coalesce(string_agg(h,'' ORDER BY h),'')) FROM "
                 f"(SELECT md5(({value})::text) h FROM {quote(schema)}.{quote(table)} t) row_hashes")
        count, digest = connection.execute(text(query)).one()
        result[f"{schema}.{table}"] = {"count": count, "fingerprint": digest}
    return result


def process_details(pid):
    result = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
        f"Get-CimInstance Win32_Process -Filter 'ProcessId = {int(pid)}' | "
        "Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Compress"],
        capture_output=True, text=True, check=True, timeout=15)
    return json.loads(result.stdout) if result.stdout.strip() else None


def verify_backend(pid):
    process = process_details(pid)
    if (not process or "uvicorn" not in process["CommandLine"] or "main:app" not in process["CommandLine"]
            or str(BACKEND).lower() not in process["CommandLine"].lower()
            or Path(process["ExecutablePath"]).resolve() != (BACKEND / "venv/Scripts/python.exe").resolve()):
        raise RuntimeError("Original backend identity mismatch; no process stopped.")
    return process


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backend-pid", type=int)
    arguments = parser.parse_args()
    os.chdir(BACKEND)
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url
    from app.core.config import settings
    url = make_url(settings.effective_database_url)
    if url.host not in {"localhost", "127.0.0.1"} or (url.port or 5432) != 5432 or url.database != "bellaarte_db" or url.query:
        raise RuntimeError("Unexpected target; deployment refused.")
    engine = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 5,
        "options": "-c lock_timeout=5000 -c statement_timeout=30000"})
    try:
        with engine.connect() as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            identity = connection.execute(text("SELECT current_database(),current_user,inet_server_port()" )).one()
            if tuple(identity) != ("bellaarte_db", url.username, 5432):
                raise RuntimeError("Connected database identity mismatch.")
            revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
            if revision not in {SOURCE, TARGET}:
                raise RuntimeError("Unexpected schema revision; no migration attempted.")
            jobs = connection.scalar(text("SELECT count(*) FROM leny.rag_trabajos WHERE status IN ('queued','running')"))
            state = connection.scalar(text("SELECT state FROM leny.inferencia_estado WHERE id=1"))
            admins = connection.scalar(text("""SELECT count(*) FROM cuentas c JOIN usuarios u ON u.id=c.usuario_id
                JOIN roles r ON r.id=c.rol_id WHERE c.is_active AND u.activo AND r.activo AND r.codigo='ADMIN'"""))
            short_ci = connection.scalar(text("SELECT count(*) FROM usuarios WHERE ci !~ '^[0-9]{7,30}$'"))
        print(json.dumps({"database": "bellaarte_db", "port": 5432, "revision": revision,
            "enabled_admins": admins, "identities_requiring_regularization": short_ci,
            "active_document_jobs": jobs, "inference_state": state, "apply": arguments.apply}), flush=True)
        if not arguments.apply:
            with connection_snapshot(engine) as connection:
                print(json.dumps({"read_only_snapshot_tables": len(snapshot(connection))}), flush=True)
            return
        if revision != SOURCE or not admins or jobs or state != "idle" or not arguments.backend_pid:
            raise RuntimeError("Apply requires0021, an enabled ADMIN, idle LENY and an identified backend PID.")
        verify_backend(arguments.backend_pid)
        from app.core.backup_runtime import backup_lock
        from app.services.leny_coordination import PostgresLease
        from app.services.leny_document_storage import DocumentStorage, protect_directory, _check_path
        from app.services.leny_document_backup import freeze_library, build_bundle, verify_bundle
        from sqlalchemy.orm import sessionmaker
        private = Path(os.environ["LOCALAPPDATA"]) / "BAB_VDOS" / "users-deployments" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8])
        _check_path(private)
        private.mkdir(parents=True, exist_ok=False)
        protect_directory(private)
        report = {"time_utc": datetime.now(timezone.utc).isoformat(), "revision_before": SOURCE,
            "revision_after": None, "state": "preparing", "business_restore_executed": False}
        def record():
            (private / "deployment.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        coordinator = PostgresLease(engine)
        stopped = False
        try:
            with backup_lock({"operation": "USERS_SESSIONS_0022_DEPLOYMENT"}):
                # All owned backend/worker children are idle and identified;
                # stopping the process tree avoids writes while comparing rows.
                verify_backend(arguments.backend_pid)
                subprocess.run(["taskkill.exe", "/PID", str(arguments.backend_pid), "/T", "/F"],
                    capture_output=True, check=True, timeout=20)
                stopped = True
                print("Original backend paused; preparing private backup.", flush=True)
                with connection_snapshot(engine) as db:
                    before = snapshot(db)
                storage = DocumentStorage(settings)
                storage.initialize()
                destination = storage.root / "backups"
                destination.mkdir(parents=True, exist_ok=True)
                protect_directory(destination)
                dump = destination / ("users-before-0022-" + uuid4().hex + ".dump")
                bundle = dump.with_suffix(".zip")
                pg_root = Path(r"C:\laragon\bin\postgresql\postgresql-17.9-1\bin")
                environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("PG")}
                environment.update(PGPASSWORD=url.password or "", PGCONNECT_TIMEOUT="5")
                with freeze_library(settings):
                    with (private / "backup-errors.log").open("wb") as errors:
                        subprocess.run([str(pg_root / "pg_dump.exe"), "-h", url.host, "-p", "5432", "-U", url.username,
                            "-d", "bellaarte_db", "-Fc", "-f", str(dump)], env=environment,
                            stdout=subprocess.DEVNULL, stderr=errors, check=True, timeout=180)
                        subprocess.run([str(pg_root / "pg_restore.exe"), "--list", str(dump)],
                            stdout=subprocess.DEVNULL, stderr=errors, check=True, timeout=60)
                        subprocess.run([str(pg_root / "pg_restore.exe"), "--file", os.devnull, str(dump)],
                            stdout=subprocess.DEVNULL, stderr=errors, check=True, timeout=180)
                    build_bundle(dump, bundle, sessionmaker(engine), storage)
                    verified = verify_bundle(bundle)
                    if verified["alembic_revision"] != SOURCE:
                        raise RuntimeError("Backup revision mismatch.")
                report.update(state="backup_verified", backup_path=str(bundle),
                    backup_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(), backup_bytes=bundle.stat().st_size,
                    backup_offline_read=True, includes_private_originals=True)
                record()
                print("Private backup verified; applying only revision0022.", flush=True)
                from alembic import command
                from alembic.config import Config
                configuration = Config(str(BACKEND / "alembic.ini"))
                configuration.set_main_option("script_location", str(BACKEND / "alembic"))
                previous = os.environ.get("PGOPTIONS")
                try:
                    os.environ["PGOPTIONS"] = "-c lock_timeout=5000 -c statement_timeout=30000"
                    command.upgrade(configuration, TARGET)
                finally:
                    if previous is None:
                        os.environ.pop("PGOPTIONS", None)
                    else:
                        os.environ["PGOPTIONS"] = previous
                with connection_snapshot(engine) as db:
                    if db.scalar(text("SELECT version_num FROM alembic_version")) != TARGET or snapshot(db) != before:
                        raise RuntimeError("Existing rows changed or migration revision differs; inspect without automatic restore.")
                    if db.scalar(text("SELECT count(*) FROM cuentas WHERE auth_version<>0 OR security_version<>0")):
                        raise RuntimeError("Unexpected initial account versions.")
                    for table in ("sesion_cuenta", "auth_login_bucket"):
                        if not db.scalar(text("SELECT has_table_privilege(:table,'SELECT,INSERT,UPDATE,DELETE')"), {"table": table}):
                            raise RuntimeError("Runtime session privilege missing.")
                report.update(state="schema_verified", revision_after=TARGET, existing_rows_unchanged=True)
                record()
        finally:
            coordinator.close()
            if stopped:
                with engine.connect() as db:
                    ready = db.scalar(text("SELECT version_num FROM alembic_version")) == TARGET
                if ready:
                    child_environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(BACKEND))
                    for name in list(child_environment):
                        if name.startswith("TEST_"):
                            child_environment.pop(name)
                    with (private / "backend.out.log").open("wb") as stdout, (private / "backend.err.log").open("wb") as stderr:
                        child = subprocess.Popen([str(BACKEND / "venv/Scripts/python.exe"), "-B", "-m", "uvicorn", "main:app",
                            "--host", "127.0.0.1", "--port", "8000"], cwd=BACKEND, env=child_environment,
                            stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
                    report.update(backend_pid=child.pid, private_directory=str(private))
                    record()
                    runtime_manifest = Path(os.environ["LOCALAPPDATA"]) / "BAB_VDOS/leny-original-integration/backend-process.json"
                    if runtime_manifest.is_file():
                        prior_process = json.loads(runtime_manifest.read_text(encoding="utf-8-sig"))
                        if prior_process.get("pid") == arguments.backend_pid:
                            prior_process.update(pid=child.pid, previous_pid=arguments.backend_pid,
                                started=time.time(), repository=str(BACKEND.parent), polling_reload=False,
                                deployment_manifest=str(private / "deployment.json"))
                            runtime_manifest.write_text(json.dumps(prior_process, indent=2) + "\n", encoding="utf-8")
        import httpx
        health = False
        for _ in range(45):
            try:
                health = httpx.get("http://127.0.0.1:8000/health", timeout=2, trust_env=False).status_code == 200
            except httpx.HTTPError:
                pass
            if health:
                break
            time.sleep(1)
        if not health:
            raise RuntimeError("Schema migrated; backend health not confirmed. Inspect private runtime logs.")
        report.update(state="deployed_health_verified", health_200=True, authenticated_business_operations_tested=False)
        record()
        print(json.dumps({"applied": TARGET, "existing_rows_unchanged": True, "backup_verified": True,
            "health_200": True, "backend_pid": report["backend_pid"], "private_directory": str(private),
            "new_login_required": True}), flush=True)
    finally:
        engine.dispose()


from contextlib import contextmanager


@contextmanager
def connection_snapshot(engine):
    from sqlalchemy import text
    with engine.connect() as connection, connection.begin():
        connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        yield connection


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("Users deployment stopped: " + (str(error) if type(error) is RuntimeError else type(error).__name__), file=sys.stderr)
        raise SystemExit(1) from None
