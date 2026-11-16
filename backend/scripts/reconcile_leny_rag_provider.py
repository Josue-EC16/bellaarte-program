"""Explicit local reconciliation; never unloads another process's Ollama model.

Use after a crashed/uncertain worker. Requires no active worker and twice-confirmed
absence of the embedding model from /api/ps. Otherwise wait or restart Ollama
manually after checking other local applications; this script never restarts it.
"""
import asyncio
from datetime import timedelta
import json
from pathlib import Path
import sys

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))


def main():
    from sqlalchemy import select,text
    from app.core.config import settings
    from app.core.database import SessionLocal
    from app.models.leny_rag import LenyRagWorker as Worker
    from app.services.leny_coordination import PostgresCoordinator,PostgresLease
    from app.services.leny_document_service import now
    from app.services.leny_rag_service import RagService
    from app.services.leny_rag_embeddings import EmbeddingProvider
    from app.services.leny_rag_common import RagError
    service=RagService(settings,SessionLocal);service.require_enabled()
    coordinator=PostgresCoordinator(settings.effective_database_url)
    lease=PostgresLease(coordinator.engine,allow_quarantine=True)
    try:
        pending_models={settings.leny_rag_model}
        with service.documents.reading() as initial:
            chat_state=bool(initial.scalar(text("SELECT to_regclass('leny.inferencia_estado') IS NOT NULL")))
            if chat_state:
                pending_models.update(initial.execute(text("SELECT model FROM leny.inferencia_estado WHERE state<>'idle'")).scalars())
        async def confirm_absent():
            provider=EmbeddingProvider(settings)
            async with provider.client() as client:
                for attempt in range(2):
                    result=await provider.request(client,'GET','/api/ps')
                    if any(model.get('name') in pending_models for model in result.get('models',[])):
                        raise RagError('RAG_INFERENCE_UNCERTAIN')
                    lease.check()
                    if not attempt:await asyncio.sleep(1)
        with service.documents.lock(),service.documents.transaction() as db:
            if db.scalar(select(Worker.id).where(Worker.stopped_at.is_(None),Worker.heartbeat_at>now()-timedelta(seconds=settings.leny_rag_lease_seconds)).limit(1)):
                raise RagError('RAG_ALREADY_ACTIVE',409)
            asyncio.run(confirm_absent())
            cleared=0
            for worker in db.scalars(select(Worker).where(Worker.provider_inflight.is_(True) | Worker.unsafe_reason.is_not(None))):
                worker.provider_inflight,worker.provider_digest,worker.unsafe_reason=False,None,None
                worker.stopped_at=worker.stopped_at or now();cleared+=1
            service.documents.audit(db,None,'LENY_RAG_PROVIDER_RECONCILED','local')
            if chat_state:
                db.execute(text("UPDATE leny.inferencia_estado SET state='idle',request_id=NULL,model=NULL,phase=NULL,updated_at=clock_timestamp() WHERE id=1"))
        print(json.dumps({'reconciled_workers':cleared,'embedding_model_loaded':False,'ollama_restarted':False}))
    finally:
        lease.close();coordinator.engine.dispose();service.documents.engine.dispose()


if __name__=='__main__':
    try:main()
    except Exception as error:
        print(json.dumps({'reconciled':False,'code':getattr(error,'code','RAG_RECONCILIATION_FAILED')}))
        raise SystemExit(1) from None
