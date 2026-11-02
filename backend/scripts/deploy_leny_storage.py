"""Deploy only reviewed LENY storage to the explicitly authorized local ERP.

Default is read-only inspection. --apply creates a private verified dump before
upgrading 0016/0017 -> 0018. Never seeds, restores, downgrades or changes real users.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def public_structure(connection):
    from sqlalchemy import text
    queries = {
        "columns": """SELECT table_name,column_name,ordinal_position,data_type,udt_name,is_nullable,column_default
            FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name,ordinal_position""",
        "constraints": """SELECT c.relname,k.conname,pg_get_constraintdef(k.oid)
            FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public'
            ORDER BY c.relname,k.conname""",
        "indexes": """SELECT tablename,indexname,indexdef FROM pg_indexes
            WHERE schemaname='public' ORDER BY tablename,indexname""",
    }
    return {key: [list(row) for row in connection.execute(text(query)).all()] for key, query in queries.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    from app.core.config import Settings, settings
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url

    configured = Settings(_env_file=BACKEND / ".env")
    url = make_url(configured.effective_database_url)
    if url.host not in {"localhost", "127.0.0.1"} or (url.port or 5432) != 5432 or url.database != "bellaarte_db" or url.query:
        raise RuntimeError("Unexpected target; refusing any deployment.")
    engine = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 5,
                            "options": "-c lock_timeout=5000 -c statement_timeout=30000"})
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            identity = connection.execute(text("SELECT current_database(),current_user,inet_server_port()")).one()
            if (identity[0], identity[2]) != ("bellaarte_db", 5432) or identity[1] != url.username:
                raise RuntimeError("Connected identity mismatch.")
            revision = connection.execute(text("SELECT version_num FROM public.alembic_version")).scalar_one()
            schema = connection.execute(text("SELECT to_regnamespace('leny')::text")).scalar_one()
            if not ((revision == "20261018_0016" and schema is None)
                    or (revision == "20261019_0017" and schema == "leny")):
                raise RuntimeError("Expected reviewed revision0016 without LENY or revision0017 with LENY; inspect before changing anything.")
            if not connection.execute(text("SELECT has_database_privilege(current_database(),'CREATE')")).scalar_one():
                raise RuntimeError("Migration identity cannot create the LENY schema.")
            before = public_structure(connection)
        print("Verified target: bellaarte_db:5432; revision=" + revision + ".", flush=True)
        if not args.apply:
            print("Inspection only. No files, backup or database changes.")
            return

        pg_root = Path(r"C:\laragon\bin\postgresql\postgresql-17.9-1\bin")
        dump_tool, restore_tool = pg_root / "pg_dump.exe", pg_root / "pg_restore.exe"
        if not dump_tool.is_file() or not restore_tool.is_file():
            raise RuntimeError("Installed PostgreSQL backup tools are required.")
        directory = BACKEND / "storage" / "backups" / ("leny-deployment-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
        directory.mkdir(parents=True, exist_ok=False)
        dump = directory / "bellaarte_db-before-leny.dump"
        environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("PG")}
        environment["PGPASSWORD"] = url.password or ""
        environment["PGCONNECT_TIMEOUT"] = "5"
        with (directory / "backup-errors.log").open("wb") as errors:
            subprocess.run([str(dump_tool), "--host", url.host, "--port", "5432", "--username", url.username,
                            "--dbname", "bellaarte_db", "--format=custom", "--file", str(dump)],
                           env=environment, stdout=subprocess.DEVNULL, stderr=errors, check=True)
            with (directory / "backup-index.txt").open("wb") as index:
                subprocess.run([str(restore_tool), "--list", str(dump)], stdout=index, stderr=errors, check=True)
            subprocess.run([str(restore_tool), "--file", os.devnull, str(dump)],
                           stdout=subprocess.DEVNULL, stderr=errors, check=True)
        if dump.stat().st_size == 0:
            raise RuntimeError("Empty backup; refusing migration.")
        report = {"time_utc": datetime.now(timezone.utc).isoformat(), "database": "bellaarte_db", "port": 5432,
                  "revision_before": revision, "revision_after": None, "backup_bytes": dump.stat().st_size,
                  "backup_sha256": hashlib.sha256(dump.read_bytes()).hexdigest(), "backup_offline_read": True,
                  "restore_rehearsed": False, "state": "backup_verified"}
        report_file = directory / "deployment.json"
        report_file.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print("Custom backup verified (index + complete offline read + SHA256).", flush=True)

        from alembic import command
        from alembic.config import Config
        settings.database_url = configured.effective_database_url
        configuration = Config(str(BACKEND / "alembic.ini"))
        configuration.set_main_option("script_location", str(BACKEND / "alembic"))
        previous_options = os.environ.get("PGOPTIONS")
        try:
            os.environ["PGOPTIONS"] = "-c lock_timeout=5000 -c statement_timeout=30000"
            command.upgrade(configuration, "20261019_0018")
        finally:
            if previous_options is None:
                os.environ.pop("PGOPTIONS", None)
            else:
                os.environ["PGOPTIONS"] = previous_options

        with engine.connect() as connection:
            connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            after_revision = connection.execute(text("SELECT version_num FROM public.alembic_version")).scalar_one()
            if after_revision != "20261019_0018" or public_structure(connection) != before:
                raise RuntimeError("Post-migration verification mismatch; inspect without restoring automatically.")
            for table in ("conversaciones", "mensajes", "rate_users", "admissions"):
                if not connection.execute(text("SELECT has_schema_privilege('leny','USAGE')")).scalar_one():
                    raise RuntimeError("Runtime schema access is missing.")
                for permission in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                    if not connection.execute(text("SELECT has_table_privilege(:table,:permission)"),
                                              {"table": "leny." + table, "permission": permission}).scalar_one():
                        raise RuntimeError("Runtime table access is missing.")
                connection.execute(text('SELECT 1 FROM leny.' + table + ' LIMIT 0'))
            report.update(revision_after=after_revision, public_structure_unchanged=True,
                          runtime_schema_and_dml_permissions=True, state="verified")
        report_file.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print("LENY migration0018 applied; public structure unchanged; runtime permissions verified.")
        print("Private deployment report: " + str(report_file))
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Never serialize database errors, connection strings or bind values.
        print("LENY deployment stopped: " + (str(error) if type(error) is RuntimeError else type(error).__name__), file=sys.stderr)
        raise SystemExit(1) from None
