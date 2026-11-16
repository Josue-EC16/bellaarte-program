"""Gated, bounded real SDK diagnostics. No RAG, private text or secret output.

A/B use the official SDK directly, sharing only LENY's durable quota and lease.
C exercises the adapter only after the saved A and B both passed in this run.
Every execution is explicit; failed steps cannot unlock a later step.
"""
import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import sys
from time import monotonic
from datetime import datetime, timezone
from urllib.parse import urlsplit

BACKEND=Path(__file__).resolve().parents[1]
REPOSITORY=BACKEND.parent
sys.path.insert(0,str(BACKEND))
SCHEMA={'type':'object','properties':{'ok':{'type':'boolean'}},'required':['ok'],'additionalProperties':False}


def prerequisite(directory, step):
    for previous in {'A':(), 'B':('A',), 'C':('A','B')}[step]:
        path=directory/(previous+'.json')
        if not path.is_file() or json.loads(path.read_text(encoding='utf-8')).get('passed') is not True:
            raise RuntimeError('Previous diagnostic step did not pass; no external call permitted')


def metrics(result):
    usage=getattr(result,'usage_metadata',None)
    return {name:getattr(usage,name) for name in
        ('prompt_token_count','candidates_token_count','thoughts_token_count')
        if type(getattr(usage,name,None)) is int}


def completed_text(result):
    candidates=result.candidates or []
    if len(candidates)!=1:return '',None
    candidate=candidates[0]
    reason=getattr(candidate.finish_reason,'value',candidate.finish_reason)
    parts=getattr(candidate.content,'parts',None) or []
    return ''.join(part.text or '' for part in parts if not part.thought).strip(),reason


