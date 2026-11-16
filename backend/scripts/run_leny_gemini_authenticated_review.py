"""Normal ERP login and complete NDJSON review, credentials only in memory."""
import getpass
import json
import os
from pathlib import Path
import time

import httpx
import run_leny_authenticated_review as review

review.ROOT=Path(os.environ['LOCALAPPDATA'])/'BAB_VDOS/leny-gemini-spec02/review'


class ReviewClient(httpx.Client):
    provider='ollama'
    def post(self,url,*args,**kwargs):
        if url=='/leny/conversations':
            kwargs['json']={'provider':self.provider}
        return super().post(url,*args,**kwargs)


def transport_checks(client, job):
    """Normal API only: persisted identity, history, immutability and disconnect.

    Fixed requests with synthetic text. No executable instructions in jobs.
    """
    from uuid import uuid4
    results=[]
    client.provider='gemini'
    status=client.get('/leny/status');status.raise_for_status()
    results.append(dict(check='configured_provider_status',passed=any(p['provider']=='gemini' and p['available']
        and p['model']=='gemini-3.1-flash-lite' for p in status.json()['providers'])))
    result=client.post('/leny/conversations',json={});result.raise_for_status();conv=result.json()['id']
    results.append(dict(check='created_provider',passed=result.json()['llm_provider']=='gemini'
        and result.json()['llm_model']=='gemini-3.1-flash-lite'))
    wrong=client.post('/leny/chat',json=dict(conversation_id=conv,request_id=str(uuid4()),
        message='Explica un concepto empresarial.',provider='ollama'))
    results.append(dict(check='message_provider_override_rejected',passed=wrong.status_code==422))
    rid=str(uuid4());started=time.monotonic();events=[]
    with client.stream('POST','/leny/chat',json=dict(conversation_id=conv,request_id=rid,
        message='Explica un procedimiento empresarial ficticio con sus etapas y condiciones.')) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                event=json.loads(line);events.append(event['type'])
                if event['type']=='start':
                    time.sleep(4)
                    break
    # Closing after start exercises real ASGI disconnect while provider work
    # is pending. Never send another turn until the durable message is terminal.
    deadline=time.monotonic()+320;terminal=None;detail=None
    while time.monotonic()<deadline:
        detail=client.get('/leny/conversations/'+conv);detail.raise_for_status()
        messages=detail.json()['items']
        assistant=next((m for m in messages if m['role']=='assistant' and m['request_id']==rid),None)
        if assistant and assistant['status']!='generating':terminal=assistant['status'];break
        time.sleep(1)
    results.append(dict(check='cancelled_turn_terminal',passed=terminal=='interrupted',status=terminal,
                        seconds=round(time.monotonic()-started,3),event_types=events))
    results.append(dict(check='provider_persisted_after_disconnect',passed=bool(detail and
        detail.json()['conversation']['llm_provider']=='gemini' and detail.json()['conversation']['llm_model']=='gemini-3.1-flash-lite')))
    if terminal is None:
        review.save(review.ROOT/'results'/(job['id']+'.json'),dict(checks=results));return
    # Read existing authorized results through the normal API, without copying
    # response text into this control report.
    previous=review.ROOT/'results/resume31-E-rag.json'
    if previous.exists():
        cases=json.loads(previous.read_text(encoding='utf-8'))['cases']
        for row in cases:
            if row.get('final',{}).get('outcome')!='answered':continue
            response=client.get('/leny/conversations/'+row['conversation_id']);response.raise_for_status()
            history=response.json();assistant=next((m for m in history['items'] if m['role']=='assistant'
                and m['request_id']==row['request_id']),None)
            results.append(dict(check='history_'+row['id'],passed=bool(assistant and
                assistant['content']==row.get('response','') and history['conversation']['llm_provider']=='gemini'),
                source_count=len(assistant.get('sources',[])) if assistant else 0))
    client.provider='ollama'
    result=client.post('/leny/conversations',json={});result.raise_for_status()
    results.append(dict(check='qwen_default_creation_retained',passed=result.json()['llm_provider']=='ollama'))
    review.save(review.ROOT/'results'/(job['id']+'.json'),dict(job=job['id'],checks=results,private_text_saved=False))
    print(json.dumps(dict(job=job['id'],checks=len(results),passed=sum(x['passed'] for x in results))),flush=True)


def main():
    review.prepare()
    username=input('Usuario ERP: ');password=getpass.getpass('Clave ERP (oculta): ')
    with ReviewClient(base_url=review.API,trust_env=False,timeout=httpx.Timeout(330,connect=5)) as client:
        response=client.post('/auth/login',json=dict(username=username,password=password));password=None
        if response.status_code!=200:
            print('Login rechazado; no se muestra su contenido.');return
        client.headers['Authorization']='Bearer '+response.json()['access_token']
        client.get('/auth/me').raise_for_status()
        review.save(review.ROOT/'session.json',dict(authenticated=True,started=time.time()))
        print('Sesion normal activa. Esperando trabajos locales.',flush=True)
        end=time.monotonic()+7200;refresh=time.monotonic()
        while time.monotonic()<end and not (review.ROOT/'stop').exists():
            if time.monotonic()-refresh>180:
                response=client.post('/auth/refresh');response.raise_for_status()
                client.headers['Authorization']='Bearer '+response.json()['access_token'];refresh=time.monotonic()
            for path in sorted((review.ROOT/'jobs').glob('*.json')):
                job=json.loads(path.read_text(encoding='utf-8'))
                if not (review.ROOT/'results'/path.name).exists():
                    if job['id']!=path.stem or not path.stem.replace('-','').isalnum():raise RuntimeError('Invalid job name')
                    client.provider=job.get('provider','ollama')
                    if client.provider not in ('ollama','gemini'):raise RuntimeError('Invalid provider')
                    if job.get('kind')=='transport_checks':transport_checks(client,job)
                    else:review.review(client,job)
            time.sleep(1)
        review.save(review.ROOT/'session.json',dict(authenticated=False,finished=time.time()))


if __name__=='__main__':
    try:main()
    except Exception as error:print('Revision detenida:',type(error).__name__,'sin mostrar credenciales.')
