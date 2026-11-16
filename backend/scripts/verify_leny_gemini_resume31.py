"""Read-only final review: aggregate metrics, no private response text output."""
import hashlib
import json
import os
from pathlib import Path
import sys
from datetime import datetime,timezone

BACKEND=Path(__file__).resolve().parents[1]
REPOSITORY=BACKEND.parent
sys.path.insert(0,str(BACKEND))


def main():
    import httpx
    from sqlalchemy import create_engine,text
    from app.core.config import Settings
    config=Settings(_env_file=BACKEND/'.env')
    private=Path(os.environ['LOCALAPPDATA'])/'BAB_VDOS/leny-gemini-spec02/review'
    rollback=Path((private.parents[1]/'leny-gemini-resume31/active.txt').read_text(encoding='utf-8'))
    before=json.loads((rollback/'manifest.json').read_text(encoding='utf-8'))
    engine=create_engine(config.effective_database_url,hide_parameters=True)
    report=dict(captured_at=datetime.now(timezone.utc).isoformat(),cases=[],human_review=None,
        configuration={name:getattr(config,name) for name in ('leny_gemini_model','leny_gemini_enabled',
        'leny_gemini_free_tier_confirmed','leny_llm_provider','leny_gemini_rpm','leny_gemini_tpm','leny_gemini_rpd',
        'leny_gemini_thinking_level','leny_gemini_input_token_budget','leny_gemini_output_tokens',
        'leny_model','leny_num_ctx','leny_num_predict','leny_temperature','leny_rag_profile','leny_rag_response_mode')})
    with engine.connect() as db:
        for path in sorted((private/'results').glob('resume31-*.json')):
            group={}
            data=json.loads(path.read_text(encoding='utf-8'))
            if 'checks' in data:
                report.setdefault('transport_checks',[]).extend(data['checks'])
                continue
            for row in data['cases']:
                final=row.get('final',{})
                item=dict(job=path.stem,case=row['id'],seconds=row['seconds'],http_status=row.get('http_status'),
                    terminal=row['termination'],outcome=final.get('outcome'),reason=final.get('reason_code'),
                    scope=final.get('response_scope'),provider=final.get('provider'),model=final.get('model'),
                    source_count=len(row.get('sources',[])),source_access=[x['http_status'] for x in row.get('sources',[])],
                    response_characters=len(row.get('response','')),errors=[e['code'] for e in row.get('events',[]) if e.get('type')=='error'])
                conv=db.execute(text('SELECT llm_provider,llm_model FROM leny.conversaciones WHERE id=:id'),{'id':row['conversation_id']}).one()
                item['persisted_provider']=conv.llm_provider;item['persisted_model']=conv.llm_model
                messages=db.execute(text('SELECT role,status,content,model FROM leny.mensajes WHERE request_id=:id ORDER BY sequence'),{'id':row['request_id']}).all()
                if messages:
                    item['user_message_preserved']=messages[0].role=='user' and messages[0].content==row['question']
                    assistant=next((m for m in messages if m.role=='assistant'),None)
                    item['assistant_status']=assistant.status if assistant else None
                    item['persisted_answer_matches_ndjson']=bool(assistant and assistant.content==row.get('response',''))
                attempts=db.execute(text('SELECT phase,status,input_tokens,output_tokens,thinking_tokens FROM leny.gemini_requests WHERE request_id=:id'),{'id':row['request_id']}).all()
                item['google_calls']=len(attempts)
                item['tokens_reported']={name:sum(getattr(a,name) or 0 for a in attempts) for name in ('input_tokens','output_tokens','thinking_tokens')}
                item['calls_without_complete_token_counts']=sum(a.input_tokens is None or a.output_tokens is None for a in attempts)
                item['same_conversation_as_previous']=bool(group.get('last')==row['conversation_id'])
                group['last']=row['conversation_id']
                report['cases'].append(item)
        report['database_revision']=db.scalar(text('SELECT version_num FROM alembic_version'))
        report['inference_state']=db.scalar(text('SELECT state FROM leny.inferencia_estado WHERE id=1'))
        report['technical_consumption_preserved']=db.scalar(text('SELECT count(*) FROM leny.gemini_requests'))
    engine.dispose()
    report['health_http_status']=httpx.get('http://127.0.0.1:8000/health',trust_env=False,timeout=5).status_code
    report['unauthenticated_leny_http_status']=httpx.get('http://127.0.0.1:8000/api/v1/leny/status',trust_env=False,timeout=5).status_code
    paths=[REPOSITORY/name for name in before['files']]
    paths += [Path(__file__),BACKEND/'tests/test_leny_gemini_diagnostics.py']
    report['source_sha256']={str(p.relative_to(REPOSITORY)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    target=REPOSITORY/'documentacion/evidencias/leny_gemini_resume31_final.json'
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(cases=len(report['cases']),health=report['health_http_status'],inference=report['inference_state'])))


if __name__=='__main__':main()
