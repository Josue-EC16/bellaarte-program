"""Explicit library housekeeping. Review the configured database/root before --apply."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Reconcile uploads and permanently purge expired library trash.')
    args = parser.parse_args()
    if not args.apply:
        print('Proposal only. --apply reconciles library operations and purges expired trash; no action performed.')
        return 0
    from app.core.config import settings
    from app.core.database import SessionLocal
    from app.services.leny_document_service import DocumentService
    from app.services.leny_document_maintenance import maintain
    try:
        maintain(DocumentService(settings, SessionLocal))
    except Exception:
        print('DOCUMENT_MAINTENANCE_FAILED: review private storage and database availability.', file=sys.stderr)
        return 1
    print('DOCUMENT_MAINTENANCE_COMPLETED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
