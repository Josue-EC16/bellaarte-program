"""Authorized production review. No migrations, publication changes or JWT minting.

Private responses stay in a protected directory outside the web root. Authentication
uses only the credential explicitly supplied locally for this review, via normal
HTTP login. Never prints credentials, tokens, document titles or response text.
"""
from __future__ import annotations

import argparse
import asyncio
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from uuid import uuid4
import xml.etree.ElementTree as ET

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)
PRIVATE = Path(os.environ['LOCALAPPDATA'])/'BAB_VDOS'/'leny-v11-review'
BASE_URL = 'http://127.0.0.1:8000/api/v1'
QUESTIONS = [
    '¿Cómo se confecciona un vestido?',
    '¿Cuáles son las responsabilidades de la modista?',
    'Actualmente quiero hacer un manual, pero no sé de dónde comenzar',
    'Quiero un ejemplo de cómo iniciar un manual',
    'Documento EJEMPLO DE COMO INICIAR EL MANUAL, dime cómo puedo iniciar un manual',
    'Explícame cómo elaborar un fuste de can-can según el manual',
]


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def settings():
    from app.core.config import Settings
    return Settings(_env_file=BACKEND/'.env')


def prepare():
    from app.services.leny_document_storage import _check_path, protect_directory
    _check_path(PRIVATE)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    protect_directory(PRIVATE)


def snapshot():
    from sqlalchemy import create_engine, text
    c = settings()
    engine = create_engine(c.effective_database_url)
    result = {}
    try:
        with engine.connect() as db, db.begin():
            db.execute(text('SET TRANSACTION READ ONLY'))
            db.execute(text("SET LOCAL statement_timeout='15s'"))
            if db.execute(text('SELECT current_database()')).scalar() != 'bellaarte_db':
                raise RuntimeError('Unexpected production database')
            result['revision'] = db.execute(text('SELECT version_num FROM alembic_version')).scalar()
            for table in ('leny.documentos','leny.documento_versiones','leny.documento_roles_lectura',
                          'leny.carpeta_roles_lectura','leny.rag_indexaciones',
                          'leny.rag_fragmentos','leny.rag_embeddings','roles'):
                # Fixed allowlist; only hashes/counts leave PostgreSQL.
                if not db.execute(text('SELECT to_regclass(:name)'), {'name': table}).scalar():
                    continue
                result[table] = dict(db.execute(text('SELECT count(*) count, md5(coalesce(string_agg(h,\'\' ORDER BY h),\'\')) fingerprint '
                    'FROM (SELECT md5(row_to_json(t)::text) h FROM '+table+' t) hashes')).mappings().one())
            result['inference_state'] = db.execute(text('SELECT state FROM leny.inferencia_estado WHERE id=1')).scalar()
            result['jobs_active'] = db.execute(text("SELECT count(*) FROM leny.rag_trabajos WHERE status IN ('queued','running')")).scalar()
    finally:
        engine.dispose()
    return result


