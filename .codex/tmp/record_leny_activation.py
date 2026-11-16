"""Finalize public deployment evidence; no application/DB imports or mutations."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
folder=ROOT/'documentacion/evidencias'
def read(name):return json.loads((folder/name).read_text('utf-8'))
before=read('leny_rag04_pilot_activation_before.json')
after=read('leny_rag04_pilot_activation_after.json')
event=read('leny_rag04_pilot_activation_event.json')
freeze=read('leny_rag04_pilot_freeze_r3.json')
expected=dict(leny_rag_profile='rag4_v1',leny_rag_evidence_mode='adaptive',leny_rag_ranking='hybrid',
              leny_rag_adaptive_token_probe=True,leny_temperature=0.0)
assert all(after['file_settings'][k]==value for k,value in expected.items())
assert all(after[k] for k in ('public_data_unchanged','library_unchanged','preexisting_history_unchanged'))
assert after['revision']=='20261020_0021' and after['inference_state']=='idle'
assert after['active_generations']==0 and after['global_generation_lock_holders']==0
assert event['configuration_dacl_preserved']
assert hashlib.sha256((ROOT/'backend/.env').read_bytes()).hexdigest()==event['env_after_sha256']
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in freeze['files'].items())
assistant=[r for r in after['new_message_metadata'] if r['role']=='assistant']
assert len(assistant)==1 and assistant[0]['status']=='completed' and assistant[0]['policy_version']=='rag4-v4'
assert assistant[0]['reason']=='identity_or_greeting' and after['new_conversations']==1
artifacts=['leny_rag04_pilot_activation_'+s+'.json' for s in ('before','after','event')]
record=dict(schema_version='leny-supervised-pilot-activation-v1',
    created_utc=datetime.now(timezone.utc).isoformat(),pilot_id='leny-rag-v1-piloto-20261021-r3',
    state='ACTIVE_SUPERVISED_PILOT_FORMAL_ACCEPTANCE_PENDING',owner_confirmation_received=True,
    database='bellaarte_db',port=5432,revision=after['revision'],
    effective_runtime_settings_verified_in_existing_authenticated_admin_ui=expected,
    runtime_policy_verified_in_completed_message='rag4-v4',
    runtime_model_verified_in_completed_message=assistant[0]['model'],
    coverage_verifier_enabled=False,source_freeze_still_matches=True,
    source_freeze_manifest_sha256=freeze['manifest_sha256'],
    env_before_sha256=event['env_before_sha256'],env_after_sha256=event['env_after_sha256'],
    dacl_preserved=True,final_replacement_full_security_descriptor_preserved=True,
    backend_reloaded=True,backend_child_pid_before=4284,backend_child_pid_after=16448,
    frontend_restarted=False,ollama_restarted=False,worker_started=False,
    frontend='http://localhost:5173/app/leny',backend='http://127.0.0.1:8000',
    authenticated_admin_session_works=True,chat_from_erp_verified=True,
    browser_check=dict(input='Hola',content_classification='non_documentary_technical_greeting',
        generating_stop_state_observed=True,completed_reply_visible=True,history_reloaded_and_same_two_messages_visible=True,
        private_document_content_read=False,commercial_operations_executed=False),
    new_test_conversations=1,new_test_messages=2,
    operational_message_metadata=assistant[0],
    public_tables_compared=len(after['public_fingerprints']),
    public_data_unchanged=True,public_comparison_exclusions=['auditoria_sistema','cuentas'],
    comparison_exclusion_reason='audit and normal authentication activity are outside the commercial data comparison',
    documents_acl_publications_versions_vectors_unchanged=True,preexisting_history_unchanged=True,
    role_codes_unchanged=before['role_codes']==after['role_codes'],
    model_digests=after['model_digests'],
    inference_state_after=after['inference_state'],global_generation_locks_after=0,
    ollama_models_loaded_after_check=after['ollama_models_loaded_after_check'],
    published_sql_eligible_for_verified_session_actor=after['published_sql_eligible_for_verified_session_actor'],
    source_check_scope='SQL eligibility/counts and unauthenticated HTTP401 only; no private source opened',
    unauthenticated_endpoint_statuses={k:after[k] for k in after if k.startswith('unauthenticated_')},
    migrations_executed=False,dependencies_installed=False,full84_executed=False,holdout36_executed=False,
    business_document_semantic_e2e_executed=False,real_cancellation_test_repeated=False,
    known_critical_semantic_failures=['rag04-acl-04','rag04-no_evidence-01'],
    new_noncritical_observation='Technical greeting misnamed BOB as Bolivares; generic capability wording requires human review. No financial action or enterprise-document assertion was executed.',
    earlier_preventive_rollback=event['earlier_attempt'],
    rollback_ready='restore exact env.before from protected r3 packet and reload backend; no DB rollback',
    rollout_scope='all currently authorized LENY users; not restricted to ADMIN',
    pending=['owner enterprise-document review and source navigation','human semantic rubric','independent holdout preparation/validation','formal SPEC04 acceptance'],
    artifacts_sha256={name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in artifacts})
output=folder/'leny_rag04_pilot_activation_verified.json'
if output.exists():raise ValueError('Preserve previous activation verification')
output.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:record[k] for k in ('state','runtime_policy_verified_in_completed_message','public_tables_compared',
    'public_data_unchanged','preexisting_history_unchanged','role_codes_unchanged','inference_state_after',
    'ollama_models_loaded_after_check','source_freeze_still_matches')}))
