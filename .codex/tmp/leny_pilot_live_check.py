"""Read-only deployment fingerprints. Never imports the app/router or contents."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.request
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

ROOT=Path(__file__).resolve().parents[2]
os.chdir(ROOT/'backend'); sys.path.insert(0,str(ROOT/'backend'))
from app.core.config import settings
from scripts.prepare_leny_rag_pilot_backup import fingerprints
from scripts.leny_rag_pilot_profile import validate_recovery_proof
from app.services.leny_document_storage import DocumentStorage

stage=sys.argv[1]
if stage not in ('before','after'):raise ValueError('Unknown deployment stage')
base=ROOT/'documentacion/evidencias'
output=base/('leny_rag04_pilot_activation_'+stage+'.json')
if output.exists():raise ValueError('Existing evidence must be preserved')
private=Path(os.environ['LOCALAPPDATA'])/'BAB_VDOS/leny-pilot/leny-rag-v1-piloto-20261021-r3'
proof=json.loads((private/'recovery-proof.json').read_text('utf-8'))
if stage=='before':
    validate_recovery_proof(private,proof,DocumentStorage(settings).root/'backups',ROOT)
url=make_url(settings.effective_database_url)
assert url.host in ('localhost','127.0.0.1') and url.port==5432 and url.database=='bellaarte_db'
engine=create_engine(url,poolclass=NullPool,hide_parameters=True,
    connect_args={'options':'-c default_transaction_read_only=on -c statement_timeout=30000'})
previous=None if stage=='before' else json.loads((base/'leny_rag04_pilot_activation_before.json').read_text('utf-8'))
record=dict(stage=stage,database='bellaarte_db',port=5432,read_only=True,
    created_utc=datetime.now(timezone.utc).isoformat(),env_sha256=hashlib.sha256((ROOT/'backend/.env').read_bytes()).hexdigest(),
    file_settings={k:getattr(settings,k) for k in ('leny_rag_profile','leny_rag_evidence_mode','leny_rag_ranking',
        'leny_rag_adaptive_token_probe','leny_temperature','leny_rag_chat_enabled','leny_num_ctx','leny_num_predict','leny_keep_alive')})
try:
    with engine.connect() as db:
        record['revision']=db.scalar(text('SELECT version_num FROM alembic_version'))
        record['library_fingerprints']=fingerprints(db)
        record['library_matches_verified_backup']=record['library_fingerprints']==proof['data_fingerprints']
        record['role_codes']=list(db.scalars(text('SELECT codigo FROM roles ORDER BY codigo')))
        record['inference_state']=db.scalar(text('SELECT state FROM leny.inferencia_estado WHERE id=1'))
        record['active_generations']=db.scalar(text("SELECT count(*) FROM leny.mensajes WHERE status='generating'"))
        record['queued_running_jobs']=db.scalar(text("SELECT count(*) FROM leny.rag_trabajos WHERE status IN ('queued','running')"))
        record['public_fingerprints']={}
        for table in db.scalars(text("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename NOT IN ('auditoria_sistema','cuentas') ORDER BY tablename")):
            quoted='"'+table.replace('"','""')+'"'
            row=db.execute(text('SELECT count(*) AS count,md5(coalesce(string_agg(h,\'\' ORDER BY h),\'\')) AS fingerprint '
                'FROM (SELECT md5(to_jsonb(t)::text) h FROM public.'+quoted+' t) s')).mappings().one()
            record['public_fingerprints'][table]=dict(row)
        cutoff=previous['history_cutoff_utc'] if previous else db.scalar(text('SELECT clock_timestamp()')).isoformat()
        record['history_cutoff_utc']=cutoff
        record['preexisting_history']={}
        for table in ('conversaciones','mensajes'):
            record['preexisting_history'][table]=dict(db.execute(text(
                'SELECT count(*) AS count,md5(coalesce(string_agg(h,\'\' ORDER BY h),\'\')) AS fingerprint '
                'FROM (SELECT md5(to_jsonb(t)::text) h FROM leny.'+table+' t WHERE created_at<CAST(:cutoff AS timestamptz)) s'),
                {'cutoff':cutoff}).mappings().one())
        if previous:
            record.update(public_data_unchanged=record['public_fingerprints']==previous['public_fingerprints'],
                preexisting_history_unchanged=record['preexisting_history']==previous['preexisting_history'],
                library_unchanged=record['library_fingerprints']==previous['library_fingerprints'])
            record['new_message_metadata']=[dict(row) for row in db.execute(text(
                'SELECT role,status,model,category,reason,policy_version,octet_length(content) content_bytes '
                'FROM leny.mensajes WHERE created_at>=CAST(:cutoff AS timestamptz) ORDER BY created_at,sequence'),
                {'cutoff':cutoff}).mappings()]
            record['new_conversations']=db.scalar(text('SELECT count(*) FROM leny.conversaciones WHERE created_at>=CAST(:cutoff AS timestamptz)'),{'cutoff':cutoff})
            key=0x4C454E590001
            record['global_generation_lock_holders']=db.scalar(text(
                "SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND classid=:high AND objid=:low AND granted"),
                {'high':key>>32,'low':key&0xffffffff})
            actor_row=db.execute(text('SELECT account_id,user_id FROM leny.conversaciones '
                'WHERE created_at>=CAST(:cutoff AS timestamptz) ORDER BY created_at DESC LIMIT 1'),{'cutoff':cutoff}).one_or_none()
            if actor_row:
                from app.services.leny_store import LenyActor
                from app.services.leny_rag_retrieval import ELIGIBLE,parameters
                actor=LenyActor(actor_row.account_id,actor_row.user_id,'deployment-readonly-check')
                eligible=db.execute(text(ELIGIBLE+'SELECT count(DISTINCT e.document_id) documents,count(*) fragments '
                    'FROM eligible e JOIN leny.rag_fragmentos f ON f.indexation_id=e.indexation_id'),parameters(settings,actor)).mappings().one()
                record['published_sql_eligible_for_verified_session_actor']=dict(eligible)
                record['eligible_check_scope']='counts_only_no_embeddings_or_document_content_returned'
finally:engine.dispose()
with urllib.request.urlopen('http://127.0.0.1:11434/api/tags',timeout=5) as response:
    tags=json.load(response)['models']
record['model_digests']={x['name']:x['digest'] for x in tags if x['name'] in ('qwen3.5:4b-q4_K_M','qwen3-embedding:0.6b')}
for name,path in (('conversations','/api/v1/leny/conversations'),('config','/api/v1/leny/admin/config'),
                  ('source','/api/v1/leny/rag/sources/00000000-0000-0000-0000-000000000001')):
    try:
        with urllib.request.urlopen('http://127.0.0.1:8000'+path,timeout=5) as response:
            status=response.status
    except urllib.error.HTTPError as error:
        status=error.code
    record['unauthenticated_'+name+'_http_status']=status
if stage=='after':
    with urllib.request.urlopen('http://127.0.0.1:11434/api/ps',timeout=5) as response:
        record['ollama_models_loaded_after_check']=len(json.load(response)['models'])
if stage=='before' and (not record['library_matches_verified_backup'] or record['inference_state']!='idle'
                       or record['active_generations'] or record['queued_running_jobs']):
    raise RuntimeError('Read-only preflight requires reconciliation before activation')
output.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:record[k] for k in ('stage','revision','library_matches_verified_backup','inference_state',
    'active_generations','queued_running_jobs','file_settings')},indent=2))
if stage=='after':
    print(json.dumps({k:record[k] for k in ('public_data_unchanged','preexisting_history_unchanged','library_unchanged',
        'new_conversations','new_message_metadata','global_generation_lock_holders',
        'published_sql_eligible_for_verified_session_actor','unauthenticated_source_http_status')},indent=2))
