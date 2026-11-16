"""Read-only baseline and prior-use corpus inventory. Never prints private text."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import json
import os
import sys

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))


def main():
    from sqlalchemy import create_engine,text
    from app.core.config import Settings
    from app.services.leny_document_storage import protect_directory
    config=Settings(_env_file=BACKEND/'.env')
    base=Path(os.environ['LOCALAPPDATA'])/'BAB_VDOS'
    root=Path((base/'leny-spec03/active.txt').read_text(encoding='utf-8'))
    review=base/'leny-gemini-spec02/review/results'
    requests=set()
    for path in review.glob('resume31-*.json'):
        for row in json.loads(path.read_text(encoding='utf-8')).get('cases',[]):
            if row.get('request_id'):requests.add(row['request_id'])
    if not requests:raise RuntimeError('Prior authorized review provenance is required')
    engine=create_engine(config.effective_database_url,hide_parameters=True,
        connect_args={'options':'-c default_transaction_read_only=on'})
    with engine.connect() as db:
        versions=[dict(row) for row in db.execute(text('''SELECT DISTINCT
          v.document_id::text document_id,v.id::text version_id,i.id::text indexation_id,v.sha256
          FROM leny.rag_fuentes_mensaje s JOIN leny.rag_fragmentos f ON f.id=s.fragment_id
          JOIN leny.rag_indexaciones i ON i.id=f.indexation_id
          JOIN leny.documento_versiones v ON v.id=i.version_id
          JOIN leny.mensajes m ON m.id=s.message_id
          WHERE m.request_id=ANY(CAST(:requests AS uuid[]))
          ORDER BY document_id,version_id,indexation_id'''),{'requests':list(requests)}).mappings()]
        revision=db.scalar(text('SELECT version_num FROM alembic_version'))
        published=db.scalar(text('SELECT count(*) FROM leny.documentos WHERE published_indexation_id IS NOT NULL AND deleted_at IS NULL'))
        quota_used=db.scalar(text("SELECT count(*) FROM leny.gemini_requests WHERE (created_at AT TIME ZONE 'America/Los_Angeles')::date=(clock_timestamp() AT TIME ZONE 'America/Los_Angeles')::date"))
    engine.dispose()
    if not versions:raise RuntimeError('No prior-use versions could be proven')
    grants=dict(format_version=1,authority='owner-approved prior review versions only',created_at=datetime.now(timezone.utc).isoformat(),versions=versions)
    path=root/'external-corpus.json'
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8'))['versions']!=versions:
            raise RuntimeError('Frozen authorized corpus changed; no automatic expansion')
    else:path.write_text(json.dumps(grants,indent=2),encoding='utf-8')
    protect_directory(root)
    names=('leny_llm_provider','leny_gemini_model','leny_gemini_enabled','leny_gemini_thinking_level',
        'leny_gemini_input_token_budget','leny_gemini_output_tokens','leny_gemini_rpm','leny_gemini_tpm','leny_gemini_rpd',
        'leny_model','leny_num_ctx','leny_num_predict','leny_temperature','leny_rag_profile','leny_rag_response_mode',
        'leny_rag_top_k','leny_rag_candidates','leny_rag_neighbor_chunks','leny_rag_section_context','leny_rag_source_coverage','leny_rag_followup_context')
    report=dict(frozen_at=datetime.now(timezone.utc).isoformat(),revision=revision,published_document_count=published,
        prior_use_authorized_version_count=len(versions),prior_review_requests=len(requests),
        corpus_manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),google_technical_attempts_today=quota_used,
        configuration={name:getattr(config,name) for name in names},
        new_inferences=0,human_semantic_acceptance=None,reserved_holdout_opened=False)
    target=BACKEND.parent/'documentacion/evidencias/leny_spec03_baseline_inventory.json'
    if target.exists():raise RuntimeError('Preserve baseline evidence; do not overwrite')
    target.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(dict(revision=revision,approved_versions=len(versions),published=published,
                         prior_requests=len(requests),technical_attempts_today=quota_used)))


if __name__=='__main__':main()
