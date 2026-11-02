"""Explicitly authorized local deployment. Never contains connection secrets."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

STAGE = Path(__file__).resolve().parent
ROOT = STAGE.parent
BACKEND = ROOT / "backend"
POINTER = STAGE / "deployment_location.json"
PG = Path(r"C:\laragon\bin\postgresql\postgresql-17.9-1\bin")
sys.path.insert(0, str(BACKEND))


def configuration():
    from app.core.config import Settings
    from sqlalchemy.engine import make_url
    settings = Settings(_env_file=BACKEND / ".env")
    url = make_url(settings.effective_database_url)
    assert url.host in {"localhost", "127.0.0.1"}
    assert (url.port or 5432) == 5432 and url.database == "bellaarte_db"
    return settings, url


def connect(url, readonly=True):
    import psycopg2
    connection = psycopg2.connect(host=url.host, port=url.port or 5432,
        dbname=url.database, user=url.username, password=url.password,
        application_name="BAB_ECONOMY_AUTHORIZED_DEPLOYMENT", connect_timeout=5,
        options="-c statement_timeout=30000 -c lock_timeout=5000")
    connection.set_session(readonly=readonly)
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(),inet_server_port()")
        assert cursor.fetchone() == ("bellaarte_db", 5432)
    return connection


def fingerprint(connection, columns=None):
    from psycopg2 import sql
    if columns is None:
        columns = {}
        with connection.cursor() as cursor:
            cursor.execute("""SELECT c.table_name,c.column_name FROM information_schema.columns c
                JOIN information_schema.tables t ON t.table_schema=c.table_schema AND t.table_name=c.table_name
                WHERE c.table_schema='public' AND t.table_type='BASE TABLE' AND c.table_name<>'alembic_version'
                ORDER BY c.table_name,c.ordinal_position""")
            for table, column in cursor.fetchall():
                columns.setdefault(table, []).append(column)
    result = {}
    with connection.cursor() as cursor:
        for table, names in columns.items():
            query = sql.SQL("""SELECT count(*),md5(coalesce(string_agg(row_to_json(t)::text,
                E'\\n' ORDER BY row_to_json(t)::text),'')) FROM (SELECT {} FROM public.{}) t""").format(
                    sql.SQL(",").join(map(sql.Identifier, names)), sql.Identifier(table))
            cursor.execute(query)
            count, digest = cursor.fetchone()
            result[table] = {"count": count, "digest": digest}
    return columns, result


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def location():
    directory = Path(json.loads(POINTER.read_text(encoding="utf-8"))["private_directory"])
    expected = Path(os.environ["LOCALAPPDATA"]) / "BAB_VDOS" / "economy-deployments"
    assert directory.resolve().is_relative_to(expected.resolve())
    return directory


def prepare():
    assert not POINTER.exists(), "An existing deployment must be inspected before reuse."
    settings, url = configuration()
    items = json.loads((STAGE / "cambios.json").read_text(encoding="utf-8"))
    for item in items:
        target = ROOT / item["path"]
        assert target.resolve().is_relative_to(ROOT.resolve())
        assert (hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None) == item["baseline_sha256"]
        assert hashlib.sha256((STAGE / item["path"]).read_bytes()).hexdigest() == item["prepared_sha256"]
    directory = Path(os.environ["LOCALAPPDATA"]) / "BAB_VDOS" / "economy-deployments" / datetime.now().strftime("%Y%m%d-%H%M%S")
    directory.mkdir(parents=True, exist_ok=False)
    write_json(POINTER, {"private_directory": str(directory)})
    connection = connect(url)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version_num FROM alembic_version")
            assert cursor.fetchone()[0] == "20261018_0014"
            cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()")
            assert cursor.fetchone()[0] == 0, "Other database clients remain; do not migrate while writers may exist."
        columns, before = fingerprint(connection)
    finally:
        connection.close()
    for item in items:
        source = ROOT / item["path"]
        if source.exists():
            target = directory / "source-before" / item["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("PG")}
    environment["PGPASSWORD"] = url.password or ""
    environment["PGCONNECT_TIMEOUT"] = "5"
    dump = directory / "bellaarte_db-before-economy.dump"
    with (directory / "backup-errors.log").open("wb") as errors:
        subprocess.run([str(PG / "pg_dump.exe"), "--host", url.host, "--port", "5432",
            "--username", url.username, "--dbname", "bellaarte_db", "--format=custom", "--file", str(dump)],
            env=environment, stdout=subprocess.DEVNULL, stderr=errors, check=True)
        with (directory / "backup-index.txt").open("wb") as index:
            subprocess.run([str(PG / "pg_restore.exe"), "--list", str(dump)], stdout=index, stderr=errors, check=True)
        subprocess.run([str(PG / "pg_restore.exe"), "--file", os.devnull, str(dump)],
            stdout=subprocess.DEVNULL, stderr=errors, check=True)
    assert dump.stat().st_size > 0
    write_json(directory / "manifest.json", {"time_utc": datetime.now(timezone.utc).isoformat(),
        "database": "bellaarte_db", "port": 5432, "revision_before": "20261018_0014",
        "dump_bytes": dump.stat().st_size, "dump_sha256": hashlib.sha256(dump.read_bytes()).hexdigest(),
        "columns_before": columns, "data_before": before, "files": items,
        "full_restore_rehearsed": False, "state": "backup_verified"})
    print("Private backup verified: custom archive, complete offline read, SHA-256; source recovery copy saved.")


def promote_and_migrate():
    directory = location()
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["state"] == "backup_verified"
    for item in manifest["files"]:
        target = ROOT / item["path"]
        assert (hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None) == item["baseline_sha256"]
        prepared = STAGE / item["path"]
        assert hashlib.sha256(prepared.read_bytes()).hexdigest() == item["prepared_sha256"]
    for item in manifest["files"]:
        target = ROOT / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(STAGE / item["path"], target)
    settings, url = configuration()
    # Import settings only after verified configuration; Alembic uses the explicit URL.
    from app.core.config import settings as active_settings
    active_settings.database_url = settings.effective_database_url
    from alembic import command
    from alembic.config import Config
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    command.upgrade(config, "20261018_0016")
    connection = connect(url)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version_num FROM alembic_version")
            assert cursor.fetchone()[0] == "20261018_0016"
            cursor.execute("SELECT count(*) FROM corte_caja WHERE control_version<>0 OR cierre_snapshot IS NOT NULL")
            assert cursor.fetchone()[0] == 0, "Legacy cuts were unexpectedly reclassified."
            for table in ("movimiento_economico", "constancia_devolucion", "solicitud_economica"):
                cursor.execute("SELECT count(*) FROM " + table)
                assert cursor.fetchone()[0] == 0
        _, after = fingerprint(connection, manifest["columns_before"])
        assert after == manifest["data_before"], "Historical business data changed; inspect before reopening."
    finally:
        connection.close()
    manifest.update(state="migrated_data_preserved", revision_after="20261018_0016",
        migrated_time_utc=datetime.now(timezone.utc).isoformat(), data_after=after)
    write_json(directory / "manifest.json", manifest)
    print("Promoted 63 reviewed files; revision 0016 verified. All prior business rows/values preserved; no controlled movements created.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "promote"])
    action = parser.parse_args().action
    if action == "prepare":
        prepare()
    else:
        promote_and_migrate()
