"""Explicit owner-authorized Google probe: synthetic data only, safe report."""
import asyncio
import argparse
import json
from pathlib import Path
import sys
from time import monotonic

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))


async def run(name, skip_model, plain, model=None):
    from app.core.config import Settings
    from app.services.leny_gemini import GeminiProvider
    from app.services.leny_gemini_usage import GeminiUsage
    from app.services.leny_llm_contracts import LenyError
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    c=Settings(_env_file=BACKEND/'.env').model_copy(update={'leny_gemini_enabled':True,'leny_gemini_free_tier_confirmed':True})
    if model is not None:
        if model not in {'gemini-3.8-flash','gemini-3.5-flash-lite','gemini-3.1-flash-lite'}:
            raise RuntimeError('Unauthorized diagnostic model')
        c=c.model_copy(update={'leny_gemini_model':model})
    engine=create_engine(c.effective_database_url,hide_parameters=True)
    from app.services.leny_coordination import PostgresCoordinator
    coordinator=PostgresCoordinator(c.effective_database_url)
    lease=coordinator.acquire()
    provider=GeminiProvider(c,usage=GeminiUsage(sessionmaker(engine),c))
    report=dict(model=c.leny_gemini_model,thinking='medium',input_budget=c.leny_gemini_input_token_budget,
                output_limit=c.leny_gemini_output_tokens,free_tier_confirmation='owner',documents_sent=False,checks=[])
    start=monotonic()
    try:
        if not skip_model:
            await provider.probe()
            report['checks'].append(dict(check='model_access',passed=True))
        if plain:
            raw=''.join([part async for part in provider.stream([{'role':'user','content':'Responde únicamente OK.'}])])
            assert raw.strip()
            report['checks'].append(dict(check='synthetic_plain_generation',passed=True))
        else:
            raw=await provider.structured([{'role':'system','content':'Responde solo JSON. Es un ejemplo ficticio sin datos empresariales.'},
            {'role':'user','content':'Devuelve un consejo breve para organizar un taller ficticio.'}],
            {'type':'object','properties':{'advice':{'type':'string'}},'required':['advice'],'additionalProperties':False})
            assert isinstance(json.loads(raw).get('advice'),str)
            report['checks'].append(dict(check='synthetic_structured_generation',passed=True))
        report['metrics']=provider.network_metrics
        report['effective_model']=provider.effective_model
    except LenyError as error:
        report['error_code']=error.code
        report['http_status']=error.status
        report['provider_http_status']=getattr(error,'provider_http_status',None)
    except Exception as error:
        report['error_code']='LOCAL_'+type(error).__name__
    finally:
        await provider.aclose();engine.dispose();lease.close();coordinator.engine.dispose()
    report['seconds']=round(monotonic()-start,3)
    destination=BACKEND.parent/('documentacion/evidencias/leny_gemini_spec02_'+name+'.json')
    if destination.exists():
        raise RuntimeError('Preserve previous probe evidence')
    destination.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='real_probe');parser.add_argument('--skip-model',action='store_true');parser.add_argument('--plain',action='store_true');parser.add_argument('--model',choices=('gemini-3.8-flash','gemini-3.5-flash-lite','gemini-3.1-flash-lite'));args=parser.parse_args()
    if not args.name.replace('_','').isalnum():raise RuntimeError('Invalid evidence name')
    if (BACKEND.parent/('documentacion/evidencias/leny_gemini_spec02_'+args.name+'.json')).exists():raise RuntimeError('Evidence already exists')
    asyncio.run(run(args.name,args.skip_model,args.plain,args.model))
