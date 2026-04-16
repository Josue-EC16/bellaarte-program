from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.services.seed_service import seed_security


def main() -> None:
    db = SessionLocal()
    try:
        seed_security(db)
        print("Seed de seguridad ejecutado correctamente.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
