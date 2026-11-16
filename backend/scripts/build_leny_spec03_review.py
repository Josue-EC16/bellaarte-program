"""Offline private HTML/JSON review packet and content-free public counters.

No HTTP, database, SDK or inference. All document text remains under the
protected review root. Human judgments are deliberately left empty.
"""
import argparse
from collections import Counter
import html
import json
import math
from pathlib import Path
import statistics

from run_leny_spec03_review import BACKEND, CORPUS, prepare, root_path, save

PHASES = ('B0-Gemini-real', 'C1-Gemini-spec03', 'C2-Gemini-spec03', 'Z-Qwen-real')
RUBRIC = (
    ('interpretation', 'Interpretación de la pregunta'),
    ('retrieval', 'Recuperación pertinente'),
    ('selection', 'Selección de evidencia'),
    ('fidelity', 'Fidelidad por afirmación'),
    ('completeness', 'Completitud y condiciones'),
    ('attribution', 'Cargo, cifras y unidades correctos'),
    ('citations', 'Respaldo de las citas'),
    ('continuity', 'Continuidad sin repetición'),
    ('utility', 'Claridad y utilidad'),
)


def escaped(value):
    return html.escape(str(value), quote=True)


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def observations(case):
    """Transport checks only, never semantic assessments."""
    final = case.get('final', {})
    events = case.get('events', [])
    terminals = [e for e in events if isinstance(e, dict) and e.get('type') in ('done', 'error')]
    sources = case.get('sources', [])
    return dict(
        http_status=case.get('http_status'), termination=case.get('termination'),
        outcome=final.get('outcome'), scope=final.get('response_scope'),
        response_nonempty=bool(case.get('response', '').strip()),
        terminal_event_count=len(terminals), terminal_count_valid=len(terminals) == 1,
        declared_sources=len(final.get('sources', [])), inspected_sources=len(sources),
        sources_http200=sum(s.get('http_status') == 200 for s in sources),
        history_match=case.get('history_matches_response'), history_status=case.get('history_status'),
        error_code=case.get('error_code'), check_error=case.get('check_error'))


def phase_summary(name, job):
    rows = job.get('cases', [])
    times = [r['seconds'] for r in rows if number(r.get('seconds'))]
    checks = [observations(r) for r in rows]
    outcomes = Counter(c['outcome'] or c['termination'] or 'unknown' for c in checks)
    scopes = Counter(c['scope'] or 'not_labeled' for c in checks)
    history = [c['history_match'] for c in checks if isinstance(c['history_match'], bool)]
    return dict(phase=name, state=job.get('state', 'unknown'), cases_n=len(rows),
        attempted_http_n=sum(c['http_status'] is not None for c in checks),
        completed_terminal_n=sum(c['termination'] == 'done' for c in checks),
        outcomes=dict(outcomes), scopes=dict(scopes),
        documentary_response_n=sum(c['outcome'] == 'answered' and c['scope'] in ('documented', 'partial')
            and c['declared_sources'] > 0 for c in checks),
        general_response_n=sum(c['scope'] == 'general' for c in checks),
        references_http200_n=sum(c['sources_http200'] for c in checks),
        references_inspected_n=sum(c['inspected_sources'] for c in checks),
        references_declared_n=sum(c['declared_sources'] for c in checks),
        history_match_n=sum(v is True for v in history), history_checked_n=len(history),
        seconds_n=len(times), seconds_individual=times,
        seconds_median=statistics.median(times) if times else None,
        seconds_range=[min(times), max(times)] if times else None,
        p95=None, p95_reason='Fewer than 30 comparable samples per condition; heterogeneous cases are not pooled',
        human_acceptance=None, semantic_success_rate=None)


def read_inputs(root, corpus):
    jobs = {}
    for phase in PHASES:
        path = root/'results'/(phase+'.json')
        jobs[phase] = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'cases': [], 'state': 'missing'}
    # Actual jobs may use owner-provided business questions. Match gold only by
    # case identity, NEVER attach fictitious document facts by ordinal position.
    identities = []
    for phase in PHASES:
        job_path = root/'jobs'/(phase+'.json')
        source = json.loads(job_path.read_text(encoding='utf-8')) if job_path.exists() else jobs[phase]
        for case in source.get('cases', []):
            if case['id'] not in identities:
                identities.append(case['id'])
    if len(identities) > 20:
        raise ValueError('More than 20 development identities: reconcile jobs before building review')
    for case in corpus['cases']:
        if len(identities) == 20:
            break
        if case['id'] not in identities:
            identities.append(case['id'])
    return jobs, identities


