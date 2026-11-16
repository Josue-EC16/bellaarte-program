"""Record preparation evidence only; never activate or start business services."""
from pathlib import Path
import hashlib
import importlib.metadata as metadata
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
BACKEND=ROOT/'backend'
sys.path.insert(0,str(BACKEND))
os.chdir(BACKEND)
from app.core.config import settings
from app.services.leny_document_storage import DocumentStorage
from scripts.leny_rag_pilot_profile import validate_recovery_proof
from app.services.leny_rag_evaluation import snapshot_manifest

evidence=ROOT/'documentacion/evidencias'
private=Path(os.environ['LOCALAPPDATA'])/'BAB_VDOS/leny-pilot/leny-rag-v1-piloto-20261021-r3'
proof=json.loads((private/'recovery-proof.json').read_text('utf-8'))
validate_recovery_proof(private,proof,DocumentStorage(settings).root/'backups',ROOT)
freeze=snapshot_manifest(ROOT)
freeze['operational_code_files_sha256']=proof['source_files_sha256']
freeze['pilot_id']=private.name
freeze['code_archive_sha256']=proof['code_sha256']
freeze_path=evidence/'leny_rag04_pilot_freeze_r3.json'
freeze_path.write_text(json.dumps(freeze,indent=2)+'\n',encoding='utf-8')
observations=json.loads((evidence/'leny_rag04_pilot_supervised_real.json').read_text())
score=json.loads((evidence/'leny_rag04_pilot_supervised_score.json').read_text())
assert observations['source_freeze_verified'] and observations['model_identity_verified'] and observations['cleanup_confirmed']
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in observations['source_files_sha256'].items())
assert observations['component_versions']['policy']=='rag4-v4'
assert len(observations['cases'])==6
settings_record={k:getattr(settings,k) for k in observations['settings']}
ram=[r[k] for r in observations['cases'] for k in ('ram_available_before_bytes','ram_available_after_bytes')]
git=subprocess.run(['git','status','--porcelain=v1','--untracked-files=all'],cwd=ROOT,capture_output=True,check=True)
runtime=dict(python=platform.python_version())
for name in ('fastapi','uvicorn','sqlalchemy','alembic','pydantic','pydantic-settings','casbin','httpx','psycopg2-binary','pytest'):
    runtime[name]=metadata.version(name)
gpu=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,memory.used','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True)
gpu_row=gpu.stdout.strip().split(',')
gpu_record=dict(name=gpu_row[0].strip(),total_mib=int(gpu_row[1]),used_mib=int(gpu_row[2]),measurement='post_evaluation_snapshot_not_peak')
with urllib.request.urlopen('http://127.0.0.1:11434/api/version',timeout=5) as handle:
    runtime['ollama']=json.load(handle)['version']
with urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=5) as handle:
    backend_health=handle.status
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://localhost:5173/',timeout=5) as handle:
    frontend_health=handle.status
artifact_names=('leny_rag04_pilot_drift_audit.json','leny_rag04_pilot_supervised_real.json',
    'leny_rag04_pilot_supervised_real.json.jsonl','leny_rag04_pilot_supervised_score.json',
    'leny_rag04_pilot_contracts.json','leny_rag04_pilot_recovery_r3.json',
    'leny_rag04_pilot_frontend_20261021_105603.json','leny_rag04_pilot_freeze_r3.json')
record=dict(schema_version='leny-supervised-pilot-predeployment-v1',pilot_id=private.name,
    created_utc=datetime.now(timezone.utc).isoformat(),state='PREPARED_AWAITING_OWNER_ACTIVATION_CONFIRMATION',
    acceptance='PILOTO SUPERVISADO - ACEPTACION FORMAL PENDIENTE',
    business_profile=settings.leny_rag_profile,business_env_unchanged=True,coverage_verifier_enabled=False,
    candidate_profile='rag4_v1',component_versions=observations['component_versions'],
    real_test_settings=observations['settings'],usual_settings=settings_record,model_identity=observations['model_identity'],
    runtime=runtime,source_freeze_manifest_sha256=freeze['manifest_sha256'],
    real_evaluated_code_still_matches=True,private_recovery_guard_passed=True,
    git_status_sha256=hashlib.sha256(git.stdout).hexdigest(),
    git_status_entry_count=len(git.stdout.splitlines()),git_state='dirty_modified_and_untracked_preserved',
    artifacts_sha256={name:hashlib.sha256((evidence/name).read_bytes()).hexdigest() for name in artifact_names},
    test_results=dict(backend_passed=892,backend_skipped=1,backend_warning='pypdf_add_js_deprecation',
        backend_seconds=13.49,
        postgres_passed=104,postgres_deselected_migration_cases=5,postgres_seconds=51.86,postgres_ddl_attempts=0,
        frontend_passed=117,frontend_files=18,frontend_lint_exit=0,frontend_build_exit=0,
        real_synthetic_routes_correct=6,real_synthetic_cases=6,real_errors=0,real_context_errors=0,
        human_review_completed=False,full84_reexecuted=False,holdout36_executed=False,business_e2e_executed=False),
    real_case_summary=[dict(id=r['case_id'],route=r['route'],status=r['status'],
        sent_fragments=len(r['sent_fragment_ids']),cited_fragments=len(r['citation_fragment_ids']),
        latency_ms=r['latency_ms'],error_code=r['error_code']) for r in observations['cases']],
    offline_score_acceptance=score['acceptance'],offline_score_acceptance_failures=score['acceptance_failures'],
    semantic_human_metrics='not_measured_do_not_infer_from_literal_output',
    performance=dict(generation_request_mean_ms=score['metrics']['latency_ms'],
        generation_request_min_ms=min(r['latency_ms'] for r in observations['cases']),
        generation_request_max_ms=max(r['latency_ms'] for r in observations['cases']),
        p95_ms=None,p95_reason='six_samples_only',ram_available_min_bytes=min(ram),ram_available_max_bytes=max(ram),
        ram_basis='before_and_after_each_generation_not_peak',gpu=gpu_record),
    known_critical_semantic_failures=['rag04-acl-04','rag04-no_evidence-01'],
    backend_health_status=backend_health,
    usual_frontend_state='healthy_localhost_5173_listening_on_ipv6_loopback',frontend_health_status=frontend_health,
    frontend_inspection_correction='initial_probe_was_ipv4_only_do_not_start_a_duplicate_Vite',
    usual_worker_state='stopped_no_pending_jobs_at_preflight',
    rollout_scope='global_for_all_currently_authorized_LENY_users_not_ADMIN_only',
    rollback='restore_exact_private_env_before_then_reload_backend_no_database_rollback',
    pending=['owner_explicit_activation_confirmation','effective_runtime_config_after_reload',
        'postactivation_session_chat_sources_checks','owner_business_semantic_review',
        'independent_holdout_preparation_and_validation'])
output=evidence/'leny_rag04_pilot_predeployment_r3.json'
output.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:record[k] for k in ('pilot_id','business_profile','source_freeze_manifest_sha256','real_evaluated_code_still_matches','private_recovery_guard_passed','performance','runtime')}))
