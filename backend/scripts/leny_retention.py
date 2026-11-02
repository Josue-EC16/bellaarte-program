"""Manual LENY retention. Dry-run unless --apply; never scheduled by the ERP."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Delete eligible LENY conversations in the configured database.")
    arguments = parser.parse_args()
    from app.core.config import settings
    from app.core.database import SessionLocal
    from app.services.leny_store import LenyStore
    count = LenyStore(SessionLocal).purge(settings.leny_retention_days, apply=arguments.apply)
    print(f"LENY retention: {'deleted' if arguments.apply else 'eligible'}={count}; configured_days={settings.leny_retention_days}")


if __name__ == "__main__":
    main()
