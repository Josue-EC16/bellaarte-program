"""Read-only technical state and aggregate usage, with no prompts or secrets."""
import json
from pathlib import Path
import sys
from run_leny_spec03_review import root_path,save,BACKEND

sys.path.insert(0,str(BACKEND))


def main():
    from app.core.config import Settings
    from sqlalchemy import create_engine,text
    from app.services.leny_external_scope import approved_versions
    config=Settings(_env_file=BACKEND/'.env')
    names=('leny_enabled','leny_llm_provider','leny_quality_profile','leny_spec03_evaluation_enabled',
        'leny_spec03_evaluation_daily_calls','leny_model','leny_num_ctx','leny_num_predict','leny_temperature',
        'leny_gemini_enabled','leny_gemini_free_tier_confirmed','leny_gemini_model',
        'leny_gemini_thinking_level','leny_gemini_input_token_budget','leny_gemini_output_tokens',
        'leny_gemini_rpm','leny_gemini_tpm','leny_gemini_rpd','leny_rag_top_k','leny_rag_candidates',
        'leny_rag_neighbor_chunks','leny_rag_section_context','leny_rag_source_coverage','leny_rag_min_ram_bytes')
    result=dict(configuration={name:getattr(config,name) for name in names},
        approved_external_versions=len(approved_versions(config)),credentials_reported=False,phases=[])
    engine=create_engine(config.effective_database_url,hide_parameters=True,
        connect_args={'options':'-c default_transaction_read_only=on'})
    try:
        with engine.connect() as db:
            result['revision']=db.scalar(text('SELECT version_num FROM alembic_version'))
            result['evaluation_http_today']=db.scalar(text("SELECT count(*) FROM leny.gemini_requests WHERE left(phase,5)='eval_' AND (created_at AT TIME ZONE 'America/Los_Angeles')::date=(clock_timestamp() AT TIME ZONE 'America/Los_Angeles')::date"))
            for path in sorted((root_path()/'results').glob('*.json')):
                job=json.loads(path.read_text(encoding='utf-8'))
                ids=[row['request_id'] for row in job['cases'] if row.get('request_id')]
                rows=[dict(row) for row in db.execute(text("SELECT phase,status,count(*) calls,"
                    "coalesce(sum(input_tokens),0) input_tokens,coalesce(sum(output_tokens),0) output_tokens,"
                    "coalesce(sum(thinking_tokens),0) thinking_tokens,count(*) FILTER (WHERE input_tokens IS NULL) calls_missing_input_usage "
                    "FROM leny.gemini_requests WHERE request_id=ANY(CAST(:ids AS uuid[])) GROUP BY phase,status ORDER BY phase,status"),{'ids':ids}).mappings()]
                result['phases'].append(dict(job=path.stem,http_usage=rows,local_tokens_available=False))
    finally:engine.dispose()
    save(BACKEND.parent/'documentacion/evidencias/leny_spec03_effective_state.json',result)
    print('Effective state recorded; approved versions:',result['approved_external_versions'],
        'evaluation HTTP:',result['evaluation_http_today'],'default:',config.leny_llm_provider)


if __name__=='__main__':main()
