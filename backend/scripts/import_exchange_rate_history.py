"""Validate a local verified one-month CSV; import only with explicit --apply.

CSV headers: fecha_objetivo,valor_bob. A separate JSON manifest must declare
verified=true, official_source, verified_by, verified_at (timezone included),
period_start, period_end and the exact dataset_sha256. No network is used.
Dry-run never imports settings, loads .env, connects to PostgreSQL or writes.
"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def read_verified_dataset(csv_path: Path, manifest_path: Path):
    from fastapi import HTTPException
    from app.services.exchange_rate_history_service import validate_history_rows
    raw = csv_path.read_bytes()
    provenance = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    actual = hashlib.sha256(raw).hexdigest()
    if not isinstance(provenance, dict) or provenance.get("dataset_sha256", "").lower() != actual:
        raise HTTPException(422, detail="SHA-256 del dataset no coincide con el manifiesto verificado.")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if reader.fieldnames != ["fecha_objetivo", "valor_bob"]:
        raise HTTPException(422, detail="CSV requiere exactamente fecha_objetivo,valor_bob en ese orden.")
    rows = list(reader)
    if len(rows) > 31 or any(set(row) != {"fecha_objetivo", "valor_bob"} for row in rows):
        raise HTTPException(422, detail="Dataset fuera de formato o límite de un mes.")
    validate_history_rows(rows, provenance)
    return rows, provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--target", choices=("testing", "business"), default="testing")
    parser.add_argument("--database-url-env", default="TEST_DATABASE_URL", help="Explicit environment variable, never .env fallback")
    parser.add_argument("--approve-business-import", action="store_true", help="Separate explicit approval for this verified dataset")
    args = parser.parse_args()
    rows, provenance = read_verified_dataset(args.csv, args.manifest)
    if not args.apply:
        print(json.dumps({"validated_rows": len(rows), "dataset_sha256": provenance["dataset_sha256"],
                          "mode": "dry_run", "database_connected": False, "imported": False}))
        return
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url
    from sqlalchemy.orm import Session
    from app.services.exchange_rate_history_service import import_history
    supplied = os.environ.get(args.database_url_env)
    if not supplied:
        raise RuntimeError("Explicit database environment variable is required; no application fallback.")
    url = make_url(supplied)
    expected_database, expected_port = ("bab_vdos_testing", 55432) if args.target == "testing" else ("bellaarte_db", 5432)
    if (url.drivername not in {"postgresql", "postgresql+psycopg2"} or url.host not in {"localhost", "127.0.0.1"}
            or (url.port or 5432) != expected_port or url.database != expected_database or url.query or not url.password):
        raise RuntimeError("Explicit database target does not match approved local destination.")
    if args.target == "business" and not args.approve_business_import:
        raise RuntimeError("A business import requires separate explicit dataset approval.")
    engine = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 5,
        "options": "-c lock_timeout=5000 -c statement_timeout=30000"})
    try:
        with Session(engine) as db:
            if db.scalar(text("SELECT current_database()")) != expected_database or db.scalar(text("SELECT inet_server_port()")) != expected_port:
                raise RuntimeError("Connected target differs from the explicitly selected destination.")
            if args.target == "testing":
                manifest_file = os.environ.get("TEST_PG_MANIFEST")
                if not manifest_file:
                    raise RuntimeError("Testing requires its independently provisioned manifest.")
                marker = json.loads(Path(manifest_file).read_text(encoding="utf-8-sig"))
                if db.scalar(text("SELECT instance_id FROM testing_control.instance")) != marker.get("instance_id"):
                    raise RuntimeError("Isolated testing identity mismatch.")
            if db.scalar(text("SELECT version_num FROM alembic_version")) != "20261104_0023":
                raise RuntimeError("Import requires reviewed migration0023; no migration is run automatically.")
            result = import_history(db, rows=rows, provenance=provenance)
            print(json.dumps(dict(result, dataset_sha256=provenance["dataset_sha256"], target=args.target)))
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Never echo provider contents, URLs with passwords or raw SQL errors.
        from fastapi import HTTPException
        safe = error.detail if isinstance(error, HTTPException) else type(error).__name__
        print("Historical import stopped: " + str(safe), file=sys.stderr)
        raise SystemExit(1) from None
