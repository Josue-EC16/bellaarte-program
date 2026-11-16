"""Authorized TC02 rollout. Default is read-only; --apply backs up and activates.

No migrations, seed, password changes, imports, restores or historical rewrites.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from uuid import uuid4
from zoneinfo import ZoneInfo

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
REVISION = "20261104_0023"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backend-pid", type=int)
    args = parser.parse_args()
    os.chdir(BACKEND)
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings
    from deploy_user_sessions import verify_backend, connection_snapshot
    from deploy_exchange_rate_history import snapshot, schema_signature
    from app.services.exchange_rate_sync_service import sync_job_lock
    url = make_url(settings.effective_database_url)
    if (url.host not in {"localhost", "127.0.0.1"} or (url.port or 5432) != 5432
            or url.database != "bellaarte_db" or url.query):
        raise RuntimeError("Unexpected original database target.")
    engine = create_engine(url, hide_parameters=True, connect_args={"connect_timeout":5,
        "options":"-c lock_timeout=5000 -c statement_timeout=30000"})
    try:
        with connection_snapshot(engine) as db:
            revision = db.scalar(text("SELECT version_num FROM alembic_version"))
            jobs = db.scalar(text("SELECT count(*) FROM leny.rag_trabajos WHERE status IN ('queued','running')"))
            inference = db.scalar(text("SELECT state FROM leny.inferencia_estado WHERE id=1"))
            usd_count = db.scalar(text("SELECT count(*) FROM moneda WHERE mon_cod='USD' AND mon_hab AND NOT mon_es_base"))
            technical_count = db.scalar(text("SELECT count(*) FROM tipo_cambio_registros"))
            duplicate = db.scalar(text("SELECT EXISTS(SELECT 1 FROM tipo_cambio_moneda WHERE tcm_activo GROUP BY mon_id HAVING count(*)>1)"))
        print(json.dumps(dict(revision=revision, enabled=settings.exchange_rate_sync_enabled,
            start_date=str(settings.exchange_rate_sync_start_date) if settings.exchange_rate_sync_start_date else None,
            active_document_jobs=jobs, inference_state=inference, enabled_usd_count=usd_count,
            technical_records=technical_count, active_duplicates=duplicate, apply=args.apply)), flush=True)
        if not args.apply:
            return
        if (revision != REVISION or jobs or inference != "idle" or usd_count != 1 or duplicate
                or settings.exchange_rate_sync_enabled or not args.backend_pid):
            raise RuntimeError("Rollout requires0023, disabled sync, enabled USD, idle LENY and original PID.")
        verify_backend(args.backend_pid)
        from app.core.backup_runtime import backup_lock
        from app.services.leny_coordination import PostgresLease
        from app.services.leny_document_storage import DocumentStorage, protect_directory
        from app.services.leny_document_backup import freeze_library, build_bundle, verify_bundle
        private = Path(os.environ["LOCALAPPDATA"]) / "BAB_VDOS/tc02-deployments" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8])
        private.mkdir(parents=True, exist_ok=False)
        protect_directory(private)
        report = dict(time_utc=datetime.now(timezone.utc).isoformat(), state="preparing",
            revision_before=REVISION, revision_after=REVISION, migrations_executed=False, restore_executed=False,
            initial_history_import_executed=False, private_directory=str(private))
        def record():
            (private / "deployment.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
        record()
        stopped = False
        lease = PostgresLease(engine)
        try:
            with sync_job_lock(engine) as check:
                if check is None:
                    raise RuntimeError("USD synchronization is already running; rollout not started.")
                with backup_lock({"operation":"TC02_DEPLOYMENT"}):
                    verify_backend(args.backend_pid)
                    subprocess.run(["taskkill.exe","/PID",str(args.backend_pid),"/T","/F"],capture_output=True,check=True,timeout=20)
                    stopped = True
                    print("Original backend paused; verifying private backup before activation.", flush=True)
                    with connection_snapshot(engine) as db:
                        before = snapshot(db)
                        moneda = schema_signature(db,"moneda")
                        rates = schema_signature(db,"tipo_cambio_moneda")
                        records = schema_signature(db,"tipo_cambio_registros")
                        technical_before = list(db.execute(text("SELECT md5(to_jsonb(t)::text) FROM tipo_cambio_registros t ORDER BY tcs_id")).scalars())
                    storage = DocumentStorage(settings)
                    storage.initialize()
                    destination = storage.root / "backups"
                    destination.mkdir(parents=True,exist_ok=True)
                    protect_directory(destination)
                    dump = destination / ("tc02-before-activation-"+uuid4().hex+".dump")
                    bundle = dump.with_suffix(".zip")
                    binaries=Path(r"C:\laragon\bin\postgresql\postgresql-17.9-1\bin")
                    environment={key:value for key,value in os.environ.items() if not key.upper().startswith("PG")}
                    environment.update(PGPASSWORD=url.password or "",PGCONNECT_TIMEOUT="5")
                    with freeze_library(settings):
                        with (private / "backup-errors.log").open("wb") as errors:
                            subprocess.run([str(binaries/"pg_dump.exe"),"-h",url.host,"-p","5432","-U",url.username,"-d","bellaarte_db","-Fc","-f",str(dump)],
                                env=environment,stdout=subprocess.DEVNULL,stderr=errors,check=True,timeout=180)
                            subprocess.run([str(binaries/"pg_restore.exe"),"--list",str(dump)],stdout=subprocess.DEVNULL,stderr=errors,check=True,timeout=60)
                            subprocess.run([str(binaries/"pg_restore.exe"),"--file",os.devnull,str(dump)],stdout=subprocess.DEVNULL,stderr=errors,check=True,timeout=180)
                        build_bundle(dump,bundle,sessionmaker(engine),storage)
                        if verify_bundle(bundle)["alembic_revision"] != REVISION:
                            raise RuntimeError("Backup revision mismatch.")
                    env_path=BACKEND/".env"
                    original_env=env_path.read_bytes()
                    (private/"backend.env.before").write_bytes(original_env)
                    start_date=settings.exchange_rate_sync_start_date or datetime.now(ZoneInfo("America/La_Paz")).date()
                    if start_date > datetime.now(ZoneInfo("America/La_Paz")).date():
                        raise RuntimeError("Approved activation cannot have a future start date.")
                    content=original_env.decode("utf-8-sig")
                    for key,value in {"EXCHANGE_RATE_SYNC_START_DATE":str(start_date),"EXCHANGE_RATE_SYNC_ENABLED":"true",
                            "EXCHANGE_RATE_SYNC_HTTP_TIMEOUT_SECONDS":"30","EXCHANGE_RATE_SYNC_RECONCILE_SECONDS":"120"}.items():
                        expression=r"(?m)^"+key+r"=.*$"
                        if re.search(expression,content):
                            content=re.sub(expression,key+"="+value,content)
                        else:
                            content=content.rstrip()+"\n"+key+"="+value+"\n"
                    env_path.write_bytes(content.encode("utf-8"))
                    with connection_snapshot(engine) as db:
                        if snapshot(db) != before or schema_signature(db,"moneda") != moneda or schema_signature(db,"tipo_cambio_moneda") != rates or schema_signature(db,"tipo_cambio_registros") != records:
                            raise RuntimeError("Rows or schema changed before activation; no automatic restore.")
                        if list(db.execute(text("SELECT md5(to_jsonb(t)::text) FROM tipo_cambio_registros t ORDER BY tcs_id")).scalars()) != technical_before:
                            raise RuntimeError("Technical rows changed before activation.")
                    report.update(state="configuration_verified",start_date=str(start_date),backup_path=str(bundle),
                        backup_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),backup_bytes=bundle.stat().st_size,
                        backup_offline_read=True,includes_private_originals=True,existing_rows_unchanged_before_activation=True,
                        existing_tables=len(before),schema_unchanged=True,old_backend_pid=args.backend_pid)
                    record()
        finally:
            lease.close()
            if stopped:
                child_env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1",PYTHONPATH=str(BACKEND))
                for key in list(child_env):
                    if key.startswith("TEST_") or key.startswith("EXCHANGE_RATE_SYNC_"):
                        child_env.pop(key)
                with (private/"backend.out.log").open("wb") as stdout,(private/"backend.err.log").open("wb") as stderr:
                    child=subprocess.Popen([str(BACKEND/"venv/Scripts/python.exe"),"-B","-m","uvicorn","main:app","--host","127.0.0.1","--port","8000"],
                        cwd=BACKEND,env=child_env,stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
                report["backend_pid"]=child.pid
                record()
                manifest=Path(os.environ["LOCALAPPDATA"])/"BAB_VDOS/leny-original-integration/backend-process.json"
                if manifest.is_file():
                    process=json.loads(manifest.read_text(encoding="utf-8-sig"))
                    if process.get("pid")==args.backend_pid:
                        process.update(pid=child.pid,previous_pid=args.backend_pid,started=time.time(),polling_reload=False,
                            repository=str(BACKEND.parent),deployment_manifest=str(private/"deployment.json"))
                        manifest.write_text(json.dumps(process,indent=2)+"\n",encoding="utf-8")
        import httpx
        healthy=False
        for _ in range(45):
            try:
                if httpx.get("http://127.0.0.1:8000/health",timeout=2,trust_env=False).status_code==200:
                    healthy=True
                    break
            except httpx.HTTPError:
                pass
            time.sleep(1)
        if not healthy:
            raise RuntimeError("Backend health not confirmed; scheduler was not activated.")
        with httpx.Client(timeout=5,trust_env=False) as client:
            checks={path:client.get("http://127.0.0.1:8000"+path).status_code for path in [
                "/api/v1/monedas/tipos-cambio/sincronizacion/estado","/api/v1/monedas/tipos-cambio/sincronizacion/registros"]}
        if any(code != 401 for code in checks.values()):
            raise RuntimeError("Unauthenticated API protection failed; scheduler was not activated.")
        task=subprocess.run(["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-File",str(BACKEND/"scripts/install_exchange_rate_sync_task.ps1"),"-Activate"],
            capture_output=True,text=True,timeout=45)
        if task.returncode:
            (private/"task-errors.log").write_text(task.stderr,encoding="utf-8")
            raise RuntimeError("Task registration failed; inspect private task log.")
        report.update(state="deployed_task_enabled",health_200=True,unauthenticated_http_checks=checks,
            task=json.loads(task.stdout),automation_enabled=True)
        record()
        print(json.dumps({key:report[key] for key in ["state","start_date","backup_sha256","backup_bytes","schema_unchanged",
            "existing_rows_unchanged_before_activation","health_200","backend_pid","private_directory","task","automation_enabled"]}),flush=True)
    finally:
        engine.dispose()


if __name__=="__main__":
    try:
        main()
    except Exception as error:
        print("TC02 rollout stopped: "+(str(error) if type(error) is RuntimeError else type(error).__name__),file=sys.stderr)
        raise SystemExit(1) from None
