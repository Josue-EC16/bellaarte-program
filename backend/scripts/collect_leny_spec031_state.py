"""Read-only effective configuration/usage; source checkpoints without secrets."""
from datetime import datetime,timezone
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from build_leny_spec031_review import roots,BACKEND
from run_leny_spec03_review import save

ROOT=BACKEND.parent


def main():
    sys.path.insert(0,str(BACKEND))
    from app.core.config import Settings
    from sqlalchemy import create_engine,text
    from app.services.leny_external_scope import approved_versions
    config=Settings(_env_file=BACKEND/'.env');current,review=roots()
    names=('leny_enabled','leny_llm_provider','leny_continuity_enabled','leny_quality_profile',
        'leny_spec03_evaluation_enabled','leny_gemini_enabled','leny_gemini_model','leny_gemini_thinking_level',
        'leny_gemini_input_token_budget','leny_gemini_output_tokens','leny_gemini_rpm','leny_gemini_tpm','leny_gemini_rpd',
        'leny_model','leny_num_ctx','leny_num_predict','leny_temperature','leny_rag_candidates','leny_rag_top_k','leny_rag_min_ram_bytes')
    state=dict(at=datetime.now(timezone.utc).isoformat(),configuration={name:getattr(config,name) for name in names},
        external_version_count=len(approved_versions(config)),model_usage=[],human_acceptance=None)
    engine=create_engine(config.effective_database_url,hide_parameters=True,connect_args={'options':'-c default_transaction_read_only=on'})
    with engine.connect() as db:
        state['revision']=db.scalar(text('SELECT version_num FROM alembic_version'))
        state['evaluation_google_http_today']=db.scalar(text("SELECT count(*) FROM leny.gemini_requests WHERE left(phase,5)='eval_' AND (created_at AT TIME ZONE 'America/Los_Angeles')::date=(clock_timestamp() AT TIME ZONE 'America/Los_Angeles')::date"))
        for path in sorted((review/'results').glob('031-*.json')):
            job=json.loads(path.read_text(encoding='utf-8'));ids=[case['request_id'] for case in job['cases']]
            rows=[dict(row) for row in db.execute(text('SELECT phase,status,error_code,count(*) calls,coalesce(sum(input_tokens),0) input_tokens,'
                'coalesce(sum(output_tokens),0) output_tokens,coalesce(sum(thinking_tokens),0) thinking_tokens,'
                'count(*) FILTER (WHERE input_tokens IS NULL) usage_unknown FROM leny.gemini_requests '
                'WHERE request_id=ANY(CAST(:ids AS uuid[])) GROUP BY phase,status,error_code ORDER BY phase,status,error_code'),{'ids':ids}).mappings()]
            state['model_usage'].append(dict(job=path.stem,google=rows))
    engine.dispose()
    source=current/('source-final-'+datetime.now().strftime('%H%M%S'));source.mkdir()
    hashes={};inverse=[]
    paths=set((BACKEND/'app/services').glob('leny*.py'))
    for directory in ('backend/app','backend/tests','backend/scripts','backend/alembic','frontend/src'):
        paths.update(path for path in (ROOT/directory).rglob('*')
            if path.suffix in {'.py','.ps1','.js','.jsx','.css','.json','.toml','.ini','.conf','.csv'}
            and '__pycache__' not in path.parts)
    paths.update((BACKEND/'tests').glob('test_leny*.py'))
    paths.update((BACKEND/'scripts').glob('*leny*spec03*'))
    paths.update((ROOT/'frontend/src/pages/leny').glob('*'))
    paths.update(ROOT/name for name in ('backend/app/core/config.py','backend/app/api/routers/leny.py','backend/app/schemas/leny.py','backend/.env.example'))
    for path in sorted(paths):
        if not path.is_file() or path.name=='.env' or '__pycache__' in path.parts:continue
        if any('holdout' in part.casefold() or 'reserved' in part.casefold() for part in path.parts):continue
        if 'tests' in path.parts and path.suffix=='.json' and path.name!='leny_spec03_development.json':continue
        relative=path.relative_to(ROOT).as_posix();data=path.read_bytes()
        target=source/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
        hashes[relative]=hashlib.sha256(data).hexdigest()
        previous=current/'before'/relative
        if previous.exists() and previous.read_bytes()!=data:
            inverse.extend(difflib.unified_diff(data.decode('utf-8-sig').splitlines(True),previous.read_text(encoding='utf-8-sig').splitlines(True),
                fromfile='a/'+relative,tofile='b/'+relative))
    (source/'inverse-backed-files.patch').write_text(''.join(inverse),encoding='utf-8')
    save(current/'candidate-snapshot.json',dict(path=str(source),inverse_coverage='Only initial backed files; other additive scripts/tests are listed separately; never reset HEAD.'))
    state['head']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();state['source_sha256']=hashes
    state['env_sha256']=hashlib.sha256((BACKEND/'.env').read_bytes()).hexdigest()
    save(ROOT/'documentacion/evidencias/leny_spec031_effective_state.json',state)
    print('SPEC03.1 state recorded; source files:',len(hashes),'Google evaluation HTTP:',state['evaluation_google_http_today'])


if __name__=='__main__':main()
