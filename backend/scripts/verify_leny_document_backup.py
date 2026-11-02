"""Verify a private bundle; optionally restore files to a NEW isolated directory."""
import argparse
import json
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.leny_document_backup import restore_bundle_files, verify_bundle
from app.services.leny_document_storage import DocumentError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--isolated-restore-files', type=Path, metavar='NEW_PRIVATE_DIRECTORY',
                        help='Extrae originales y database.dump en un directorio nuevo fuera del webroot. No restaura PostgreSQL.')
    args = parser.parse_args()
    try:
        if args.isolated_restore_files:
            result = restore_bundle_files(args.bundle, args.isolated_restore_files)
        else:
            result = verify_bundle(args.bundle)
    except DocumentError as error:
        print(json.dumps({'verified': False, 'code': error.code, 'message': error.message}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
