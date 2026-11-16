"""Reconcile only a request created by this private review, after proven unload.

No model unload/restart, worker changes or unconditional clearing of quarantine.
"""
import asyncio
import json
import os
from pathlib import Path
import sys
from uuid import UUID

import httpx
from sqlalchemy import create_engine, text

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


async def main():
    from app.core.config import Settings
    from app.services.leny_coordination import PostgresCoordinator, PostgresLease
    from app.services.leny_inference_state import InferenceState
    from sqlalchemy.orm import sessionmaker
    config = Settings(_env_file=BACKEND/'.env')
    root = Path(os.environ['LOCALAPPDATA'])/'BAB_VDOS/leny-gemini-spec02/review'
    requests = {UUID(row['request_id']) for f in (root/'results').glob('*.json')
                for row in json.loads(f.read_text(encoding='utf-8'))['cases']}
    coordinator = PostgresCoordinator(config.effective_database_url)
    lease = PostgresLease(coordinator.engine, allow_quarantine=True)
    engine = create_engine(config.effective_database_url)
    try:
        with engine.connect() as db:
            row = db.execute(text('SELECT state,request_id,model FROM leny.inferencia_estado WHERE id=1')).one()
            if row.state != 'uncertain' or row.request_id not in requests:
                raise RuntimeError('Not an uncertain request belonging to this review')
            if db.scalar(text("SELECT EXISTS(SELECT 1 FROM leny.rag_trabajos WHERE status IN ('queued','running'))")):
                raise RuntimeError('Document jobs active')
            if db.scalar(text('SELECT EXISTS(SELECT 1 FROM leny.rag_workers WHERE provider_inflight OR unsafe_reason IS NOT NULL)')):
                raise RuntimeError('Worker inference unresolved')
        async with httpx.AsyncClient(base_url=config.leny_ollama_url,trust_env=False,timeout=5) as client:
            for attempt in range(2):
                result = await client.get('/api/ps');result.raise_for_status()
                if any(model.get('name') in {row.model,config.leny_rag_model}
                       for model in result.json()['models']):
                    raise RuntimeError('Model still loaded; no state changed')
                lease.check()
                if not attempt:await asyncio.sleep(1)
        InferenceState(sessionmaker(bind=engine)).finish(lease,row.request_id,True)
        print('Own review quarantine reconciled after twice-confirmed model absence; no services stopped.')
    finally:
        lease.close();engine.dispose();coordinator.engine.dispose()


if __name__=='__main__':
    asyncio.run(main())
