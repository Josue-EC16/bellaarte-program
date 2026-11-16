"""Content-free evidence and private, baseline-relative source rollback patch."""
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

BACKEND=Path(__file__).resolve().parents[1]
REPOSITORY=BACKEND.parent
sys.path.insert(0,str(BACKEND))


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    from app.core.config import Settings
    from sqlalchemy import create_engine,text
    import httpx
    root=Path(os.environ['LOCALAPPDATA'])/'BAB_VDOS/leny-gemini-spec02'
    backup=Path((root/'active-backup.txt').read_text().strip())
    baseline=json.loads((backup/'manifest.json').read_text(encoding='utf-8'))
    target=REPOSITORY/'documentacion/evidencias/leny_gemini_spec02_final.json'
    if target.exists():
        previous=json.loads(target.read_text(encoding='utf-8'))
        for name,expected in previous['source_snapshot'].items():
            path=REPOSITORY/name
            if path.resolve()==Path(__file__).resolve():continue
            if not path.is_file() or digest(path)!=expected:
                raise RuntimeError('Frozen source changed; preserve checkpoint and review a new one separately')
    patch=[];files={}
    for name,original_hash in baseline.items():
        original,current=backup/name,REPOSITORY/name
        if name=='backend\\.env':continue
        if not original.is_file() or digest(original)!=original_hash:
            raise RuntimeError('Source baseline verification failed')
        if current.is_file() and digest(current)!=original_hash:
            files[name.replace('\\','/')]=dict(before=original_hash,after=digest(current))
            before=original.read_text(encoding='utf-8-sig').splitlines(keepends=True)
            after=current.read_text(encoding='utf-8-sig').splitlines(keepends=True)
            posix=name.replace('\\','/')
            patch.extend(difflib.unified_diff(before,after,fromfile='a/'+posix,tofile='b/'+posix))
    patch_path=root/'spec02-source.patch'
    patch_path.write_text(''.join(patch),encoding='utf-8')
    check=subprocess.run(['git','apply','--reverse','--check','--ignore-space-change',str(patch_path)],cwd=REPOSITORY,capture_output=True)
    config=Settings(_env_file=BACKEND/'.env')
    engine=create_engine(config.effective_database_url,hide_parameters=True)
    with engine.connect() as db:
        revision=db.scalar(text('SELECT version_num FROM alembic_version'))
        inference=db.scalar(text('SELECT state FROM leny.inferencia_estado WHERE id=1'))
        ledger=[dict(row) for row in db.execute(text('SELECT phase,status,error_code,count(*) attempts,'
            'count(input_tokens) calls_with_input_tokens,count(output_tokens) calls_with_output_tokens '
            'FROM leny.gemini_requests GROUP BY phase,status,error_code ORDER BY phase,status,error_code')).mappings()]
    engine.dispose()
    cases=[]
    for path in sorted((root/'review/results').glob('spec02-*.json')):
        for row in json.loads(path.read_text(encoding='utf-8'))['cases']:
            final=row.get('final',{})
            cases.append(dict(job=path.stem,case=row['id'],http_status=row.get('http_status'),
                termination=row.get('termination'),seconds=row.get('seconds'),outcome=final.get('outcome'),
                scope=final.get('response_scope'),provider=final.get('provider'),
                source_count=len(row.get('sources',[])),source_http_status=[s['http_status'] for s in row.get('sources',[])],
                error_codes=[event['code'] for event in row.get('events',[]) if event.get('type')=='error']))
    report=dict(captured_at=datetime.now(timezone.utc).isoformat(),revision=revision,
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPOSITORY,text=True).strip(),
        original_env_unchanged=digest(BACKEND/'.env')==baseline['backend\\.env'],
        health_http_status=httpx.get('http://127.0.0.1:8000/health',trust_env=False,timeout=5).status_code,
        unauthenticated_leny_http_status=httpx.get('http://127.0.0.1:8000/api/v1/leny/status',trust_env=False,timeout=5).status_code,
        inference_state=inference,operational_provider='ollama',gemini_operationally_enabled=False,
        activation_note='Gemini remains disabled after real generation failures; not accepted',
        configuration={name:getattr(config,name) for name in ('leny_llm_provider','leny_gemini_enabled',
            'leny_gemini_model','leny_gemini_thinking_level','leny_gemini_input_token_budget','leny_gemini_output_tokens',
            'leny_gemini_rpm','leny_gemini_tpm','leny_gemini_rpd','leny_model','leny_num_ctx','leny_num_predict',
            'leny_temperature','leny_keep_alive','leny_rag_profile','leny_rag_ranking','leny_rag_response_mode','leny_rag_neighbor_chunks')},
        gemini_key_present=bool(config.gemini_api_key and config.gemini_api_key.get_secret_value().strip()),
        baseline_relative_files=files,source_reverse_patch_check=check.returncode==0,
        google_ledger=ledger,authenticated_api_cases=cases,human_acceptance=None)
    # Include the real working tree, not only HEAD; never .env or corpus text.
    paths=list((BACKEND/'app/services').glob('leny*.py'))+[
        BACKEND/'app/core/config.py',BACKEND/'app/models/leny.py',BACKEND/'app/schemas/leny.py',
        BACKEND/'app/api/routers/leny.py',BACKEND/'alembic/versions/20261105_0024_leny_conversation_providers.py']
    paths+=list((REPOSITORY/'frontend/src/pages/leny').glob('*'))
    paths+=list((BACKEND/'tests').glob('test_leny_gemini*.py'))
    paths+=list((BACKEND/'scripts').glob('*leny_gemini*'))
    paths.append(BACKEND/'scripts/restart_leny_review_backend.py')
    report['source_snapshot']={str(p.relative_to(REPOSITORY)).replace('\\','/'):digest(p)
                               for p in paths if p.is_file()}
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(health=report['health_http_status'],inference=inference,reverse_patch_valid=check.returncode==0,
                         env_unchanged=report['original_env_unchanged'],api_cases=len(cases))))


if __name__=='__main__':main()