def activate():
    from app.services.leny_coordination import PostgresCoordinator
    import leny_rag_pilot_profile as profile
    prepare()
    c = settings()
    if c.leny_rag_profile != 'rag4_v1' or c.leny_num_ctx != 4096 or c.leny_num_predict != 768:
        raise RuntimeError('Unexpected resources/profile')
    path = PRIVATE/'activation.json'
    if path.exists():
        raise RuntimeError('Preserve previous activation package')
    before = snapshot()
    if before['revision'] != '20261020_0021':
        raise RuntimeError('Unexpected database revision; no migration is authorized')
    if before['inference_state'] != 'idle' or before['jobs_active']:
        raise RuntimeError('Inference or worker is busy; no configuration changed')
    lease = PostgresCoordinator(c.effective_database_url).acquire()
    try:
        old = (BACKEND/'.env').read_bytes()
        profile.CHANGES = {'LENY_RAG_RESPONSE_MODE': 'controlled-synthesis-v1'}
        replacement = profile.render_environment(old)
        (PRIVATE/'env.before').write_bytes(old)
        (PRIVATE/'env.candidate').write_bytes(replacement)
        new = type(c)(_env_file=PRIVATE/'env.candidate')
        if any(c.model_dump()[key] != new.model_dump()[key] for key in c.model_dump() if key != 'leny_rag_response_mode'):
            raise RuntimeError('Unrelated effective setting changed')
        if new.leny_rag_response_mode != 'controlled-synthesis-v1':
            raise RuntimeError('Process overrides response mode')
        profile.atomic_replace(BACKEND/'.env', profile.sha(old), replacement)
        write(path, {'time': datetime.now(timezone.utc).isoformat(), 'before': before,
                     'env_before_sha256': profile.sha(old), 'env_after_sha256': profile.sha(replacement)})
    finally:
        lease.close()
    # The verified existing Uvicorn supervisor watches Python files, not .env.
    # Change only mtime; source bytes and git diff stay identical.
    (BACKEND/'main.py').touch()
    print(json.dumps({'configuration_changed': True, 'response_mode': new.leny_rag_response_mode,
                      'reload_requested': True, 'database_migrated': False}))


def rollback():
    import leny_rag_pilot_profile as profile
    from app.services.leny_coordination import PostgresCoordinator
    manifest = json.loads((PRIVATE/'activation.json').read_text(encoding='utf-8'))
    original = (PRIVATE/'env.before').read_bytes()
    if profile.sha(original) != manifest['env_before_sha256']:
        raise RuntimeError('Rollback copy integrity mismatch')
    lease = PostgresCoordinator(settings().effective_database_url).acquire()
    try:
        profile.atomic_replace(BACKEND/'.env', manifest['env_after_sha256'], original)
    finally:
        lease.close()
    (BACKEND/'main.py').touch()
    print(json.dumps({'restored_previous_configuration': True, 'reload_requested': True}))


def credential():
    """Read only the user-created, DPAPI-protected credential for this task."""
    from ctypes import wintypes
    tree = ET.parse(PRIVATE/'credential.xml')
    username = next(e.text for e in tree.iter() if e.attrib.get('N') == 'UserName')
    encrypted = next(e.text for e in tree.iter() if e.attrib.get('N') == 'Password')
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_char))]
    raw = bytes.fromhex(encrypted)
    buffer = ctypes.create_string_buffer(raw)
    source = Blob(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    output = Blob()
    api = ctypes.WinDLL('crypt32', use_last_error=True)
    if not api.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(output)):
        raise RuntimeError('Local review credential could not be decrypted')
    try:
        password = ctypes.string_at(output.data, output.size).decode('utf-16-le')
    finally:
        ctypes.windll.kernel32.LocalFree(output.data)
    return username, password


