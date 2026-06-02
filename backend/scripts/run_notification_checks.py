from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.services.notification_job_service import retry_failed_email_notifications, run_daily_notification_checks


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecuta chequeos programados del módulo de notificaciones.")
    parser.add_argument(
        "--mode",
        choices=("daily", "retry-emails"),
        default="daily",
        help="Modo diario completo o reintento técnico de correos fallidos.",
    )
    args = parser.parse_args()
    db = SessionLocal()
    try:
        if args.mode == "retry-emails":
            print(retry_failed_email_notifications(db))
        else:
            print(run_daily_notification_checks(db))
    finally:
        db.close()


if __name__ == "__main__":
    main()