def rubric_markup(prefix):
    fields = []
    for key, label in RUBRIC:
        fields.append('<label>'+escaped(label)+' <select data-review="'+escaped(prefix+'.'+key)+'">'
            '<option value="">Pendiente</option><option value="0">0 — Incorrecto</option>'
            '<option value="1">1 — Parcial</option><option value="2">2 — Satisfactorio</option>'
            '<option value="na">No aplicable</option></select></label>')
    fields.append('<label>Error crítico <select data-review="'+escaped(prefix+'.critical')+'">'
        '<option value="">Pendiente</option><option value="yes">Sí</option><option value="no">No</option></select></label>')
    fields.append('<label>Observaciones humanas<textarea data-review="'+escaped(prefix+'.notes')+'"></textarea></label>')
    return '<div class="rubric">'+''.join(fields)+'</div>'


def render(root, jobs, identities, corpus):
    gold = {c['id']: c for c in corpus['cases']}
    sections = []
    for ordinal, identity in enumerate(identities, 1):
        rows = {phase: next((r for r in jobs[phase].get('cases', []) if r['id'] == identity), None) for phase in PHASES}
        example = next((row for row in rows.values() if row), {})
        expected = gold.get(identity)
        if expected and any(row and row.get('question')!=expected.get('question') for row in rows.values()):
            expected=None  # A synthetic fact is never gold for a real business question.
        expected_text = (json.dumps({k: expected[k] for k in ('expected_intent', 'essential_fact_ids', 'forbidden')},
            ensure_ascii=False, indent=2) if expected else
            'Pendiente de revisión del propietario: caso empresarial sin gold documental adjudicado. No inferir completitud.')
        question = example.get('question', expected.get('question', '') if expected else '')
        sections.append('<section><h2>Desarrollo '+str(ordinal)+' — '+escaped(identity)+'</h2>'
            '<label>Pregunta<textarea data-review="dev.'+str(ordinal)+'.question">'+escaped(question)+'</textarea></label>'
            '<label>Expectativas editables — provisionales<textarea data-review="dev.'+str(ordinal)+'.expected">'
            +escaped(expected_text)+'</textarea></label><div class="comparison">')
        for phase in PHASES:
            row = rows[phase]
            sections.append('<article><h3>'+escaped(phase)+'</h3>')
            if row is None:
                sections.append('<p>Sin resultado ejecutado.</p></article>')
                continue
            conversation = row.get('persisted_conversation') or {}
            sections.append('<p>Proveedor: '+escaped(conversation.get('llm_provider', jobs[phase].get('provider', 'sin registrar')))
                +' · Perfil: '+escaped(conversation.get('quality_profile', jobs[phase].get('quality_profile', 'sin registrar')))
                +' · Modelo: '+escaped(conversation.get('llm_model', 'sin registrar'))+'</p>')
            prior = []
            for old in jobs[phase].get('cases', []):
                if old is row:
                    break
                if row.get('conversation_id') and old.get('conversation_id') == row['conversation_id']:
                    prior.append(dict(question=old.get('question', ''), response=old.get('response', '')))
            sections.append('<details><summary>Contexto conversacional anterior</summary><pre>'
                +escaped(json.dumps(prior, ensure_ascii=False, indent=2))+'</pre></details>'
                '<h4>Respuesta emitida</h4><pre>'+escaped(row.get('response', '(sin texto emitido)'))+'</pre>'
                '<details><summary>Integridad automática — no evalúa fidelidad</summary><pre>'
                +escaped(json.dumps(observations(row), ensure_ascii=False, indent=2))+'</pre></details>')
            for source in row.get('sources', []):
                detail = source.get('detail') or {}
                sections.append('<details><summary>Fuente '+escaped(detail.get('citation_id', '?'))+' — '
                    +escaped(detail.get('label', 'no disponible'))+' (HTTP '+escaped(source.get('http_status'))+')</summary>'
                    '<pre>'+escaped(json.dumps(detail.get('locator', {}), ensure_ascii=False))+'</pre>'
                    '<pre>'+escaped(detail.get('text', '(sin pasaje accesible)'))+'</pre></details>')
            declared = row.get('final', {}).get('sources', [])
            sections.append('<details><summary>Referencias declaradas por la respuesta</summary><pre>'
                +escaped(json.dumps(declared, ensure_ascii=False, indent=2))+'</pre></details>')
            sections.append(rubric_markup('dev.'+str(ordinal)+'.'+phase)+'</article>')
        sections.append('</div><label>Nueva prueba de la versión corregida (propietario): pregunta, respuesta y fuentes'
            '<textarea data-review="dev.'+str(ordinal)+'.current_execution"></textarea></label></section>')
    for number in range(1, 9):
        prefix='reserved.'+str(number)
        sections.append('<section><h2>Reservado '+str(number)+' — custodia del propietario</h2>'
            '<p>Casilla vacía. No se generó ni abrió una pregunta reservada; no es una prueba ejecutada.</p>'
            '<label>Pregunta reservada<textarea data-review="'+prefix+'.question"></textarea></label>'
            '<label>Expectativas / evidencia adjudicada<textarea data-review="'+prefix+'.expected"></textarea></label>'
            '<label>Respuesta y procedencia de ejecución<textarea data-review="'+prefix+'.response"></textarea></label>'
            +rubric_markup(prefix)+'</section>')
    return '''<!doctype html><html lang="es"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; img-src 'none'; base-uri 'none'; form-action 'none'">
<title>Revisión humana privada LENY SPEC03</title><style>
body{font-family:system-ui,sans-serif;margin:20px;color:#222;background:#faf8f4}h1,h2{color:#623e30}section{background:white;padding:20px;margin:24px 0;border:1px solid #c9b8a9;border-radius:10px}.comparison{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}article{min-width:0;padding:12px;border:1px solid #ddd}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f3ef;padding:10px;font:14px/1.6 system-ui}label{display:block;margin:12px 0}textarea{display:block;box-sizing:border-box;min-height:95px;width:100%;padding:8px;font:14px/1.5 system-ui}select,button,input{padding:8px;font:inherit}summary{cursor:pointer;padding:8px}.notice{padding:16px;border:2px solid #9c663d}.toolbar{display:flex;gap:12px;flex-wrap:wrap}select:focus-visible,textarea:focus-visible,button:focus-visible{outline:3px solid #935b30}@media(max-width:1100px){.comparison{grid-template-columns:1fr}}@media print{.toolbar{display:none}section{break-inside:avoid}}
</style><h1>LENY SPEC03 — revisión humana privada</h1>
<p class="notice">Contiene respuestas y documentación empresarial privada. No compartir ni subir a servicios externos.
HTTP 200, JSON válido o una cita reconocida no prueban respaldo semántico. Ninguna valoración humana viene completada.
Los consejos generales se revisan aparte y no cuentan como éxito documental. Las ocho casillas reservadas están vacías.</p>
<p>C1 y C2 son intentos históricos conservados, con fallos. La versión corregida posterior aún requiere una nueva prueba documental real con RAM suficiente. No interpretar estos paneles como aprobación de esa versión. Puedes registrar la nueva ejecución en el campo al final de cada caso.</p>
<div class="toolbar"><button id="export" type="button">Guardar rúbrica local JSON</button><label>Recuperar rúbrica JSON <input id="import" type="file" accept="application/json"></label><button type="button" onclick="window.print()">Imprimir revisión</button></div>
<p>No se guarda automáticamente en navegador ni se transmite información. Guarda la rúbrica en la misma carpeta privada del paquete.</p>
''' + ''.join(sections) + '''<script>
'use strict';
const fields=()=>Array.from(document.querySelectorAll('[data-review]'));
document.getElementById('export').onclick=()=>{const values={};for(const field of fields())values[field.dataset.review]=field.value;const blob=new Blob([JSON.stringify({schema:'leny-spec03-human-review-v1',human_scores_are_owner_entered:true,values},null,2)],{type:'application/json'});const link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download='REVISION_HUMANA_SPEC03.json';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000)};
document.getElementById('import').onchange=async event=>{const file=event.target.files[0];if(!file)return;try{if(file.size>2000000)throw Error();const data=JSON.parse(await file.text());if(data.schema!=='leny-spec03-human-review-v1'||!data.values)throw Error();for(const field of fields()){const value=data.values[field.dataset.review];if(typeof value==='string')field.value=value}}catch{alert('Rúbrica no válida; no se importó contenido ejecutable.')}};
</script></html>'''