class Monitor:
    def __init__(self):
        self.samples = []
        self.stop = threading.Event()
    def run(self):
        from app.services.leny_rag_common import available_ram
        from ctypes import wintypes
        import httpx
        previous_cpu = None
        while not self.stop.is_set():
            sample = {'time': time.time(), 'ram_available_bytes': available_ram()}
            idle, kernel, user = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
            if ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
                values = tuple((v.dwHighDateTime << 32)+v.dwLowDateTime for v in (idle, kernel, user))
                if previous_cpu:
                    total = values[1]-previous_cpu[1]+values[2]-previous_cpu[2]
                    if total:
                        sample['system_cpu_percent'] = round(100*(1-(values[0]-previous_cpu[0])/total), 2)
                previous_cpu = values
            try:
                status = httpx.get('http://127.0.0.1:11434/api/ps', trust_env=False, timeout=2)
                status.raise_for_status()
                sample['resident_models'] = [{key: row[key] for key in ('name','size','size_vram','context_length') if key in row}
                    for row in status.json().get('models', [])]
            except (httpx.HTTPError, ValueError, TypeError):
                sample['ollama_status_unavailable'] = True
            try:
                output = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,utilization.gpu', '--format=csv,noheader,nounits'],
                    capture_output=True, text=True, timeout=3, creationflags=subprocess.CREATE_NO_WINDOW)
                if output.returncode == 0:
                    memory, utilization = output.stdout.splitlines()[0].split(',')
                    sample.update(gpu_memory_mib=int(memory), gpu_utilization_percent=int(utilization))
            except (OSError, ValueError, subprocess.TimeoutExpired):
                pass
            self.samples.append(sample)
            self.stop.wait(1)
    def __enter__(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        return self
    def __exit__(self, *_):
        self.stop.set()
        self.thread.join(5)


def review(phase):
    import httpx
    prepare()
    target = PRIVATE/(phase+'.json')
    if target.exists():
        raise RuntimeError('Preserve previous review output; choose a fresh phase')
    username, password = credential()
    report = {'phase': phase, 'human_review': None, 'cases': [], 'before': snapshot()}
    with httpx.Client(base_url=BASE_URL, trust_env=False, timeout=150) as client:
        response = client.post('/auth/login', json={'username': username, 'password': password})
        password = None
        response.raise_for_status()
        client.headers['Authorization'] = 'Bearer '+response.json()['access_token']
        config = client.get('/leny/admin/config')
        config.raise_for_status()
        report['configuration'] = config.json()
        expected = 'document-excerpts-v2' if phase == 'baseline' else 'controlled-synthesis-v1'
        if config.json().get('rag_response_mode') != expected:
            raise RuntimeError('Live API response mode differs from review phase')
        for index, question in enumerate(QUESTIONS, 1):
            conversation = client.post('/leny/conversations')
            conversation.raise_for_status()
            cid = conversation.json()['id']
            started = time.monotonic()
            with Monitor() as monitor:
                result = client.post('/leny/chat', json={'conversation_id': cid, 'request_id': str(uuid4()), 'message': question})
            elapsed = round(time.monotonic()-started, 3)
            events = [json.loads(line) for line in result.text.splitlines()] if result.status_code == 200 else []
            final = events[-1] if events else {}
            report['cases'].append({'case': index, 'question': question, 'conversation_id': cid,
                'http_status': result.status_code, 'elapsed_seconds': elapsed,
                'events': events, 'resource_samples': monitor.samples, 'human_review': None})
            write(target, report)
            print(json.dumps({'phase': phase, 'case': index, 'http': result.status_code,
                              'result': final.get('type'), 'outcome': final.get('outcome'), 'code': final.get('code'),
                              'seconds': elapsed, 'sources': len(final.get('sources', [])),
                              'ram_min_bytes': min((s['ram_available_bytes'] for s in monitor.samples), default=None)}), flush=True)
            # Respect the ordinary quota, never bypass or repeat consumed requests.
            if index < len(QUESTIONS):
                time.sleep(max(0, 13-elapsed))
        report['after'] = snapshot()
        write(target, report)
    print(json.dumps({'private_review': str(target), 'human_review_complete': False}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'snapshot', 'activate', 'rollback', 'review', 'monitor'])
    parser.add_argument('--phase', choices=['baseline', 'candidate'], default='candidate')
    parser.add_argument('--seconds', type=int, default=900)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare()
        print(json.dumps({'credential_path': str(PRIVATE/'credential.xml')}))
    elif args.command == 'snapshot':
        print(json.dumps(snapshot()))
    elif args.command == 'activate':
        activate()
    elif args.command == 'rollback':
        rollback()
    elif args.command == 'monitor':
        if not 1 <= args.seconds <= 1800:
            raise ValueError('Invalid bounded monitoring window')
        prepare()
        with Monitor() as monitor:
            for _ in range(args.seconds):
                time.sleep(1)
                write(PRIVATE/'manual-resource-samples.json', {'scope': 'whole-system samples during manual review', 'samples': monitor.samples})
    elif args.command == 'review':
        review(args.phase)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # No HTTP response bodies, credentials, private paths or SQL parameters.
        print(json.dumps({'failed': type(error).__name__, 'code': getattr(error, 'code', None)}))
        raise SystemExit(1)
