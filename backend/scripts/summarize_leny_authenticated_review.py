"""Export content-free measurements and a PRIVATE human review packet.

Reads completed normal-API attempts. Never authenticates, infers or changes
application data. Raw responses/passages remain under the protected local root.
"""
import difflib
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import zipfile
from collections import Counter

from run_leny_authenticated_review import ROOT, BACKEND, prepare, save


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resources(phase):
    path = ROOT/'results'/('resources-'+phase+'.json')
    if not path.exists():
        return {'available': False}
    data = json.loads(path.read_text(encoding='utf-8'))
    samples = data.get('samples', [])
    ram = [row['ram_available_bytes']/1024**3 for row in samples if 'ram_available_bytes' in row]
    gpu = [row['gpu_memory_mib'] for row in samples if 'gpu_memory_mib' in row]
    model_gpu = [model.get('size_vram', 0)/1024**2 for row in samples for model in row.get('resident_models', [])]
    return {'available': True, 'scope': 'global_machine_not_process_attributed', 'samples': len(samples),
            'seconds': round(data.get('seconds', 0), 3),
            'ram_available_gib_min_max': [round(min(ram), 3), round(max(ram), 3)] if ram else None,
            'gpu_memory_mib_min_max': [min(gpu), max(gpu)] if gpu else None,
            'ollama_model_resident_vram_mib_max': round(max(model_gpu), 1) if model_gpu else None,
            'cold_warm': 'not_a_controlled_comparison; keep_alive=0'}