async def run(args):
    from google import genai
    from google.genai import types, errors
    import httpx
    from sqlalchemy import create_engine,text
    from sqlalchemy.orm import sessionmaker
    from app.core.config import Settings
    from app.services.leny_coordination import PostgresCoordinator
    from app.services.leny_document_storage import protect_directory
    from app.services.leny_gemini_usage import GeminiUsage
    from app.services.leny_llm_contracts import LenyError

    directory=REPOSITORY/'documentacion/evidencias'/args.run
    directory.mkdir(exist_ok=True)
    destination=directory/(args.step+'.json')
    if destination.exists():raise RuntimeError('Preserve previous step evidence; no automatic replay')
    prerequisite(directory,args.step)
    config=Settings(_env_file=BACKEND/'.env')
    if config.leny_gemini_enabled:raise RuntimeError('User-facing Gemini must remain disabled during diagnostics')
    if config.leny_gemini_model not in {'gemini-3.8-flash','gemini-3.5-flash-lite','gemini-3.1-flash-lite'}:
        raise RuntimeError('Unexpected model')
    private=Path(os.environ['LOCALAPPDATA'])/'BAB_VDOS/leny-gemini-spec021'/args.run
    private.mkdir(parents=True,exist_ok=True);protect_directory(private)
    original_env_hash=hashlib.sha256((BACKEND/'.env').read_bytes()).hexdigest()
    # Back up only source/configuration definitions, never the private .env.
    for name in ('app/services/leny_gemini.py','app/services/leny_gemini_usage.py',
                 'app/core/config.py','tests/test_leny_gemini_provider.py'):
        target=private/name
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes((BACKEND/name).read_bytes())
    engine=create_engine(config.effective_database_url,hide_parameters=True)
    coordinator=PostgresCoordinator(config.effective_database_url)
    lease=coordinator.acquire()
    usage=GeminiUsage(sessionmaker(engine),config)
    observations=[]
    async def request_hook(request):
        # Query, headers and body are deliberately inaccessible to the report.
        observations.append(dict(method=request.method,host=request.url.host,path=request.url.path))
    async def response_hook(response):
        if observations:observations[-1]['http_status']=response.status_code
    options=types.HttpOptions(api_version='v1beta',timeout=60000,
        retry_options=types.HttpRetryOptions(attempts=1),client_args={'trust_env':False},
        async_client_args={'trust_env':False,'event_hooks':{'request':[request_hook],'response':[response_hook]}})
    client=genai.Client(api_key=config.gemini_api_key.get_secret_value(),vertexai=False,enterprise=False,http_options=options)
    effective=client._api_client._http_options
    if urlsplit(effective.base_url).hostname!='generativelanguage.googleapis.com':
        await client.aio.aclose();client.close();lease.close();engine.dispose();coordinator.engine.dispose()
        raise RuntimeError('Unexpected SDK endpoint; no call sent')
    report=dict(step=args.step,run=args.run,started_at=datetime.now(timezone.utc).isoformat(),
        python=sys.version.split()[0],sdk=importlib.metadata.version('google-genai'),
        model=config.leny_gemini_model,endpoint='https://generativelanguage.googleapis.com',api_version=effective.api_version,
        transport='aiohttp' if client._api_client._use_aiohttp() else 'httpx',sdk_attempts=1,
        application_retries=0 if args.step in ('A','B') else 1,timeout_seconds=60,
        target=dict(thinking='medium',input_budget=32678,output_tokens=8192),
        diagnostic=dict(thinking='omitted_model_default' if args.step in ('A','B') else 'medium',
            output_tokens=1024 if args.step in ('A','B') else 8192,structured=args.step!='A'),
        declared_quota=dict(rpm=config.leny_gemini_rpm,tpm=config.leny_gemini_tpm,rpd=config.leny_gemini_rpd),
        authenticated_project_verified=False,effective_account_quota_verified=False,
        documents_sent=False,passed=False,operations=[],http=observations)
    start=monotonic();adapter=None

    async def direct(operation,phase,reserved_tokens):
        identity=usage.reserve(phase,reserved_tokens);error_code=None;values={};began=monotonic()
        row=dict(operation=phase)
        report['operations'].append(row)
        try:
            result=await asyncio.wait_for(operation(),65)
            row.update(success=True,tokens=metrics(result));values=row['tokens']
            return result
        except errors.APIError as error:
            error_code='GOOGLE_HTTP_'+str(error.code)
            row.update(success=False,http_status=error.code,exception_type=type(error).__name__)
            status=getattr(error,'status',None)
            if isinstance(status,str) and re.fullmatch(r'[A-Z_]{1,64}',status):row['provider_status']=status
            # Allowlist error categories only, not raw error text or details.
            message=getattr(error,'message','') or ''
            row['overload_wording']=bool(re.search(r'overload|high demand|temporar',message,re.I))
            row['deadline_wording']=bool(re.search(r'deadline|timed? ?out',message,re.I))
            raise
        except (asyncio.TimeoutError,httpx.TimeoutException) as error:
            error_code='LOCAL_TIMEOUT';row.update(success=False,exception_type=type(error).__name__,local_timeout=True)
            raise
        except BaseException as error:
            error_code='LOCAL_'+type(error).__name__;row.update(success=False,exception_type=type(error).__name__)
            raise
        finally:
            row['seconds']=round(monotonic()-began,3)
            usage.finish(identity,error=error_code,metrics=dict(prompt_eval_count=values.get('prompt_token_count'),
                eval_count=values.get('candidates_token_count'),thinking_tokens=values.get('thoughts_token_count')))

    try:
        if args.step=='A':
            model=await direct(lambda:client.aio.models.get(model=config.leny_gemini_model),'diag_model',0)
            report['model_metadata']={field:getattr(model,field) for field in
                ('name','version','input_token_limit','output_token_limit','supported_actions')
                if getattr(model,field,None) is not None}
        if args.step in ('A','B'):
            parameters=dict(max_output_tokens=1024,automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
            if args.step=='B':parameters.update(response_mime_type='application/json',response_json_schema=SCHEMA)
            result=await direct(lambda:client.aio.models.generate_content(model=config.leny_gemini_model,
                contents='Responde únicamente OK.' if args.step=='A' else 'Devuelve un JSON con ok igual a true.',
                config=types.GenerateContentConfig(**parameters)),'diag_'+args.step.lower(),1024)
            value,reason=completed_text(result)
            report.update(finish_reason=reason,output_characters=len(value),tokens=metrics(result),
                          passed=bool(value) and reason=='STOP')
            if args.step=='B':report['passed']=report['passed'] and json.loads(value)=={'ok':True}
        else:
            from app.services.leny_gemini import GeminiProvider
            c=config.model_copy(update={'leny_gemini_enabled':True,'leny_gemini_free_tier_confirmed':True})
            def factory(**kwargs):
                kwargs['http_options'].async_client_args['event_hooks']={'request':[request_hook],'response':[response_hook]}
                return genai.Client(**kwargs)
            adapter=GeminiProvider(c,usage=usage,client_factory=factory,authorize=lambda:asyncio.to_thread(lease.check))
            value=await adapter.structured([{'role':'user','content':'Devuelve un JSON con ok igual a true.'}],SCHEMA)
            report.update(passed=json.loads(value)=={'ok':True},metrics=adapter.network_metrics,effective_model=adapter.effective_model)
    except (errors.APIError,asyncio.TimeoutError,httpx.HTTPError,LenyError) as error:
        report['passed']=False
        report['exception_type']=type(error).__name__
        report['error_code']=getattr(error,'code','LOCAL_'+type(error).__name__)
    except Exception as error:
        report['passed']=False
        report['error_code']='LOCAL_'+type(error).__name__
    finally:
        if adapter is not None:await adapter.aclose()
        await client.aio.aclose();client.close();lease.close();engine.dispose();coordinator.engine.dispose()
        report['seconds']=round(monotonic()-start,3)
        report['original_env_unchanged']=hashlib.sha256((BACKEND/'.env').read_bytes()).hexdigest()==original_env_hash
        # Credentials, HTTP error bodies, request payloads and generated text never enter the report.
        destination.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(step=args.step,passed=report['passed'],seconds=report['seconds'],error=report.get('error_code'),
                         calls=len(observations),evidence=str(destination.relative_to(REPOSITORY)))))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);parser.add_argument('--step',choices=('A','B','C'),required=True)
    args=parser.parse_args()
    if not re.fullmatch(r'leny_gemini_spec021_[a-zA-Z0-9_-]{1,48}',args.run):raise RuntimeError('Invalid diagnostic run name')
    asyncio.run(run(args))
