"""Read-only, content-free diagnosis of the owner's V1.1 manual review."""
import json
from pathlib import Path
import sys
import re
import unicodedata
import asyncio
from time import monotonic
from uuid import uuid4

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.config import Settings
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.services.leny_rag_synthesis import messages, SCHEMA
from app.services.leny_rag_retrieval import ELIGIBLE, parameters, reader
from app.services.leny_store import LenyActor


def main():
    if '--revalidate' in sys.argv:
        from verify_leny_v11_production import PRIVATE
        from app.services.leny_rag_synthesis import validate
        results = []
        for path in sorted(PRIVATE.glob('corrective-probe-*.json'), key=lambda p: p.stat().st_mtime):
            report = json.loads(path.read_text(encoding='utf-8'))
            try:
                validate(report['captured']['raw'], report['sources'])
                results.append({'mechanical_validation': True})
            except (ValueError, KeyError, TypeError) as error:
                results.append({'mechanical_validation': False, 'reason': str(error)})
        print(json.dumps({'known_outputs_revalidated_not_human_review': results}))
        return
    if '--summary' in sys.argv:
        from verify_leny_v11_production import PRIVATE
        summaries = []
        for path in sorted(PRIVATE.glob('corrective-probe-*.json'), key=lambda p: p.stat().st_mtime):
            report = json.loads(path.read_text(encoding='utf-8'))
            samples = report.get('samples', [])
            summaries.append({key: report.get(key) for key in ('validated','failure','reason','seconds','metrics')} | {
                'ram_available_min_bytes': min((s['ram_available_bytes'] for s in samples), default=None),
                'gpu_peak_mib': max((s.get('gpu_memory_mib',0) for s in samples), default=None),
                'samples': len(samples)})
        print(json.dumps({'real_probe_summaries': summaries}))
        return
    if '--inspect-probe' in sys.argv:
        from verify_leny_v11_production import PRIVATE
        from app.services.leny_rag_synthesis import source_passages, numbers, units
        path = max(PRIVATE.glob('corrective-probe-*.json'), key=lambda p: p.stat().st_mtime)
        data = json.loads(path.read_text(encoding='utf-8'))
        blocks = json.loads(data['captured']['raw'])['blocks']
        details = []
        for block in blocks:
            if not re.fullmatch(r'S[1-5]', block.get('source','')):
                continue
            i = int(block['source'][1:])
            passages = dict(source_passages(data['sources'][i-1], i))
            support = ('\n'.join(passages.get(pid, '') for pid in block['support']) if isinstance(block['support'], list)
                       else passages.get(block['support'], block['support']))
            plain = re.sub(r'(?m)(?<!\w)\d+[.)]\s+', '', block['text'])
            details.append({'support_present': (all(pid in passages for pid in block['support']) if isinstance(block['support'], list)
                                               else support in data['sources'][i-1]['text']),
                'support_chars': len(support), 'unsupported_number_count': len(numbers(block['text'])-numbers(support)),
                'unsupported_unit_count': len(units(block['text'])-units(support)),
                'full_source_supports_quantities': numbers(block['text']) <= numbers(data['sources'][i-1]['text']) and units(block['text']) <= units(data['sources'][i-1]['text']),
                'enumeration_only': numbers(plain) <= numbers(support),
                'missing_markers': [marker for marker in ('no','sin','antes','después','solo','únicamente','excepto')
                    if re.search(r'\b'+marker+r'\b', support,re.I) and not re.search(r'\b'+marker+r'\b', block['text'],re.I)]})
        print(json.dumps({'validation_details': details}))
        return
    c = Settings(_env_file=BACKEND/'.env')
    engine = create_engine(c.effective_database_url)
    results = []
    probes = []
    with Session(engine) as db, db.begin():
        db.execute(text('SET TRANSACTION READ ONLY'))
        rows = db.execute(text("""SELECT a.id,a.reason,a.policy_version,a.status,a.content,a.created_at,
          u.content question,cv.account_id,cv.user_id FROM leny.mensajes a
          JOIN leny.mensajes u ON u.request_id=a.request_id AND u.role='user'
          JOIN leny.conversaciones cv ON cv.id=a.conversation_id
          WHERE a.role='assistant' AND a.policy_version='rag-v11-synthesis-v1'
          ORDER BY a.created_at DESC LIMIT 12""")).mappings().all()
        for row in rows:
            sources = [dict(r) for r in db.execute(text("""SELECT f.id fragment_id,f.text,f.ordinal,f.locator,
              d.title,v.document_id FROM leny.rag_fuentes_mensaje s
              JOIN leny.rag_fragmentos f ON f.id=s.fragment_id
              JOIN leny.rag_indexaciones i ON i.id=f.indexation_id
              JOIN leny.documento_versiones v ON v.id=i.version_id
              JOIN leny.documentos d ON d.id=v.document_id
              WHERE s.message_id=:id ORDER BY s.ordinal"""), {'id': row['id']}).mappings()]
            prompt = messages(row['question'], sources, 'sufficient')
            cost = sum(len(m['content'].encode())+32 for m in prompt)+len(json.dumps(SCHEMA).encode())
            results.append(dict(id=str(row['id']), reason=row['reason'], status=row['status'],
                date=str(row['created_at']), chars=len(row['content']),
                extractive='Extractos de las fuentes publicadas' in row['content'],
                synthesized='Según la documentación' in row['content'],
                source_count=len(sources), source_bytes=sum(len(r['text'].encode()) for r in sources),
                synthesis_cost_bytes=cost, conservative_budget=c.leny_num_ctx-c.leny_num_predict-256))
            if sources:
                probes.append((row['question'], sources))
        if rows:
            actor = LenyActor(rows[0]['account_id'], rows[0]['user_id'], 'read-only-review')
            reader(db, actor)
            role = db.execute(text(ELIGIBLE+"""SELECT f.ordinal,f.text,f.locator
              FROM eligible e JOIN leny.rag_fragmentos f ON f.indexation_id=e.indexation_id
              WHERE f.text ILIKE '%modista%' ORDER BY e.document_id,f.ordinal"""), parameters(c, actor)).mappings().all()
            print(json.dumps({'authorized_role_passages': [dict(ordinal=r['ordinal'],chars=len(r['text']),
                locator_keys=list(r['locator']),modista_mentions=r['text'].casefold().count('modista'),
                other_actor='asesor' in r['text'].casefold(),
                role_heading='modista' in str(r['locator'].get('heading','')).casefold()) for r in role]}))
            normalized_rows = db.execute(text(ELIGIBLE+"""SELECT f.ordinal,f.text,f.source_type FROM eligible e
                JOIN leny.rag_fragmentos f ON f.indexation_id=e.indexation_id"""), parameters(c, actor)).mappings().all()
            print(json.dumps({'normalized_role_matches': [dict(ordinal=r['ordinal'],source_type=r['source_type']) for r in normalized_rows
                if 'modista' in re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', r['text'].casefold()))]}))
            role_code = db.execute(text('SELECT r.codigo FROM cuentas c JOIN roles r ON r.id=c.rol_id WHERE c.id=:id'), {'id': actor.account_id}).scalar()
            if role_code == 'ADMIN':
                role_doc_text = db.execute(text("""SELECT f.text,f.source_type FROM leny.documentos d
                    JOIN leny.rag_fragmentos f ON f.indexation_id=d.published_indexation_id
                    WHERE d.title ILIKE '%modista%'""")).mappings().all()
                combined = unicodedata.normalize('NFKD', ' '.join(r['text'] for r in role_doc_text).casefold())
                print(json.dumps({'role_document_keywords': {word: len(re.findall(r'\b'+word+r'\b', combined))
                    for word in ('modista','costurera','asesor','asesora','responsabilidades','funciones','costura','puesto','inventario','confeccion')},
                    'role_document_types': sorted({r['source_type'] for r in role_doc_text})}))
                if '--inspect-original' in sys.argv:
                    import zipfile
                    from defusedxml import ElementTree as SafeET
                    from app.services.leny_document_storage import DocumentStorage, document_root
                    original = db.execute(text('SELECT v.storage_key FROM leny.documentos d JOIN leny.documento_versiones v ON v.id=d.published_version_id WHERE d.title ILIKE :title'), {'title': '%modista%'}).scalar_one()
                    storage = DocumentStorage(c)
                    storage.root = document_root(c)
                    with zipfile.ZipFile(storage.path(original)) as archive:
                        media_count = sum(name.startswith('word/media/') for name in archive.namelist())
                        inspected = []
                        for name in archive.namelist():
                            if name.startswith('word/') and name.endswith('.xml'):
                                xml = SafeET.fromstring(archive.read(name), forbid_dtd=True, forbid_entities=True, forbid_external=True)
                                value = ' '.join(node.text or '' for node in xml.iter() if node.tag.endswith('}t')).casefold()
                                inspected.append({'part': name if name in {'word/document.xml'} else 'other_word_part',
                                    'modista_mentions': value.count('modista'), 'function_mentions': value.count('funcion'),
                                    'text_chars': len(value)})
                    print(json.dumps({'original_docx_keyword_audit': inspected, 'embedded_media_count': media_count}))
                inventory = db.execute(text("""SELECT d.title,d.state,d.published_version_id,d.published_indexation_id,
                    (SELECT count(*) FROM leny.documento_versiones v WHERE v.document_id=d.id) versions,
                    (SELECT count(*) FROM leny.rag_fragmentos f JOIN leny.rag_indexaciones i ON i.id=f.indexation_id
                        JOIN leny.documento_versiones v ON v.id=i.version_id WHERE v.document_id=d.id) fragments,
                    (SELECT count(*) FROM leny.rag_fragmentos f JOIN leny.rag_indexaciones i ON i.id=f.indexation_id
                        JOIN leny.documento_versiones v ON v.id=i.version_id WHERE v.document_id=d.id AND f.text ILIKE '%modista%') role_fragments
                    FROM leny.documentos d ORDER BY d.created_at""")).mappings().all()
                print(json.dumps({'library_metadata': [dict(title_names_modista='modista' in r['title'].casefold(),
                    state=r['state'], published=bool(r['published_version_id'] and r['published_indexation_id']),
                    versions=r['versions'], fragments=r['fragments'], role_fragments=r['role_fragments']) for r in inventory]}))
    engine.dispose()
    print(json.dumps({'turns': results}))
    if ('--probe' in sys.argv or '--probe-largest' in sys.argv) and probes:
        # Replays only evidence already presented to the owner's conversation.
        # Does not mint credentials, impersonate an HTTP session or alter history.
        choose = max if '--probe-largest' in sys.argv else min
        question, sources = choose(probes, key=lambda pair: sum(len(r['text']) for r in pair[1]))
        asyncio.run(probe(c, question, sources))


async def probe(config, question, sources):
    from sqlalchemy.orm import sessionmaker
    from app.services.leny_coordination import PostgresCoordinator
    from app.services.leny_inference_state import InferenceState, ManagedProvider
    from app.services.leny_ollama import OllamaProvider
    from app.services.leny_rag_synthesis import synthesize
    from app.services.leny_rag_common import available_ram
    from verify_leny_v11_production import PRIVATE, prepare, write, Monitor
    if available_ram() < config.leny_rag_min_ram_bytes:
        raise RuntimeError('Insufficient available RAM')
    prepare()
    captured = {}
    class Provider(OllamaProvider):
        async def structured(self, context, schema):
            raw = await super().structured(context, schema)
            captured['raw'] = raw
            return raw
    engine = create_engine(config.effective_database_url)
    sessions = sessionmaker(engine)
    coordinator = PostgresCoordinator(config.effective_database_url)
    lease = coordinator.acquire()
    started = monotonic()
    provider = Provider(config)
    managed = ManagedProvider(provider, InferenceState(sessions), lease, uuid4(), lambda: max(.001, 120-(monotonic()-started)))
    result = {'scope': 'real_qwen_private_documentary_probe', 'human_review': None}
    try:
        with Monitor() as monitor:
            try:
                await provider.available()
                answer = await asyncio.wait_for(synthesize(managed, config, question, sources, 'partial'), 120)
                result.update(validated=True, answer=answer)
            except Exception as error:
                result.update(validated=False, failure=type(error).__name__,
                    reason=str(error) if isinstance(error, ValueError) else getattr(error,'code',None))
        result.update(seconds=round(monotonic()-started,3), metrics=provider.metrics,
            samples=monitor.samples, question=question, sources=json.loads(json.dumps(sources, default=str)), captured=captured)
        private_file = PRIVATE/('corrective-probe-'+uuid4().hex+'.json')
        write(private_file, result)
        print(json.dumps({key: result.get(key) for key in ('scope','validated','failure','reason','seconds','metrics')}))
    finally:
        lease.close()
        engine.dispose()


if __name__ == '__main__':
    main()
