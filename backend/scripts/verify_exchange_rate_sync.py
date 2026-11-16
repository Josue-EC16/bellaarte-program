"""Read-only TC02 deployment evidence; compare archive COPY without restoring it.

Never prints account/user contents, passwords, connection URLs or archive rows.
"""
import argparse
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deployment-manifest",type=Path,required=True)
    parser.add_argument("--evidence",type=Path,required=True)
    args=parser.parse_args()
    os.chdir(BACKEND)
    from sqlalchemy import create_engine,text
    from sqlalchemy.orm import Session
    from psycopg2 import sql
    import httpx
    from app.core.config import settings
    from app.schemas.exchange_rate_sync import ExchangeRateSyncStateResponse
    from app.services.exchange_rate_sync_query import sync_state
    report=json.loads(args.deployment_manifest.read_text(encoding="utf-8"))
    engine=create_engine(settings.effective_database_url,hide_parameters=True,connect_args={"connect_timeout":5,
        "options":"-c default_transaction_read_only=on -c statement_timeout=15000"})
    try:
        with Session(engine) as db:
            if db.scalar(text("SELECT current_database()")) != "bellaarte_db":
                raise RuntimeError("Unexpected original target.")
            revision=db.scalar(text("SELECT version_num FROM alembic_version"))
            state=ExchangeRateSyncStateResponse(**sync_state(db,config=settings)).model_dump(mode="json")
            records=[dict(row._mapping) for row in db.execute(text("SELECT tcs_id,tcs_fecha_objetivo,tcs_num_intento,tcs_estado,tcs_codigo_http FROM tipo_cambio_registros ORDER BY tcs_id"))]
            recipients=dict(db.execute(text("SELECT r.codigo,count(*) FROM notificacion n JOIN usuarios u ON u.id=n.usu_id JOIN cuentas c ON c.usuario_id=u.id JOIN roles r ON r.id=c.rol_id WHERE n.not_tipo LIKE 'TC_SYNC_%' GROUP BY r.codigo")).all())
            duplicates=db.scalar(text("SELECT count(*) FROM (SELECT mon_id FROM tipo_cambio_moneda WHERE tcm_activo GROUP BY mon_id HAVING count(*)>1) d"))
        comparisons={}
        dump=Path(report["backup_path"]).with_suffix(".dump")
        raw=engine.raw_connection()
        try:
            for table in ("venta_boutique","pago_pedido","salida_flete","comprobante_interno","moneda","usuarios","cuentas","roles","tipo_cambio_moneda"):
                archived=subprocess.run([r"C:\laragon\bin\postgresql\postgresql-17.9-1\bin\pg_restore.exe","--data-only","--table="+table,"--file=-",str(dump)],
                    capture_output=True,check=True,timeout=30).stdout.decode("utf-8")
                match=re.search(r"^COPY public\."+table+r" \((.*?)\) FROM stdin;\r?\n",archived,re.M)
                if match is None:
                    raise RuntimeError("Archive table missing: "+table)
                columns=[column.strip().strip('"') for column in match.group(1).split(",")]
                before=archived[match.end():].split("\n\\.")[0].rstrip("\r\n").splitlines()
                query=sql.SQL("COPY (SELECT {} FROM {}) TO STDOUT").format(sql.SQL(",").join(map(sql.Identifier,columns)),sql.Identifier("public",table))
                if table=="tipo_cambio_moneda":
                    index=columns.index("tcm_activo")
                    ids=[int(row.split("\t")[columns.index("tcm_id")]) for row in before]
                    columns.pop(index)
                    before=["\t".join(value for n,value in enumerate(row.split("\t")) if n!=index) for row in before]
                    query=sql.SQL("COPY (SELECT {} FROM {} WHERE tcm_id=ANY({})) TO STDOUT").format(
                        sql.SQL(",").join(map(sql.Identifier,columns)),sql.Identifier("public",table),sql.Literal(ids))
                output=io.StringIO()
                # pg_dump COPY uses the server zone. Retain that same zone;
                # changing to UTC would change textual timestamp representation.
                with raw.cursor() as cursor:
                    cursor.copy_expert(query.as_string(cursor),output)
                after=output.getvalue().rstrip("\r\n").splitlines()
                same=sorted(before)==sorted(after)
                comparisons[table]=dict(rows_before=len(before),rows_after=len(after),unchanged=same)
                if table=="tipo_cambio_moneda":
                    comparisons[table]["excluded_expected_activation_change"]=True
                if not same:
                    raise RuntimeError("Archive comparison differs: "+table)
        finally:
            raw.rollback()
            raw.close()
        task_output=subprocess.run(["powershell.exe","-NoProfile","-Command",
            "Get-ScheduledTaskInfo -TaskName BAB_VDOS_USD_BOB_SYNC | Select-Object LastTaskResult,@{Name='LastRunTime';Expression={$_.LastRunTime.ToString('o')}},@{Name='NextRunTime';Expression={$_.NextRunTime.ToString('o')}} | ConvertTo-Json -Compress"],
            capture_output=True,text=True,check=True,timeout=15)
        task_info=json.loads(task_output.stdout)
        with httpx.Client(timeout=5,trust_env=False) as client:
            health=client.get("http://127.0.0.1:8000/health").status_code
            frontend=client.get("http://localhost:5173").status_code
        if not (state["status"]=="UPDATED" and state["official_today"] and state["attempts_used"]==1
                and len(records)==1 and not duplicates and recipients and set(recipients)=={"ADMIN"}
                and task_info["LastTaskResult"]==0 and health==200 and frontend==200):
            raise RuntimeError("First-run acceptance not satisfied; no evidence claimed.")
        evidence=dict(verified_at_utc=datetime.now(timezone.utc).isoformat(),revision=revision,
            deployment={key:report[key] for key in ("state","start_date","backup_sha256","backup_bytes","backup_offline_read",
                "includes_private_originals","schema_unchanged","existing_rows_unchanged_before_activation","existing_tables",
                "migrations_executed","restore_executed","initial_history_import_executed","health_200","automation_enabled","task")},
            state=state,records=records,notification_recipient_roles=recipients,task_runtime=task_info,
            archive_data_comparison=comparisons,health_http=health,frontend_http=frontend,active_duplicate_groups=duplicates)
        args.evidence.write_text(json.dumps(evidence,indent=2,default=str)+"\n",encoding="utf-8")
        print(json.dumps(evidence,default=str))
    finally:
        engine.dispose()


if __name__=="__main__":
    try:
        main()
    except Exception as error:
        print("TC02 read-only verification stopped: "+(str(error) if type(error) is RuntimeError else type(error).__name__),file=sys.stderr)
        raise SystemExit(1) from None
