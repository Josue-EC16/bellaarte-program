"""Normal authenticated API evaluation; no app startup, SQL or Google client.

Jobs contain questions only. Every admitted attempt is checkpointed BEFORE
POST and is never replayed after interruption. Textual evidence stays private.
"""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from uuid import UUID, uuid4

import httpx

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
API = 'http://127.0.0.1:8000/api/v1'
NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$')
CORPUS = BACKEND/'tests/fixtures/leny_spec03_development.json'


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    with temporary.open('w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def root_path():
    base = Path(os.environ['LOCALAPPDATA'])/'BAB_VDOS/leny-spec03'
    active = (base/'active.txt').read_text(encoding='utf-8-sig').strip()
    checkpoint = base/active if NAME.fullmatch(active) else Path(active)
    checkpoint = checkpoint.resolve()
    if checkpoint.parent != base.resolve() or not NAME.fullmatch(checkpoint.name):
        raise ValueError('Invalid private checkpoint root')
    return checkpoint/'review'


def prepare(root):
    from app.services.leny_document_storage import _check_path, protect_directory
    _check_path(root)
    root.mkdir(parents=True, exist_ok=True)
    protect_directory(root)
    for name in ('jobs', 'results', 'resume'):
        (root/name).mkdir(exist_ok=True)


def validate_job(job, name):
    if not NAME.fullmatch(name) or job.get('id') != name:
        raise ValueError('Invalid job identity')
    if set(job)-{'id','provider','quality_profile','omit_profile','cases'}:
        raise ValueError('Unsupported job options')
    if job.get('provider', 'ollama') not in ('ollama','gemini'):
        raise ValueError('Invalid provider')
    if job.get('quality_profile','baseline') not in ('baseline','spec03'):
        raise ValueError('Invalid profile')
    if type(job.get('omit_profile',False)) is not bool or (job.get('omit_profile') and job.get('quality_profile','baseline') != 'baseline'):
        raise ValueError('Only baseline may omit profile')
    cases = job.get('cases')
    if not isinstance(cases,list) or not 1 <= len(cases) <= 28:
        raise ValueError('Expected 1 to 28 cases')
    seen = set()
    for case in cases:
        if set(case)-{'id','question','conversation','depends_on'}:
            raise ValueError('Unsupported case options')
        if not NAME.fullmatch(case.get('id','')) or case['id'] in seen:
            raise ValueError('Invalid case identity')
        if not NAME.fullmatch(case.get('conversation',case['id'])):
            raise ValueError('Invalid conversation group')
        if not isinstance(case.get('question'),str) or not 1 <= len(case['question']) <= 10000:
            raise ValueError('Invalid question')
        if case.get('depends_on') and case['depends_on'] not in seen:
            raise ValueError('Dependency must precede case')
        seen.add(case['id'])
    return job


def fingerprint(job):
    return hashlib.sha256(json.dumps(job,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def safe_code(response):
    try:
        detail = response.json().get('detail',{})
        value = detail.get('code') if isinstance(detail,dict) else None
        return value if isinstance(value,str) and re.fullmatch(r'[A-Z][A-Z0-9_]{0,79}',value) else 'HTTP_ERROR'
    except (ValueError,AttributeError):
        return 'HTTP_ERROR'


def event_code(value):
    return value if isinstance(value,str) and re.fullmatch(r'[A-Z][A-Z0-9_]{0,79}',value) else 'STREAM_ERROR'


def retry_delay(value):
    try:
        return min(60,max(13,int(value)))
    except (TypeError,ValueError):
        return 13


def refresh_auth(client):
    me = client.get('/auth/me')
    now=time.monotonic()
    last=getattr(client,'_leny_last_refresh',None)
    # run_job can outlive one access token. Renew normally between cases, not
    # only after the entire batch returns to the watch loop. Tokens stay memory-only.
    if me.status_code == 401 or (type(last) in (int,float) and now-last>180):
        response = client.post('/auth/refresh')
        response.raise_for_status()
        client.headers['Authorization'] = 'Bearer '+response.json()['access_token']
        me = client.get('/auth/me')
    me.raise_for_status()
    if me.status_code==200 and (type(last) not in (int,float) or now-last>180):client._leny_last_refresh=now


def reconcile(client, row):
    """An interrupted checkpoint can only be read back, never resent."""
    conversation = row.get('conversation_id')
    if conversation:
        response = client.get('/leny/conversations/'+str(UUID(conversation)))
        row['reconcile_http_status'] = response.status_code
        if response.status_code == 200:
            detail = response.json()
            messages = detail.get('items',[])
            assistant = next((m for m in messages if m.get('role')=='assistant' and m.get('request_id')==row['request_id']),None)
            if assistant:
                row['reconciled_message'] = assistant
                row['response'] = assistant.get('content','')
                row['history_status'] = assistant.get('status')
    row['termination'] = 'interrupted_checkpoint_not_replayed'
    row['consumed'] = True


def run_job(client, root, job):
    path = root/'results'/(job['id']+'.json')
    token_path = root/'resume'/(job['id']+'.json')
    token = token_path.read_text(encoding='utf-8') if token_path.exists() else ''
    result = json.loads(path.read_text(encoding='utf-8')) if path.exists() else dict(
        job=job['id'],job_sha256=fingerprint(job),provider=job.get('provider','ollama'),
        quality_profile=job.get('quality_profile','baseline'),cases=[],conversations={},human_review=None)
    if result['job_sha256'] != fingerprint(job):
        raise ValueError('Job changed after checkpoint')
    if result.get('state')=='complete' or (result.get('state')=='paused_quota' and result.get('resume_token','')==token):
        return
    result['resume_token'] = token
    result['state'] = 'running'
    by_id = {c['id']:c for c in result['cases']}
    for row in result['cases']:
        if row.get('termination')=='attempt_started':
            refresh_auth(client)
            reconcile(client,row)
            save(path,result)
    for case in job['cases']:
        if case['id'] in by_id:
            continue
        refresh_auth(client)
        started = time.monotonic()
        row = dict(id=case['id'],question=case['question'],request_id=str(uuid4()),
                   termination='attempt_started',events=[],sources=[],consumed=True)
        result['cases'].append(row)
        by_id[case['id']] = row
        dependency = by_id.get(case.get('depends_on'))
        if dependency and (dependency.get('termination')!='done' or dependency.get('final',{}).get('status')!='completed'):
            row['termination']='dependency_unavailable'
            save(path,result)
            continue
        group = case.get('conversation',case['id'])
        save(path,result)  # Durable before conversation creation or chat POST.
        try:
            if group not in result['conversations']:
                payload={'provider':job.get('provider','ollama')}
                if not job.get('omit_profile',False):payload['quality_profile']=job.get('quality_profile','baseline')
                response=client.post('/leny/conversations',json=payload)
                row['creation_http_status']=response.status_code
                row['retry_after']=response.headers.get('Retry-After')
                if response.status_code!=201:
                    row['http_status']=response.status_code;row['error_code']=safe_code(response)
                    row['termination']='http_error'
                else:
                    result['conversations'][group]=str(UUID(response.json()['id']))
            if row['termination']=='attempt_started':
                row['conversation_id']=result['conversations'][group]
                save(path,result)
                payload=dict(conversation_id=row['conversation_id'],request_id=row['request_id'],message=case['question'])
                with client.stream('POST','/leny/chat',json=payload) as response:
                    row['http_status']=response.status_code
                    row['retry_after']=response.headers.get('Retry-After')
                    if response.status_code!=200:
                        response.read();row['error_code']=safe_code(response);row['termination']='http_error'
                    else:
                        total_bytes=0
                        for line in response.iter_lines():
                            if line:
                                size=len(line.encode());total_bytes+=size
                                if size>65536 or total_bytes>1024*1024:raise ValueError('Oversized NDJSON stream')
                                event=json.loads(line)
                                if not isinstance(event,dict) or event.get('type') not in ('start','delta','done','error','progress'):
                                    raise ValueError('Invalid NDJSON event')
                                row['events'].append(event)
                                if len(row['events'])>5000:raise ValueError('Excessive events')
                                if event.get('type')=='delta' and 'first_delta_seconds' not in row:
                                    row['first_delta_seconds']=round(time.monotonic()-started,3)
                        terminals=[e for e in row['events'] if e.get('type') in ('done','error')]
                        row['termination']=terminals[-1]['type'] if len(terminals)==1 else 'invalid_terminal_count'
                        row['response']=''.join(e.get('text','') for e in row['events'] if e.get('type')=='delta')
                        if terminals:
                            if terminals[-1]['type']=='done':row['final']=terminals[-1]
                            else:row['error_code']=event_code(terminals[-1].get('code'))
                save(path,result)  # Stream result survives errors opening sources/history.
                for source in row.get('final',{}).get('sources',[]):
                    response=client.get('/leny/rag/sources/'+str(UUID(source['source_id'])))
                    row['sources'].append(dict(http_status=response.status_code,
                        detail=response.json() if response.status_code==200 else None))
                response=client.get('/leny/conversations/'+row['conversation_id'])
                row['history_http_status']=response.status_code
                if response.status_code==200:
                    detail=response.json();row['persisted_conversation']=detail.get('conversation',{})
                    assistant=next((m for m in detail.get('items',[]) if m.get('role')=='assistant' and m.get('request_id')==row['request_id']),None)
                    row['history_matches_response']=bool(assistant and assistant.get('content')==row.get('response',''))
                    row['history_status']=assistant.get('status') if assistant else None
        except (httpx.HTTPError,ValueError,KeyError,TypeError) as error:
            row['check_error']=type(error).__name__
            if row['termination']=='attempt_started':row['termination']=type(error).__name__
        row['seconds']=round(time.monotonic()-started,3)
        quota=row.get('http_status')==429 or row.get('error_code')=='LENY_EVALUATION_QUOTA'
        if quota:
            result['state']='paused_quota'
            result['pause']=dict(case_id=row['id'],request_id=row['request_id'],code=row.get('error_code'),
                retry_after=row.get('retry_after'),resume='Explicit --resume JOB continues with NEXT case; never repeats consumed attempt')
        save(path,result)
        print(json.dumps(dict(job=job['id'],case=case['id'],termination=row['termination'],
            error_code=row.get('error_code'),seconds=row['seconds'])),flush=True)
        if quota:
            print('Trabajo pausado por cuota. Reanudar tras la ventana/cuota indicada por el backend; no se espera hasta otro día.',flush=True)
            return
        if case is not job['cases'][-1]:time.sleep(retry_delay(row.get('retry_after')))
    result['state']='complete'
    save(path,result)


def watch(root):
    username=input('Usuario ERP: ');password=getpass.getpass('Clave ERP (oculta): ')
    with httpx.Client(base_url=API,trust_env=False,follow_redirects=False,timeout=httpx.Timeout(330,connect=5)) as client:
        response=client.post('/auth/login',json=dict(username=username,password=password));password=None
        if response.status_code!=200:raise RuntimeError('Login rejected')
        client.headers['Authorization']='Bearer '+response.json()['access_token']
        refresh_auth(client)
        save(root/'session.json',dict(authenticated=True,started=time.time()))
        print('Sesión normal activa. Esperando trabajos locales.',flush=True)
        try:
            deadline=time.monotonic()+7200
            last_refresh=time.monotonic()
            while time.monotonic()<deadline and not (root/'stop').exists():
                if time.monotonic()-last_refresh>180:
                    refresh_auth(client);last_refresh=time.monotonic()
                for path in sorted((root/'jobs').glob('*.json')):
                    job=validate_job(json.loads(path.read_text(encoding='utf-8')),path.stem)
                    run_job(client,root,job)
                time.sleep(1)
        finally:
            save(root/'session.json',dict(authenticated=False,finished=time.time()))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--watch',action='store_true')
    parser.add_argument('--resume',metavar='JOB')
    parser.add_argument('--validate-corpus',action='store_true')
    args=parser.parse_args()
    if args.validate_corpus:
        data=json.loads(CORPUS.read_text(encoding='utf-8'))
        assert data['split']=='development' and len(data['cases'])==20
        print('20 synthetic development cases; human gold provisional; no requests performed')
        return
    root=root_path();prepare(root)
    if args.resume:
        if not NAME.fullmatch(args.resume):raise ValueError('Invalid job name')
        save(root/'resume'/(args.resume+'.json'),dict(token=str(uuid4()),created=time.time()))
        print('Resume marker prepared; consumed requests will not be resent')
    if args.watch:watch(root)


if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:print('Evaluación interrumpida localmente; intentos conservados.')
    except Exception as error:
        if isinstance(error,httpx.HTTPStatusError):
            print('Evaluación detenida: HTTP',error.response.status_code,safe_code(error.response),'sin mostrar credenciales ni respuestas privadas.')
        else:print('Evaluación detenida:',type(error).__name__,'sin mostrar credenciales ni respuestas privadas.')
        raise SystemExit(1)