def export():
    prepare()
    phases, review = [], ['# Revisión humana privada LENY', '',
        'No subir este paquete al repositorio ni a servicios externos.',
        'Las puntuaciones humanas están pendientes. HTTP 200, answered o cita válida no prueban fidelidad.', '']
    base = ROOT/'results/B0-original-01.json'
    candidate = ROOT/'results/FINAL-effective-02.json'
    if base.exists() and candidate.exists():
        old_cases = {c['id']: c for c in json.loads(base.read_text(encoding='utf-8'))['cases']}
        review += ['## Comparación A/B de los mismos casos', '']
        for case in json.loads(candidate.read_text(encoding='utf-8'))['cases']:
            if case['id'] not in old_cases:
                continue
            old = old_cases[case['id']]
            review += ['### '+case['id'], '', '**Pregunta:** '+case['question'], '',
                '**A — B0 original:**', '', old.get('response', '(sin respuesta)'), '',
                '**B — candidata:**', '', case.get('response', '(sin respuesta)'), '',
                '**Preferencia humana / fidelidad / omisión / error crítico:** __________________', '']
    for path in sorted((ROOT/'results').glob('*.json')):
        if path.name.startswith(('trace-', 'resources-')):
            continue
        job = json.loads(path.read_text(encoding='utf-8'))
        if 'cases' not in job:
            continue
        phase, rows = job['job'], []
        review += ['## '+phase, '']
        for case in job['cases']:
            trace_path = ROOT/'results'/('trace-'+case.get('request_id', '')+'.json')
            trace = json.loads(trace_path.read_text(encoding='utf-8')) if trace_path.exists() else {}
            final = case.get('final', {})
            diagnostics = trace.get('diagnostics', {})
            rows.append({'case': case['id'], 'seconds': case['seconds'], 'http_status': case.get('http_status'),
                'termination': case.get('termination'), 'outcome': final.get('outcome'),
                'response_scope': final.get('response_scope'), 'reason_code': final.get('reason_code'),
                'response_nonempty': bool(case.get('response', '').strip()),
                'source_count_fragments': len(final.get('sources', [])),
                'source_access_http_statuses': [source['http_status'] for source in case.get('sources', [])],
                'effective_config': trace.get('config'),
                'synthesis_protocol': trace.get('prompt', {}).get('protocol'),
                'validation': trace.get('validation'), 'diagnostics': diagnostics})
            review += ['### '+case['id'], '', '**Pregunta:** '+case['question'], '',
                '**Respuesta emitida:**', '', case.get('response', '(sin respuesta)'), '',
                '**Resultado técnico:** '+json.dumps({k: rows[-1][k] for k in
                    ('seconds','outcome','response_scope','reason_code','source_count_fragments')}, ensure_ascii=False), '']
            for source in case.get('sources', []):
                detail = source.get('detail') or {}
                review += ['**Fuente '+str(detail.get('citation_id', '?'))+'** '+detail.get('label', ''),
                    json.dumps(detail.get('locator', {}), ensure_ascii=False), '', detail.get('text', ''), '']
            review += ['**Rúbrica pendiente (0/1/2):** respuesta directa __; fidelidad __; completitud __; '
                'cargo/cifras/condiciones __; citas __; continuidad __; utilidad __.',
                '**Error crítico / observación del propietario:** __________________', '']
        times = [row['seconds'] for row in rows]
        phases.append({'phase': phase, 'cases_n': len(rows),
            'outcomes': dict(Counter(row['outcome'] or row['termination'] for row in rows)),
            'scopes': dict(Counter(row['response_scope'] or 'not_labeled' for row in rows)),
            'all_referenced_sources_http200': all(status == 200 for row in rows for status in row['source_access_http_statuses']),
            'seconds_median': statistics.median(times) if times else None,
            'seconds_range': [min(times), max(times)] if times else None, 'cases': rows, 'resources': resources(phase)})
    changed = None
    before, after = ROOT/'library-before-final.json', ROOT/'library-after-final.json'
    if before.exists() and after.exists():
        left, right = (json.loads(p.read_text(encoding='utf-8')) for p in (before, after))
        changed = [key for key in left if key not in ('inference_state','jobs_active') and left[key] != right.get(key)]
    files = [p for folder in (BACKEND/'app', BACKEND/'scripts', BACKEND/'tests', BACKEND.parent/'frontend/src/pages/leny')
        for p in folder.rglob('*') if p.is_file() and p.suffix in ('.py','.js','.jsx','.ps1') and
        ('leny' in p.name.lower() or p.name == 'config.py')]
    manifest = {str(p.relative_to(BACKEND.parent)): digest(p) for p in files}
    save(ROOT/'candidate-code-manifest.json', manifest)
    head = subprocess.run(['git','rev-parse','HEAD'], cwd=BACKEND.parent, capture_output=True, text=True, check=True).stdout.strip()
    # Preserve the exact owner-modified starting tree, not just HEAD. This
    # patch excludes .env and never restores a whole unrelated file blindly.
    baseline = ROOT/'backups/20261103-112707'
    patch = []
    for old in sorted(baseline.rglob('*.py')):
        relative = old.relative_to(baseline)
        current = BACKEND/relative
        if current.exists() and old.read_bytes() != current.read_bytes():
            name = 'backend/'+relative.as_posix()
            patch += list(difflib.unified_diff(old.read_text(encoding='utf-8-sig').splitlines(True),
                current.read_text(encoding='utf-8-sig').splitlines(True), fromfile='a/'+name, tofile='b/'+name))
    (ROOT/'own-backend-changes.patch').write_text(''.join(patch), encoding='utf-8')
    archived = Path.home()/'AppData/Local/Temp/BAB_LENY_INCREMENTAL_20261103/documentacion/evidencias/leny_incremental_B0_code.zip'
    if archived.exists():
        frontend_patch = []
        with zipfile.ZipFile(archived) as archive:
            for name in ('frontend/src/pages/leny/LenyPage.jsx', 'frontend/src/pages/leny/useLenyChat.js',
                         'frontend/src/pages/leny/LenyPage.test.jsx'):
                old = archive.read(name).decode('utf-8-sig')
                current = (BACKEND.parent/name).read_text(encoding='utf-8-sig')
                frontend_patch += list(difflib.unified_diff(old.splitlines(True), current.splitlines(True),
                    fromfile='a/'+name, tofile='b/'+name))
        (ROOT/'own-frontend-changes.patch').write_text(''.join(frontend_patch), encoding='utf-8')
        save(ROOT/'frontend-rollback-provenance.json', {'archive_sha256': digest(archived),
            'basis': 'preserved initial B0 frontend snapshot', 'patch_sha256': digest(ROOT/'own-frontend-changes.patch')})
    # API evidence contains only codes/counts/timings/configuration, no titles,
    # questions, private text, accounts, tokens or local secret paths.
    result = {'head': head, 'tree_manifest_sha256': digest(ROOT/'candidate-code-manifest.json'),
        'human_acceptance': None, 'spec04_acceptance': 'not_demonstrated',
        'library_tables_changed_during_final': changed,
        'phases': phases, 'limits': ['no semantic judge', 'no p95 with N<30 per condition',
            'tokens with missing provider counts are lower bounds', 'global resources are not process allocation',
            'complete reserved SPEC04 set not executed', 'A4 experiment excluded due repetition']}
    public = BACKEND.parent/'documentacion/evidencias/leny_original_api_summary.json'
    public.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    table = ['# Resultados técnicos de las API normales', '',
        'No son puntuaciones de calidad humana. Cada fuente cuenta un fragmento.', '',
        '| Fase | Caso | Terminal | Resultado | Alcance | Fuentes | Segundos |',
        '|---|---|---|---|---|---:|---:|']
    for phase in phases:
        if phase['phase'] not in ('B0-original-01','FINAL-effective-01','FINAL-effective-02') and not phase['phase'].startswith('GENERAL-'):
            continue
        for row in phase['cases']:
            table.append('| '+ ' | '.join(str(v) if v is not None else '—' for v in
                (phase['phase'],row['case'],row['termination'],row['outcome'],row['response_scope'],
                 row['source_count_fragments'],row['seconds']))+' |')
    (public.parent/'leny_original_api_cases.md').write_text('\n'.join(table)+'\n', encoding='utf-8')
    totals = ['# Coste agregado por checkpoint', '',
        'Tokens: suma de contadores disponibles; no incluye contadores ausentes. RAM/VRAM: globales.', '',
        '| Fase | N | Llamadas | Entrada tokens | Salida tokens | Llamadas sin tokens | Mediana s | RAM libre GiB mín. | VRAM global MiB máx. |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for phase in phases:
        keys = ('inference_calls_total','prompt_tokens_total','output_tokens_total','calls_without_token_counts')
        counters = [sum(row.get('diagnostics',{}).get('counts',{}).get(k,0) for row in phase['cases'])
            if any(k in row.get('diagnostics',{}).get('counts',{}) for row in phase['cases']) else 'sin contador'
            for k in keys]
        resource = phase['resources']
        ram = resource.get('ram_available_gib_min_max')
        gpu = resource.get('gpu_memory_mib_min_max')
        values = (phase['phase'],phase['cases_n'],*counters,round(phase['seconds_median'],3),
                  ram[0] if ram else 'sin muestra',gpu[1] if gpu else 'sin muestra')
        totals.append('| '+' | '.join(str(v) for v in values)+' |')
    (public.parent/'leny_original_api_costs.md').write_text('\n'.join(totals)+'\n', encoding='utf-8')
    (ROOT/'REVISION_HUMANA.md').write_text('\n'.join(review), encoding='utf-8')
    print(json.dumps({'phases': len(phases), 'attempted_turns': sum(p['cases_n'] for p in phases),
        'library_tables_changed_during_final': changed, 'human_acceptance': None}))


if __name__ == '__main__':
    export()
