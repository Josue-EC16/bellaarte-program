from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.models.boutique_enums import TipoBackupBdEnum
from app.services.backup_service import run_backup_process


def main() -> None:
    parser = argparse.ArgumentParser(description="EJECUTA EL JOB DE BACKUPS DE BELLAARTE.")
    parser.add_argument(
        "--mode",
        choices=("weekly",),
        default="weekly",
        help="MODO OFICIAL DEL JOB PROGRAMADO.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        backup_type = TipoBackupBdEnum.SEMANAL if args.mode == "weekly" else TipoBackupBdEnum.LOGICO_COMPLETO
        result = run_backup_process(
            db,
            backup_type=backup_type,
            origin="AUTOMATICO",
            observation="BACKUP PROGRAMADO SEMANAL DOMINGO 02:00 AM.",
        )
        print(result.message)
        print(result.ruta_archivo)
    finally:
        db.close()


if __name__ == "__main__":
    main()
