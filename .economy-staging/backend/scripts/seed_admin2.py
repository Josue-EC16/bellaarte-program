from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.services.seed_service import ensure_policy_files, seed_admin2_account, seed_roles, sync_policy_file


def main() -> None:
    db = SessionLocal()
    try:
        seed_roles(db)
        ensure_policy_files()
        sync_policy_file()
        seed_admin2_account(db)
        print("Seed de ADMIN2 ejecutado correctamente.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
