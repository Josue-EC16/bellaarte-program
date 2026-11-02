"""Bounded housekeeping, independent of Ollama and of future RAG workers."""
import logging

import anyio


def maintain(service):
    with service.lock():
        service.recover()
        service.expire()
        if service.settings.leny_rag_enabled:
            from app.services.leny_rag_service import cleanup_staging
            with service.transaction() as db:
                cleanup_staging(db, service.settings.leny_rag_staging_retention_days)


async def maintenance_loop(service, interval):
    while True:
        try:
            await anyio.to_thread.run_sync(maintain, service)
        except Exception:
            logging.getLogger(__name__).warning('LENY_DOCUMENT_MAINTENANCE_DEFERRED')
        await anyio.sleep(interval)
