"""Offline SPEC03.1 packet and public technical counters, no inference.

Source texts/responses remain under the protected private checkpoint. Does not
change an older SPEC03 packet or replace failed attempts with newer answers.
"""
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import sys

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND/'scripts'))
import build_leny_spec03_review as packet
from run_leny_spec03_review import save

REVIEW_IDENTITIES=('location','manager','dress','after','detail','actor','next','sources',
    'd-controller','d-other','f-modista','f-advisor','f-absent','f-manual','qwen-drafting-corrected','e-entity',
    'active-location','active-manager','active-duties','active-sources')


def render_review(review,jobs,identities):
    rendered=packet.render(review,jobs,identities,{'cases':[]})
    rendered=rendered.replace('SPEC03','SPEC03.1').replace('SPEC-03','SPEC-03.1')
    # Missing comparisons are not observations; avoid hundreds of empty cards.
    # Recorded failures remain visible and all attempts stay in the JSON.
    rendered=re.sub(r'<article><h3>[^<]*</h3><p>Sin resultado ejecutado\.</p></article>','',rendered)
    start=rendered.index('<p>C1 y C2 ')
    end=rendered.index('</p>',start)+4
    return rendered[:start]+('<p>A conserva la referencia habitual anterior; B no es una referencia inmutable. '
        'Los intentos C, C2 y C4 incluyen errores corregidos posteriormente; C5 confirma el recorrido de referencias. '
        'D registra la comprobación ordinaria tras activar continuidad; no hay aceptación humana. '
        'Todos los intentos, incluidos fallos, '
        'permanecen en el apéndice privado. Se omiten paneles de condiciones no ejecutadas, '
        'sin ocultar fallos registrados. F conserva abstenciones de continuación; G verifica redacción Qwen.</p>')+rendered[end:]


def roots():
    base=Path(os.environ['LOCALAPPDATA'])/'BAB_VDOS'
    current=Path((base/'leny-spec031/active.txt').read_text().strip())
    previous=Path((base/'leny-spec03/active.txt').read_text().strip())/'review'
    if current.parent!=base/'leny-spec031' or previous.parent.parent!=base/'leny-spec03':
        raise RuntimeError('Unexpected checkpoint roots')
    return current,previous


def main():
    current,previous=roots()
    from app.services.leny_document_storage import protect_directory
    protect_directory(current)
    review=current/'review';review.mkdir(exist_ok=True)
    results=review/'results';results.mkdir(exist_ok=True)
    jobs={};identities=[];provenance={};technical=[]
    for path in sorted((previous/'results').glob('031-*.json')):
        job=json.loads(path.read_text(encoding='utf-8'));jobs[path.stem]=job
        shutil.copy2(path,results/path.name)
        provenance[path.stem]=hashlib.sha256(path.read_bytes()).hexdigest()
        summary=packet.phase_summary(path.stem,job)
        summary['errors']=dict(Counter(row.get('error_code') for row in job['cases'] if row.get('error_code')))
        summary['policy_reasons']=dict(Counter(row.get('final',{}).get('reason_code') for row in job['cases'] if row.get('final',{}).get('reason_code')))
        summary['cases']=[dict(id=row['id'],**packet.observations(row),seconds=row.get('seconds'),
            reason_code=row.get('final',{}).get('reason_code')) for row in job['cases']]
        technical.append(summary)
        for case in job['cases']:
            if case['id'] not in identities:identities.append(case['id'])
            trace=previous/'traces'/('trace-'+case['request_id']+'.json')
            if trace.exists():
                target=review/'traces'/trace.name;target.parent.mkdir(exist_ok=True);shutil.copy2(trace,target)
                data=json.loads(trace.read_text(encoding='utf-8'))
                public_case=next(row for row in summary['cases'] if row['id']==case['id'])
                public_case['context_revision']=data.get('context_revision')
                public_case['diagnostics']=data.get('diagnostics')
    packet.PHASES=tuple(jobs)
    human=review/'human-review';human.mkdir(exist_ok=True)
    selected=[identity for identity in REVIEW_IDENTITIES if identity in identities]
    rendered=render_review(review,jobs,selected)
    warning=('<p class="notice">A es el habitual anterior. B conserva fallos de la ruta retirada, pero sus imports '
        'diferidos de contexto pudieron leer cambios durante la preparación: B no es una comparación pura e inmutable. '
        'C inicial y C2 final se conservan por separado, incluidos sus errores. Las diferencias de estado no certifican fidelidad.</p>')
    rendered=rendered.replace('<div class="toolbar">',warning+'<div class="toolbar">')
    (human/'REVISION_HUMANA_SPEC031.html').write_text(rendered,encoding='utf-8')
    (human/'APENDICE_TODOS_LOS_INTENTOS.html').write_text(render_review(review,jobs,identities),encoding='utf-8')
    save(human/'REVISION_HUMANA_SPEC031.json',dict(human_acceptance=None,jobs=jobs,
        development_identities=selected,reserved_empty_slots=8,reserved_questions_opened=False))
    report=dict(at=datetime.now(timezone.utc).isoformat(),phases=technical,
        human_acceptance=None,semantic_success_certified=False,
        baseline_b_comparable=False,baseline_b_limitation='Deferred context imports could observe local changes; keep historical failures, do not infer a pure algorithm comparison.',
        private_result_sha256=provenance,development_review_slots=len(selected),reserved_empty_slots=8,reserved_holdout_opened=False)
    save(BACKEND.parent/'documentacion/evidencias/leny_spec031_comparison.json',report)
    print('SPEC03.1 private packet:',len(jobs),'jobs,',sum(len(j['cases']) for j in jobs.values()),'turns; no human scores assigned.')


if __name__=='__main__':main()
