"""Real backend acceptance probe on the owner's existing LENY identity.

No HTTP/JWT shortcut: reuses the account from the owner's latest V1.1 review,
revalidates reader/Casbin, and runs the normal service, quota and inference lease.
Creates new review conversations, never modifies commercial/library records.
All questions, responses and source text are saved only in protected local storage.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
from time import monotonic
from uuid import uuid4

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.config import Settings
from app.schemas.leny import LenyChatRequest
from app.services.leny_store import LenyActor, LenyStore
from app.services.leny_coordination import PostgresCoordinator
from app.services.leny_inference_state import InferenceState
from app.services.leny_ollama import OllamaProvider, LenyError
from app.services.leny_rag_retrieval import RetrievalService, reader
from app.services.leny_rag_sources import SourceService
from app.services.leny_rate_limit import RateLimiter
from app.services.leny_service import LenyService
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from verify_leny_v11_production import PRIVATE, prepare, write, Monitor

QUESTIONS = ['RESUME QUE HACE LA ENCARGADA DE LA BOUTIQUE',
             '¿Cómo se confecciona un vestido?',
             'QUIERO SABER COMO QUEDAR LA FECHA DE LA PRIEMRA PRUEBA']


def inspect(args):
    import re
    from app.services.leny_rag_synthesis import numbers, units, source_passages
    report = json.loads((PRIVATE/('backend-review-'+args.run_id+'.json')).read_text(encoding='utf-8'))
    for case in report['cases']:
        raw = case['capture'].get('raw')
        details = []
        if raw:
            for block in json.loads(raw).get('blocks', []):
                label = block.get('source', '')
                if not re.fullmatch(r'S[1-5]', label):
                    details.append({'kind': block.get('kind'), 'empty_reference': not label})
                    continue
                source = case['sources'][int(label[1:])-1]
                passages = dict(source_passages(source, int(label[1:])))
                refs = block.get('support', [])
                support = '\n'.join(passages.get(pid, '') for pid in refs) if isinstance(refs, list) else passages.get(refs, refs)
                content = block.get('text', '')
                unnumbered = re.sub(r'(?m)(?:^|\n)\s*\d+[.)]\s+', '', content)
                same_document = [row for row in case['sources'] if source.get('indexation_id')
                    and row.get('indexation_id') == source['indexation_id']]
                joined = ' '.join(row['text'] for row in same_document) or source['text']
                details.append({'kind': block.get('kind'), 'support_chars': len(support),
                    'novel_numbers': len(numbers(content)-numbers(source['text'])),
                    'novel_units': len(units(content)-units(source['text'])),
                    'same_document_supports_numbers_units': numbers(content) <= numbers(joined) and units(content) <= units(joined),
                    'enumeration_only': numbers(unnumbered) <= numbers(source['text'])})
        print(json.dumps({'case': case['case'], 'validation_details': details}))


async def run(args):
    config = Settings(_env_file=BACKEND/'.env')
    prepare()
    destination = PRIVATE/('backend-review-'+args.run_id+'.json')
    if destination.exists():
        raise RuntimeError('Preserve existing review output')
    engine = create_engine(config.effective_database_url)
    sessions = sessionmaker(engine)
    with sessions() as db, db.begin():
        db.execute(text('SET TRANSACTION READ ONLY'))
        if db.scalar(text('SELECT current_database()')) != 'bellaarte_db':
            raise RuntimeError('Unexpected database')
        owner = db.execute(text("""SELECT c.account_id,c.user_id FROM leny.conversaciones c
            JOIN leny.mensajes m ON m.conversation_id=c.id WHERE m.role='assistant'
            AND m.policy_version='rag-v11-synthesis-v1' ORDER BY m.created_at DESC LIMIT 1""")).mappings().one()
        actor = LenyActor(owner['account_id'], owner['user_id'], str(uuid4()), user_agent='LENY-authorized-backend-review')
        reader(db, actor)
    capture = {}
    class Provider(OllamaProvider):
        async def structured(self, messages, schema):
            raw = await super().structured(messages, schema)
            capture['raw'] = raw
            capture['metrics'] = dict(self.metrics)
            return raw
    class Diagnostics(logging.Handler):
        def emit(self, record):
            if hasattr(record, 'leny_rag'):
                capture['diagnostics'] = record.leny_rag
    logger = logging.getLogger('app.services.leny_service')
    level = logger.level
    handler = Diagnostics()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    sources = SourceService(config, sessions)
    store = LenyStore(sessions, sources)
    service = LenyService(config, store, PostgresCoordinator(config.effective_database_url),
        provider_factory=lambda: Provider(config), sources=sources, retrieval=RetrievalService(config, sessions),
        rate_limiter=RateLimiter(sessions, config.leny_rate_limit, config.leny_rate_window_seconds),
        inference_state=InferenceState(sessions))
    report = {'time': datetime.now(timezone.utc).isoformat(), 'scope': 'normal_backend_pipeline_real_database_real_qwen',
              'actor': dict(owner), 'human_review': None, 'cases': []}
    try:
        for index, question in enumerate(QUESTIONS if args.case is None else [QUESTIONS[args.case-1]], 1):
            capture.clear()
            conversation = store.create(actor)
            payload = LenyChatRequest(conversation_id=conversation['id'], request_id=uuid4(), message=question)
            events = []
            turn = None
            started = monotonic()
            failure = None
            with Monitor() as monitor:
                try:
                    turn = await service.prepare(actor, payload)
                    try:
                        async for event in turn.events():
                            events.append(json.loads(event))
                    finally:
                        await turn.close()
                except LenyError as error:
                    failure = error.code
            raw = capture.get('raw')
            validation = None
            if raw and turn:
                from app.services.leny_rag_synthesis import validate
                try:
                    validate(raw, turn.fragments, allow_general=turn.decision.reason in {'v11_mixed','v11_drafting','v11_advice'})
                    validation = 'accepted'
                except (ValueError,TypeError,KeyError) as error:
                    validation = str(error)
            final = events[-1] if events else {}
            item = {'case': args.case or index, 'question': question, 'conversation_id': conversation['id'],
                    'events': events, 'capture': dict(capture), 'failure': failure,
                    'validation': validation, 'seconds': round(monotonic()-started,3), 'samples': monitor.samples,
                    'sources': turn.fragments if turn else []}
            report['cases'].append(json.loads(json.dumps(item, default=str)))
            write(destination, report)
            print(json.dumps({'case': item['case'], 'seconds': item['seconds'], 'final': final.get('type'),
                'outcome': final.get('outcome'), 'reason': final.get('reason_code'), 'failure': failure,
                'validation': validation, 'synthesis_generated': bool(raw), 'sources': len(final.get('sources',[])),
                'diagnostics': capture.get('diagnostics')}), flush=True)
    finally:
        logger.removeHandler(handler)
        logger.setLevel(level)
        engine.dispose()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--case', type=int, choices=(1,2,3))
    parser.add_argument('--inspect-only', action='store_true')
    arguments = parser.parse_args()
    if not arguments.run_id.replace('-', '').isalnum():
        parser.error('Use an alphanumeric run identifier')
    try:
        if arguments.inspect_only:
            inspect(arguments)
        else:
            asyncio.run(run(arguments))
    except Exception as error:
        print(json.dumps({'failed': type(error).__name__, 'code': getattr(error, 'code', None)}))
        raise SystemExit(1)
