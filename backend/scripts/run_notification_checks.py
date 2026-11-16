from pathlib import Path
import argparse
import json
import logging
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Chequeos de notificaciones por lotes; usa la base configurada.")
    parser.add_argument("--mode", choices=("daily", "retry-emails"), default="daily")
    args = parser.parse_args()
    # Parsing --help must not import application configuration or create an engine.
    from app.core.database import SessionLocal, engine
    from app.services.notification_job_service import notification_job_lock, retry_failed_email_notifications, run_daily_notification_checks

    try:
        with notification_job_lock(engine, args.mode) as acquired:
            if not acquired:
                print(json.dumps({"status": "skipped", "reason": "ALREADY_RUNNING", "mode": args.mode}))
                return 0
            with SessionLocal() as db:
                result = retry_failed_email_notifications(db) if args.mode == "retry-emails" else run_daily_notification_checks(db)
                print(json.dumps({"mode": args.mode, **result}, ensure_ascii=True))
                return 1 if result["status"] == "failed" else 0
    except Exception as error:
        logging.getLogger(__name__).error("NOTIFICATION_JOB_FAILED category=%s", type(error).__name__)
        print(json.dumps({"status": "failed", "mode": args.mode, "reason": "JOB_FAILED"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
