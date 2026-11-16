"""One synthetic-only coverage experiment. No database or model invocation.

Strict DRAFT rejection and exploratory simulated approval are separate outputs.
The latter never enables release or counts as real end-to-end observations.
Inputs are fixed frozen synthetic artifacts, never enterprise documents.
"""
from __future__ import annotations

import argparse
from collections import Counter
import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path
import socket
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'backend'))

from app.services.leny_rag_coverage import CoverageVerifier, MemoryCoverageProvider, digest


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def process_memory():
    """Windows process RSS/peak, not model RAM or guaranteed isolated peaks."""
    if sys.platform != 'win32':
        return None
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                    *[(name, ctypes.c_size_t) for name in ['PeakWorkingSetSize', 'WorkingSetSize',
                       'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                       'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage']]]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    value = Counters(); value.cb = ctypes.sizeof(value)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(value), value.cb):
        return None
    return dict(rss_bytes=value.WorkingSetSize, peak_rss_bytes=value.PeakWorkingSetSize)


def bound_rows(observation, package):
    """Only actual selected SQL identities; no gold enters the evidence adapter."""
    selected = observation.get('sent_fragment_ids') or []
    sql = {r['fragment']: r for r in observation.get('sql_candidates', [])}
    rows = []
    for fid in selected:
        if fid not in sql:
            raise ValueError('Selected source not present in recorded SQL eligibility')
        identity = sql[fid]
        manifest = next((m for m in package['manifests'] if m['document_id'] == identity['document_id']), None)
        if manifest is None:
            raise ValueError('Missing synthetic binding')
        rows.append(dict(fragment_id=fid, document_id=identity['document_id'],
            version_id=identity['version_id'], indexation_id=identity['indexation_id'],
            source_sha256=manifest['source_sha256'], text=package['fragment_texts'][fid]))
    return rows


def decision_record(decision):
    return dict(verdict=decision.verdict, reason=decision.reason, signature=decision.signature,
                proposed_fragment_ids=list(decision.fragment_ids), release_allowed=decision.release_allowed,
                authoritative=decision.authoritative, manifest_fingerprints=list(decision.manifest_fingerprints))


def metric(ids, relevant):
    if not relevant:
        return None
    values = ids[:5]
    ranks = [i+1 for i, value in enumerate(values) if value in relevant]
    return dict(hit=int(bool(ranks)), recall=len(set(values)&set(relevant))/len(set(relevant)),
                precision=len(set(values)&set(relevant))/len(values) if values else 0,
                mrr=1/ranks[0] if ranks else 0)


def control_adapter(case, controls, grammar):
    """Proposed source annotations only. Never consumes query_signature/gold."""
    eligible = set(case['evidence']['eligible_fragment_ids_at_target'])
    fragments = case['evidence']['fragments']
    allowed = [f for f in fragments if f['fragment_id'] in eligible]
    if any(not f['authorized_at_target'] or not f['published_at_target'] for f in allowed):
        raise ValueError('Control eligibility contradiction')
    vocab = dict(version='control-extension-draft-v1', approval=dict(state='draft'),
                 concepts=controls['proposed_control_vocabulary']['concepts'],
                 grammar_words=grammar, presentation_phrases=[], complete_phrases=[],
                 comparison_phrases=[], followup_phrases=[])
    rows, manifests = [], []
    groups = {}
    for f in allowed:
        groups.setdefault(f['document_id'], []).append(f)
    for doc, parts in groups.items():
        source = digest(json.dumps([(f['fragment_id'], f['text']) for f in parts], ensure_ascii=False))
        units = []
        for f in parts:
            annotation = f['proposed_coverage']
            units.append(dict(fragment_id=f['fragment_id'], text_sha256=digest(f['text']),
                 spans=[dict(start=s['start'], end=s['end'], sha256=digest(f['text'][s['start']:s['end']]))
                        for s in annotation['spans']], topics=annotation['topics'], aspects=annotation['aspects'],
                 qualifiers=annotation['qualifiers'], required_fragment_ids=annotation['required_fragment_ids']))
            rows.append(dict(fragment_id=f['fragment_id'], document_id=doc,
                             version_id=doc+'-version-'+str(f['version']),
                             indexation_id=f['indexation_id'], source_sha256=source, text=f['text']))
        manifests.append(dict(revision=1, document_id=doc, version_id=rows[-1]['version_id'],
            indexation_id=parts[0]['indexation_id'], source_sha256=source,
            source_hash_basis='synthetic_virtual_document', vocabulary_version=vocab['version'],
            approval=dict(state='draft'), units=units))
    return CoverageVerifier(MemoryCoverageProvider(vocab, manifests)), rows


def experiment(corpus, observations, turns, package, controls):
    cases = {c['id']: c for c in corpus['cases']}
    gate = CoverageVerifier(MemoryCoverageProvider(package['vocabulary'], package['manifests']))
    results, samples, prerequisites, anchors = [], [], [], {}
    before_memory = process_memory()
    for turn in turns:
        if turn.get('event') != 'turn':
            continue
        observed = turn.get('observation')
        if not observed:
            raise ValueError('All admitted synthetic turns must have observations')
        if observed['observed_turn'] >= observed['target_turn']:
            continue
        case = cases[turn['case_id']]
        question = case['prior_user_questions'][observed['observed_turn']]
        ids = []
        if observed['route'] == 'rag':
            checked = gate.evaluate(question, bound_rows(observed, package), research=True)
            ids = list(checked.fragment_ids)
            prerequisites.append(dict(case_id=case['id'], turn=observed['observed_turn'],
                                      question=question, decision=decision_record(checked)))
        anchors[case['id']] = [dict(role='user', content=question, documentary=True)] if ids else []
    for observed in observations['cases']:
        case = cases[observed['case_id']]
        entry = dict(case_id=case['id'], category=case['category'], question=case['question'],
                     role=case['role'], baseline_route=observed['route'], target_executed=observed.get('target_executed'),
                     baseline_sent_ids=observed.get('sent_fragment_ids') or [],
                     strict=None, exploratory=None, simulated_retained_ids=[], selection_added_ids=[])
        if observed.get('target_executed') and observed['route'] == 'rag':
            rows = bound_rows(observed, package)
            started = perf_counter()
            strict = gate.evaluate(case['question'], rows, history=anchors.get(case['id'], []))
            checked = gate.evaluate(case['question'], rows, history=anchors.get(case['id'], []), research=True)
            samples.append((perf_counter()-started)*1000)
            entry.update(strict=decision_record(strict), exploratory=decision_record(checked),
                         simulated_retained_ids=list(checked.fragment_ids),
                         simulated_route='rag' if checked.fragment_ids else 'no_evidence' if checked.verdict == 'not_covered' else 'uncertain')
        else:
            entry['simulated_route'] = observed['route']
        # Gold is read only AFTER the gate decided; never fed to resolver/provider.
        relevant = case['gold']['relevant_fragment_ids']
        entry['expected_route'] = case['gold']['route']
        entry['baseline_metrics'] = metric(entry['baseline_sent_ids'], relevant)
        entry['exploratory_metrics'] = metric(entry['simulated_retained_ids'], relevant)
        entry['new_loss_of_gold_evidence'] = bool(entry['baseline_metrics'] and entry['baseline_metrics']['hit']
                                                 and not entry['exploratory_metrics']['hit'])
        entry['unauthorized_simulated_ids'] = sorted(set(entry['simulated_retained_ids'])-set(case['gold']['authorized_fragment_ids']))
        results.append(entry)
    control_results = []
    for case in controls['cases']:
        control_gate, rows = control_adapter(case, controls, package['vocabulary']['grammar_words'])
        # Only the original prior user question and proposed fixture precondition
        # may supply a topic. No proposed query signature or assistant prose.
        context = case.get('context', {})
        anchor = context.get('prior_documentary_anchor', {})
        history = [dict(role='user', content=q, documentary=True)
                   for q in context.get('prior_user_questions', [])[-1:]] if (
                       rows and anchor.get('authorized_when_created') and
                       context.get('document_authorized_at_target', True)) else []
        checked = control_gate.evaluate(case['question'], rows, history=history, research=True)
        control_results.append(dict(case_id=case['id'], polarity=case['polarity'],
            expected_decision=case['expected_decision'], decision=decision_record(checked),
            exact_decision_match=checked.verdict == case['expected_decision'],
            unsafe_acceptance=case['expected_decision']=='not_covered' and bool(checked.fragment_ids),
            history_basis='proposed_fixture_precondition_not_recorded_live_prior_turn' if history else 'no_current_authorized_anchor',
            annotation_human_reviewed=False))
    after_memory = process_memory()
    rag = [r for r in results if r['expected_route'] == 'rag']
    natural = [r for r in results if r['category']=='natural']
    critical = [r for r in results if r['case_id'] in {'rag04-acl-04','rag04-no_evidence-01'}]
    positives = [r for r in control_results if r['polarity']=='positive']
    negatives = [r for r in control_results if r['polarity']=='negative']
    p95 = sorted(samples)[max(0, __import__('math').ceil(.95*len(samples))-1)] if len(samples)>=30 else None
    counts = dict(records=len(results), targets_executed=sum(bool(r['target_executed']) for r in results),
        expected_rag=len(rag), baseline_hit=sum(r['baseline_metrics']['hit'] for r in rag),
        simulated_hit=sum(r['exploratory_metrics']['hit'] for r in rag),
        simulated_recall_macro=sum(r['exploratory_metrics']['recall'] for r in rag)/len(rag),
        natural_total=len(natural), natural_retained=sum(bool(r['simulated_retained_ids']) for r in natural),
        newly_lost_evidence=sum(r['new_loss_of_gold_evidence'] for r in results),
        critical_total=len(critical), critical_unsafe_acceptances=sum(bool(r['simulated_retained_ids']) for r in critical),
        critical_specific_rejections=sum(r['exploratory'] is not None and r['exploratory']['verdict']=='not_covered' and r['exploratory']['reason'] in {'coverage_subject_mismatch','coverage_specialization_not_supported'} for r in critical),
        controls_positive_correct=sum(r['exact_decision_match'] for r in positives), controls_positive_total=len(positives),
        controls_negative_correct=sum(r['exact_decision_match'] for r in negatives), controls_negative_total=len(negatives),
        controls_unsafe_acceptances=sum(r['unsafe_acceptance'] for r in control_results),
        unauthorized_simulated_ids=sum(len(r['unauthorized_simulated_ids']) for r in results))
    return dict(scope='offline_coverage_replay_not_real_generation_or_new_sql', coverage_version='coverage-prototype-v1',
        human_review_complete=False, acceptance='not_accepted',
        approval_blockers=['draft_vocabulary_and_manifests','control_expectations_not_human_reviewed'],
        source_hash_basis='virtual_synthetic_documents_not_uploaded_files',
        control_basis='proposed_control_vocabulary_extension_not_independent_unseen_language_test',
        qwen_calls=0, embedding_calls=0, postgres_connections=0, business_documents_read=False,
        candidate_activated=False, evaluation84_executed=False, holdout_executed=False,
        strict_approved_release_count=sum(bool(r['strict'] and r['strict']['release_allowed']) for r in results),
        counts=counts, cases=results, prerequisites=prerequisites, controls=control_results,
        performance=dict(basis='per_target_two_gate_passes_strict_plus_research_not_http_latency', samples=len(samples),
                         p95_ms=p95, max_ms=max(samples) if samples else None,
                         memory_before=before_memory, memory_after=after_memory,
                         rss_growth_bytes=after_memory['rss_bytes']-before_memory['rss_bytes'] if after_memory and before_memory else None))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    target = Path(args.output).resolve()
    evidence = (ROOT/'documentacion/evidencias').resolve()
    if target.parent != evidence or not target.name.startswith('leny_rag04_coverage_') or target.suffix != '.json' or target.exists():
        parser.error('Use a new leny_rag04_coverage_*.json inside documentacion/evidencias; no overwrites.')
    paths = dict(corpus=ROOT/'backend/tests/fixtures/leny_rag04_development.json',
        observations=evidence/'leny_rag04_semantic_focused.json',
        journal=evidence/'leny_rag04_semantic_focused.json.jsonl',
        package=ROOT/'backend/tests/fixtures/leny_rag04_coverage_draft.json',
        controls=ROOT/'backend/tests/fixtures/leny_rag04_coverage_controls.json')
    data = {key: read(path) for key,path in paths.items() if key!='journal'}
    if any(data[k].get('data_classification')!='synthetic' for k in ['corpus','observations','package','controls']):
        raise ValueError('Only fixed synthetic artifacts are permitted')
    package = data['package']
    if sha(paths['corpus']) != package['corpus_sha256'] or sha(paths['observations']) != package['baseline_sha256']:
        raise ValueError('Frozen synthetic source changed')
    # No connection to Ollama, PostgreSQL, subprocesses or arbitrary applications.
    def forbidden(*_args, **_kwargs):
        raise RuntimeError('Offline coverage experiment forbids network operations')
    socket.socket = forbidden
    def audit(event, _args):
        if event in {'subprocess.Popen','os.system','os.posix_spawn','os.exec'}:
            raise RuntimeError('Offline coverage experiment forbids external processes')
    sys.addaudithook(audit)
    turns = [json.loads(line) for line in paths['journal'].read_text('utf-8').splitlines()]
    result = experiment(data['corpus'],data['observations'],turns,package,data['controls'])
    result['inputs_sha256'] = {k:sha(p) for k,p in paths.items()}
    source_paths = [Path(__file__), ROOT/'backend/app/services/leny_rag_coverage.py',
                    ROOT/'backend/app/services/leny_service.py', ROOT/'backend/app/services/leny_rag_diagnostics.py']
    result['source_sha256'] = {str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in source_paths}
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(output=str(target.relative_to(ROOT)),acceptance=result['acceptance'],counts=result['counts'],
                         p95_ms=result['performance']['p95_ms']),ensure_ascii=True))


if __name__ == '__main__':
    main()
