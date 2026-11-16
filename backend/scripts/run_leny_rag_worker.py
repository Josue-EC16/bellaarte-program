"""Manual local contextualization worker. Ctrl+C stops without deleting jobs."""
import argparse
import json
import logging
from pathlib import Path
import signal
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--stop-file', type=Path)
    parser.add_argument('--shutdown-file', type=Path)
    args = parser.parse_args()
    if args.shutdown_file:
        from app.services.leny_runtime import valid_shutdown_file
        if args.stop_file or args.once or args.status or not valid_shutdown_file(args.shutdown_file):
            raise RuntimeError('Only a private backend-owned shutdown marker is accepted.')
    from app.core.config import settings
    from app.core.database import SessionLocal
    from app.services.leny_rag_service import RagService
    from app.services.leny_rag_worker import RagWorker
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    if args.status:
        service = RagService(settings, SessionLocal)
        try:
            print(json.dumps(service.status(), ensure_ascii=False))
        finally:
            service.documents.engine.dispose()
        return
    worker = RagWorker(settings, SessionLocal)
    if args.stop_file:
        from app.services.leny_rag_common import runtime_root
        from app.services.leny_document_storage import _check_path
        expected = runtime_root() / 'worker.stop'
        if args.stop_file.absolute() != expected.absolute():
            raise RuntimeError('Only the owned private worker stop marker is accepted.')
        _check_path(expected)
    signal.signal(signal.SIGINT, lambda *_:worker.stop.set())
    worker.run(once=args.once, stop_file=args.stop_file, shutdown_file=args.shutdown_file)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Public/operator output never contains DB errors, documents or paths.
        print(json.dumps({'state':'stopped', 'code':getattr(error,'code','RAG_WORKER_FAILED')}))
        raise SystemExit(1) from None
