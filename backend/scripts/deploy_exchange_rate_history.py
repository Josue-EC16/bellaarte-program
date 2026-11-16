"""Authorized TC-01 deployment: inspect by default, explicit --apply for 0023.

No provider access, datasets, seeds, user changes, restore or automatic downgrade.
Retains a private verified DB/original bundle before touching the business schema.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
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
SOURCE, TARGET = "20261103_0022", "20261104_0023"


def snapshot(connection):
    from sqlalchemy import text
    tables = connection.execute(text("""SELECT schemaname,tablename FROM pg_tables
        WHERE schemaname IN ('public','leny') AND tablename NOT IN ('alembic_version','tipo_cambio_registros')
        ORDER BY schemaname,tablename""")).all()
    quote = connection.dialect.identifier_preparer.quote
    result = {}
    for schema, table in tables:
        value = "to_jsonb(t)"
        if (schema, table) == ("public", "tipo_cambio_moneda"):
            value += " - 'tcm_origen' - 'tcm_fuente' - 'tcm_fec_consulta'"
        row = connection.execute(text("SELECT count(*),md5(coalesce(string_agg(h,'' ORDER BY h),'')) FROM "
            f"(SELECT md5(({value})::text) h FROM {quote(schema)}.{quote(table)} t) row_hashes")).one()
        result[f"{schema}.{table}"] = {"count": row[0], "fingerprint": row[1]}
    return result


def schema_signature(connection, table):
    from sqlalchemy import text
    return [list(row) for row in connection.execute(text("""SELECT column_name,data_type,udt_name,is_nullable,
        numeric_precision,numeric_scale,character_maximum_length,column_default,is_identity,identity_generation
        FROM information_schema.columns WHERE table_schema='public' AND table_name=:table ORDER BY ordinal_position"""), {"table": table})]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backend-pid", type=int)
    args = parser.parse_args()
    os.chdir(BACKEND)
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url
    from app.core.config import settings
    from deploy_user_sessions import verify_backend, connection_snapshot
    url = make_url(settings.effective_database_url)
    if (url.host not in {"localhost", "127.0.0.1"} or (url.port or 5432) != 5432
            or url.database != "bellaarte_db" or url.query):
        raise RuntimeError("Unexpected deployment target; no change allowed.")
    engine = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 5,
        "options": "-c lock_timeout=5000 -c statement_timeout=30000"})
    try:
        with connection_snapshot(engine) as db:
            if tuple(db.execute(text("SELECT current_database(),current_user,inet_server_port()")).one()) != ("bellaarte_db", url.username, 5432):
                raise RuntimeError("Database identity mismatch.")
            revision = db.scalar(text("SELECT version_num FROM alembic_version"))
            if revision not in {SOURCE, TARGET}:
                raise RuntimeError("Unexpected schema revision.")
            duplicates = db.scalar(text("SELECT count(*) FROM (SELECT mon_id FROM tipo_cambio_moneda WHERE tcm_activo GROUP BY mon_id HAVING count(*)>1) d"))
            invalid = db.scalar(text("SELECT count(*) FROM tipo_cambio_moneda WHERE tcm_valor_bob<=0 OR tcm_valor_bob='NaN'::numeric"))
            jobs = db.scalar(text("SELECT count(*) FROM leny.rag_trabajos WHERE status IN ('queued','running')"))
            state = db.scalar(text("SELECT state FROM leny.inferencia_estado WHERE id=1"))
        print(json.dumps({"database": "bellaarte_db", "port": 5432, "revision": revision,
            "active_duplicate_groups": duplicates, "invalid_values": invalid, "active_document_jobs": jobs,
            "inference_state": state, "apply": args.apply}), flush=True)
        if not args.apply:
            return
        if revision != SOURCE or duplicates or invalid or jobs or state != "idle" or not args.backend_pid:
            raise RuntimeError("Apply requires0022, consistent rates, idle LENY and an identified original backend PID.")
        verify_backend(args.backend_pid)
        from app.core.backup_runtime import backup_lock
        from app.services.leny_coordination import PostgresLease
        from app.services.leny_document_storage import DocumentStorage, protect_directory, _check_path
        from app.services.leny_document_backup import freeze_library, build_bundle, verify_bundle
        from sqlalchemy.orm import sessionmaker
        directory = Path(os.environ["LOCALAPPDATA"]) / "BAB_VDOS/tc01-deployments" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8])
        _check_path(directory)
        directory.mkdir(parents=True, exist_ok=False)
        protect_directory(directory)
        report = {"time_utc": datetime.now(timezone.utc).isoformat(), "revision_before": SOURCE,
            "revision_after": None, "state": "preparing", "provider_requests": 0,
            "historical_import_executed": False, "business_restore_executed": False}
        def record():
            (directory / "deployment.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        record()
        lease = PostgresLease(engine)
        stopped = False
        try:
            with engine.connect() as gate:
                if not gate.scalar(text("SELECT pg_try_advisory_lock(83998045405465)")):
                    raise RuntimeError("Another deployment is active.")
                with backup_lock({"operation": "TC01_0023_DEPLOYMENT"}):
                    verify_backend(args.backend_pid)
                    subprocess.run(["taskkill.exe", "/PID", str(args.backend_pid), "/T", "/F"],
                        capture_output=True, check=True, timeout=20)
                    stopped = True
                    print("Original backend paused; verifying private DB/document backup.", flush=True)
                    with connection_snapshot(engine) as db:
                        before = snapshot(db)
                        moneda_before = schema_signature(db, "moneda")
                        rate_before = schema_signature(db, "tipo_cambio_moneda")
                    storage = DocumentStorage(settings)
                    storage.initialize()
                    destination = storage.root / "backups"
                    destination.mkdir(parents=True, exist_ok=True)
                    protect_directory(destination)
                    dump = destination / ("tc01-before-0023-" + uuid4().hex + ".dump")
                    bundle = dump.with_suffix(".zip")
                    binaries = Path(r"C:\laragon\bin\postgresql\postgresql-17.9-1\bin")
                    environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("PG")}
                    environment.update(PGPASSWORD=url.password or "", PGCONNECT_TIMEOUT="5")
                    with freeze_library(settings):
                        with (directory / "backup-errors.log").open("wb") as errors:
                            subprocess.run([str(binaries / "pg_dump.exe"), "-h", url.host, "-p", "5432", "-U", url.username,
                                "-d", "bellaarte_db", "-Fc", "-f", str(dump)], env=environment,
                                stdout=subprocess.DEVNULL, stderr=errors, check=True, timeout=180)
                            subprocess.run([str(binaries / "pg_restore.exe"), "--list", str(dump)],
                                stdout=subprocess.DEVNULL, stderr=errors, check=True, timeout=60)
                            subprocess.run([str(binaries / "pg_restore.exe"), "--file", os.devnull, str(dump)],
                                stdout=subprocess.DEVNULL, stderr=errors, check=True, timeout=180)
                        build_bundle(dump, bundle, sessionmaker(engine), storage)
                        if verify_bundle(bundle)["alembic_revision"] != SOURCE:
                            raise RuntimeError("Backup revision mismatch.")
                    report.update(state="backup_verified", backup_path=str(bundle),
                        backup_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(), backup_bytes=bundle.stat().st_size,
                        backup_offline_read=True, includes_private_originals=True)
                    record()
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
                            raise RuntimeError("Existing rows changed or revision mismatch; no automatic restore.")
                        if schema_signature(db, "moneda") != moneda_before:
                            raise RuntimeError("Currency structure changed unexpectedly.")
                        after = schema_signature(db, "tipo_cambio_moneda")
                        expected = [list(row) for row in rate_before]
                        for row in expected:
                            if row[0] == "usu_id":
                                row[3] = "YES"
                        if after[:len(expected)] != expected or {row[0] for row in after[len(expected):]} != {"tcm_origen", "tcm_fuente", "tcm_fec_consulta"}:
                            raise RuntimeError("Unexpected original column change.")
                        if db.scalar(text("SELECT count(*) FROM tipo_cambio_moneda WHERE tcm_origen<>'MANUAL' OR tcm_fuente IS NOT NULL OR tcm_fec_consulta IS NOT NULL")):
                            raise RuntimeError("Legacy classification differs from reviewed MANUAL baseline.")
                        if db.scalar(text("SELECT count(*) FROM tipo_cambio_registros")) != 0:
                            raise RuntimeError("Deployment must not import historical records or create attempts.")
                        if not db.scalar(text("SELECT has_table_privilege('tipo_cambio_registros','SELECT,INSERT,UPDATE,DELETE')")):
                            raise RuntimeError("Runtime privilege missing.")
                    report.update(state="schema_verified", revision_after=TARGET, existing_rows_unchanged=True,
                        existing_tables=len(before), moneda_structure_unchanged=True, only_three_columns_added=True,
                        legacy_rates_manual=True, historical_log_rows=0)
                    record()
        finally:
            lease.close()
            if stopped:
                with engine.connect() as db:
                    ready = db.scalar(text("SELECT version_num FROM alembic_version")) == TARGET
                if ready:
                    child_env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(BACKEND))
                    for name in list(child_env):
                        if name.startswith("TEST_"):
                            child_env.pop(name)
                    with (directory / "backend.out.log").open("wb") as stdout, (directory / "backend.err.log").open("wb") as stderr:
                        child = subprocess.Popen([str(BACKEND / "venv/Scripts/python.exe"), "-B", "-m", "uvicorn", "main:app",
                            "--host", "127.0.0.1", "--port", "8000"], cwd=BACKEND, env=child_env,
                            stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
                    report.update(backend_pid=child.pid, private_directory=str(directory))
                    record()
                    manifest = Path(os.environ["LOCALAPPDATA"]) / "BAB_VDOS/leny-original-integration/backend-process.json"
                    if manifest.is_file():
                        process = json.loads(manifest.read_text(encoding="utf-8-sig"))
                        if process.get("pid") == args.backend_pid:
                            process.update(pid=child.pid, previous_pid=args.backend_pid, started=time.time(),
                                repository=str(BACKEND.parent), polling_reload=False, deployment_manifest=str(directory / "deployment.json"))
                            manifest.write_text(json.dumps(process, indent=2) + "\n", encoding="utf-8")
        import httpx
        for _ in range(45):
            try:
                if httpx.get("http://127.0.0.1:8000/health", timeout=2, trust_env=False).status_code == 200:
                    report.update(state="deployed_health_verified", health_200=True)
                    record()
                    print(json.dumps({"applied": TARGET, "backup_verified": True, "existing_rows_unchanged": True,
                        "moneda_structure_unchanged": True, "health_200": True, "backend_pid": report["backend_pid"],
                        "private_directory": str(directory), "automation_enabled": False, "historical_import_executed": False}), flush=True)
                    return
            except httpx.HTTPError:
                pass
            time.sleep(1)
        raise RuntimeError("Schema migrated; backend health not confirmed. Inspect private logs.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("TC01 deployment stopped: " + (str(error) if type(error) is RuntimeError else type(error).__name__), file=sys.stderr)
        raise SystemExit(1) from None
