"""One bounded USD/BOB job, suitable for Windows Task Scheduler, not Uvicorn."""
import argparse
from datetime import datetime, timezone
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspect", action="store_true", help="Read-only state; never invokes the provider or writes notifications")
    args = parser.parse_args()
    os.chdir(BACKEND)
    from app.core.config import settings
    from app.core.database import SessionLocal, engine
    from app.core.backup_runtime import is_backup_lock_active
    from app.services.exchange_rate_sync_query import sync_state
    from app.services.exchange_rate_sync_service import run_sync, sync_job_lock
    from app.schemas.exchange_rate_sync import ExchangeRateSyncStateResponse
    from sqlalchemy import text
    if args.inspect:
        with SessionLocal() as db:
            db.execute(text("SET TRANSACTION READ ONLY"))
            print(ExchangeRateSyncStateResponse(**sync_state(db, config=settings)).model_dump_json())
        return 0
    directory = Path(os.environ.get("LOCALAPPDATA", BACKEND / "storage")) / "BAB_VDOS/tc02-runtime"
    directory.mkdir(parents=True, exist_ok=True)
    from app.services.leny_document_storage import protect_directory
    protect_directory(directory)
    logger = logging.getLogger("bab.exchange_rate.sync")
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(directory / "sync.log", maxBytes=1024*1024, backupCount=3, encoding="utf-8")
    logger.addHandler(handler)
    try:
        with sync_job_lock(engine) as check:
            if check is None:
                result = {"status":"skipped", "reason":"ALREADY_RUNNING", "requests":0}
            else:
                with SessionLocal() as db:
                    if db.scalar(text("SELECT version_num FROM alembic_version")) != "20261104_0023":
                        raise RuntimeError("SYNC_SCHEMA_NOT_READY")
                    db.commit()
                    result = run_sync(db, config=settings, check_lease=check, backup_active=is_backup_lock_active)
        logger.info(json.dumps(dict(result, time_utc=datetime.now(timezone.utc).isoformat())))
        if sys.stdout is not None:
            print(json.dumps(result))
        return 0
    except Exception as error:
        logger.error(json.dumps({"status":"failed", "category":type(error).__name__, "time_utc":datetime.now(timezone.utc).isoformat()}))
        if sys.stderr is not None:
            print("USD synchronization failed; inspect the private runtime log.", file=sys.stderr)
        return 1
    finally:
        handler.close()
        logger.removeHandler(handler)
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