def build(root, public_path):
    corpus=json.loads(CORPUS.read_text(encoding='utf-8'))
    jobs, identities=read_inputs(root,corpus)
    private=root/'human-review';private.mkdir(exist_ok=True)
    # Protected parent inheritance applies to generated text and HTML alike.
    packet=dict(schema='leny-spec03-private-review-v1',human_acceptance=None,
        development_identities=identities,reserved_slots=[dict(slot=i,question='',expectations='',human_review=None) for i in range(1,9)],
        results=jobs,gold_provisional=corpus['cases'])
    save(private/'REVISION_HUMANA_SPEC03.json',packet)
    (private/'REVISION_HUMANA_SPEC03.html').write_text(render(root,jobs,identities,corpus),encoding='utf-8')
    summary=dict(schema='leny-spec03-public-integrity-v1',development_slots=20,reserved_empty_slots=8,
        human_acceptance=None,fidelity_certified=False,
        phases=[phase_summary(phase,jobs[phase]) for phase in PHASES])
    save(public_path,summary)
    return dict(development_slots=20,reserved_empty_slots=8,
        recorded_cases=sum(len(j['cases']) for j in jobs.values()),private_html=str(private/'REVISION_HUMANA_SPEC03.html'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    root=root_path();prepare(root)
    print(json.dumps(build(root,BACKEND.parent/'documentacion/evidencias/leny_spec03_review_integrity.json'),ensure_ascii=True))


if __name__=='__main__':
    main()
