"""Synthetic-only SQL diagnostics, called after the existing PG55432 guard.

No chat model invocation. Gold is used exclusively to score recorded identities,
never as an input to SQL, ranking or production selection. Distances and frozen
synthetic source identities are safe here; this is not a production logger.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
import sys
import time
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def ranking_metrics(ids, relevant, k):
    values = list(dict.fromkeys(ids))[:k]
    hits = [i + 1 for i, value in enumerate(values) if value in relevant]
    if not relevant:
        return None
    return dict(hit=float(bool(hits)), recall=len(hits)/len(relevant),
                precision=len(hits)/len(values) if values else 0.0,
                mrr=1/hits[0] if hits else 0.0, denominator=1)


def analyze_layers(corpus, sql, chat):
    """Replay bounded selection at K3/K5 without Qwen or database access.

    Recorded review decisions are observations, never a gold oracle. Replaying
    the same plan with a stricter cap is not a new K-specific model experiment.
    Stage comparisons remain explicit even when a request failed operationally.
    """
    from app.services.leny_rag_selection import preselect, verify_plan, SELECTION_VERSION
    from app.services.leny_rag_evaluation import validate_corpus
    validate_corpus(corpus)
    if sql.get('data_classification') != 'synthetic' or chat.get('data_classification') != 'synthetic':
        raise ValueError('Only frozen synthetic observations may be replayed.')
    if sql['corpus_sha256'] != chat['corpus_sha256']:
        raise ValueError('Different corpora cannot be compared.')
    corpus_path = Path(__file__).resolve().parents[1]/'tests/fixtures/leny_rag04_development.json'
    if hashlib.sha256(corpus_path.read_bytes()).hexdigest() != sql['corpus_sha256']:
        raise ValueError('The frozen corpus changed.')
    fragments = {f['id']: dict(f, document=doc['id']) for doc in corpus['documents'] for f in doc['fragments']}
    cases = {c['id']: c for c in corpus['cases']}
    answers = {c['case_id']: c for c in chat['cases']}
    output = []
    for recorded in sql['cases']:
        case = cases[recorded['case_id']]
        relevant, authorized = set(case['gold']['relevant_fragment_ids']), set(case['gold']['authorized_fragment_ids'])
        result = dict(case_id=case['id'], category=case['category'], role=case['role'],
                      expected_fragment_ids=sorted(relevant),
                      expected_publications=recorded.get('expected_publications'), variants=[])
        observation = answers.get(case['id'])
        for variant in recorded['variants']:
            rows = [dict(r, text=fragments[r['fragment']]['text'], fragment_id=r['fragment'],
                         document_id=fragments[r['fragment']]['document']) for r in variant['candidates']]
            # Use the actual review's bounded topic query when present. For
            # followups the recorded pool is authoritative, not a guessed topic.
            preselected = preselect(rows, question=case['question'])
            ids = [r['fragment_id'] for r in rows]
            pre_ids = [r['fragment_id'] for r in preselected]
            after = dict(ranking=variant['ranking'], candidates=variant['candidates'],
                candidates_metrics={str(k): ranking_metrics(ids, relevant, k) for k in (3, 5, 20)},
                preselected_ids=pre_ids,
                preselection_rejections=[dict(fragment=f, reason='document_preselection_limit_or_unsafe') for f in ids if f not in pre_ids],
                preselection_metrics=ranking_metrics(pre_ids, relevant, 20),
                reviewer_ids=None, selection_rejections=[], k_variants={}, generator_ids=None,
                unauthorized_by_stage={'sql': sorted(set(ids)-authorized), 'preselection': sorted(set(pre_ids)-authorized)})
            if observation is not None and observation.get('target_executed', True):
                reviewer = observation.get('review_fragment_ids')
                selected = observation.get('selected_fragment_ids')
                rendered = observation.get('render_fragment_ids', selected)
                generated = observation.get('generator_fragment_ids')
                after.update(reviewer_ids=reviewer, selected_ids=selected, rendered_ids=rendered,
                             generator_ids=generated, generator_invoked=observation.get('generator_invoked'),
                             response_origin=observation.get('response_origin'),
                             actual_error_code=observation.get('error_code'), target_status=observation['status'])
                for stage, values in [('reviewer', reviewer), ('selected', selected), ('renderer', rendered), ('generator', generated)]:
                    after['unauthorized_by_stage'][stage] = None if values is None else sorted(set(values)-authorized)
                reviews = observation.get('document_reviews', [])
                after['plan_replay'] = 'unavailable_without_recorded_joint_plan'
                if reviews and set(reviews[-1]['decision']) == {'aspect', 'scope', 'relation', 'sources'}:
                    plan = reviews[-1]
                    mapping = {r['fragment_id']: r for r in rows}
                    review_ids = plan['fragment_ids']
                    if all(fid in mapping for fid in review_ids):
                        try:
                            verified, _, relation = verify_plan(json.dumps(plan['decision']), [mapping[fid] for fid in review_ids])
                            after['plan_replay'] = 'deterministic_source_identity_verified_not_semantic_certification'
                            after['relation'] = relation
                            kept = {r['fragment_id'] for r in verified}
                            after['selection_rejections'] = [dict(fragment=f, reason='joint_plan_not_responding') for f in review_ids if f not in kept]
                        except ValueError:
                            after['plan_replay'] = 'invalid_plan_operational_failure'
                # Actual backend assembly already expands complete procedures.
                # K3 must reject four required parts rather than quietly trim.
                for k in (3, 5):
                    final = selected if selected is not None and len(selected) <= k else []
                    reason = ('complete_selection_fits_cap' if selected is not None and len(selected) <= k else
                              'whole_evidence_exceeds_cap' if selected is not None else 'selection_not_completed')
                    after['k_variants'][str(k)] = dict(final_ids=final, reason=reason,
                        metrics=ranking_metrics(final, relevant, k),
                        experiment='same_recorded_plan_and_assembly_with_cap_not_new_qwen_run')
            result['variants'].append(after)
        output.append(result)
    return dict(scope='deterministic_layer_replay_without_model_or_database',
        corpus_sha256=sql['corpus_sha256'], selection_version=SELECTION_VERSION,
        qwen_calls=0, human_review_complete=False, holdout_executed=False, cases=output)


def retrieval_cases(settings, sessions, coordinator, state, corpus, cases, owned, journal, save):
    from app.services.leny_rag_common import QUERY_POLICY
    from app.services.leny_rag_retrieval import RetrievalService
    from app.services.leny_rag_routing import retrieval_question, question_with_topic
    from app.services.leny_store import LenyActor
    from app.services.leny_ollama import LenyError
    from run_leny_rag_quality import embed_corpus, case_scenario

    expected_docs = {f['id']: doc['id'] for doc in corpus['documents'] for f in doc['fragments']}
    for case in cases:
        cid = case['id']
        if journal.consumed(cid):
            raise RuntimeError('A layered diagnostic attempt cannot be silently replayed.')
        journal.append({'event': 'attempt', 'case_id': cid, 'request_id': str(uuid4())})
        if case['role'] not in owned['actors']:
            observation = dict(case_id=cid, target_executed=False, status='missing',
                               reason='isolated_preexisting_role_absent', variants=[], qwen_calls=0)
        else:
            original = owned['actors'][case['role']]
            actor = LenyActor(original['account'], original['user'], str(uuid4()))
            history = [{'role': 'user', 'content': q} for q in case['prior_user_questions']]
            question = retrieval_question(question_with_topic(case['question'], history))
            started = time.monotonic()
            vector = asyncio.run(embed_corpus(settings, coordinator, state,
                [QUERY_POLICY['template'].format(query=question)]))[0]
            embedding_seconds = time.monotonic()-started
            variants = []
            with case_scenario(sessions, owned, case) as apply:
                apply()
                for ranking in ('semantic', 'hybrid'):
                    config = settings.model_copy(update={'leny_rag_ranking': ranking})
                    retrieval = RetrievalService(config, sessions)
                    started = time.monotonic()
                    try:
                        rows = retrieval.search(actor, vector, question=question)
                        retrieval.revalidate(actor, rows)
                    except LenyError as error:
                        variants.append(dict(ranking=ranking, error_code=error.code, candidates=[],
                                             authorization='denied_before_content'))
                        continue
                    sql_seconds = time.monotonic()-started
                    candidates = []
                    for rank, row in enumerate(rows, 1):
                        fid = owned['fragment_ids'].get(str(row['fragment_id']), 'UNKNOWN')
                        candidates.append(dict(rank=rank, fragment=fid,
                            document=expected_docs.get(fid, 'UNKNOWN'),
                            document_id=str(row['document_id']), version=row['version'],
                            version_id=str(row['version_id']), indexation_id=str(row['indexation_id']),
                            fragment_id=str(row['fragment_id']), ordinal=row['ordinal'],
                            distance=float(row['distance']), rrf_score=float(row['rrf_score']) if 'rrf_score' in row else None))
                    ids = [r['fragment'] for r in candidates]
                    relevant = set(case['gold']['relevant_fragment_ids'])
                    variants.append(dict(ranking=ranking, candidates=candidates, sql_seconds=sql_seconds,
                        authorization='reader_and_sql_eligible_and_revalidation',
                        unauthorized_ids=sorted(set(ids)-set(case['gold']['authorized_fragment_ids'])),
                        metrics={str(k): ranking_metrics(ids, relevant, k) for k in (3, 5, 20)},
                        final_selection=None, generator_fragment_ids=[],
                        final_selection_reason='ranking_prefix_is_not_relevance_or_generation'))
            observation = dict(case_id=cid, target_executed=True, status='recorded', qwen_calls=0,
                embedding_seconds=embedding_seconds,
                query_vector_sha256=hashlib.sha256(json.dumps(vector).encode()).hexdigest(),
                routing='bypassed_for_stage_isolation', followup_scope='fresh_user_anchors_not_persisted_topic',
                expected_fragment_ids=case['gold']['relevant_fragment_ids'],
                expected_document_ids=sorted({expected_docs[f] for f in case['gold']['relevant_fragment_ids']}),
                expected_publications={name: owned['identities'][name] for name in
                    sorted({expected_docs[f] for f in case['gold']['relevant_fragment_ids']})},
                variants=variants)
        journal.append({'event': 'case', 'case_id': cid, 'observation': observation})
        save()
        print(json.dumps({'event': 'layered_sql_case', 'case_id': cid, 'status': observation['status']}), flush=True)


def sample_resources(output, stop):
    """Whole-system spot samples, never a continuous/model-exclusive peak."""
    import ctypes
    import subprocess
    from datetime import datetime, timezone
    from pathlib import Path
    class Memory(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong),
                    *[(name, ctypes.c_ulonglong) for name in
                      ('total', 'available', 'p1', 'p2', 'v1', 'v2', 'v3')]]
    path, stop = Path(output), Path(stop)
    if path.exists() or stop.exists():
        raise ValueError('Resource artifacts must use new filenames.')
    started, records = time.monotonic(), []
    while time.monotonic()-started < 3600 and not stop.exists():
        memory = Memory(); memory.length = ctypes.sizeof(memory)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
            raise RuntimeError('Memory measurement unavailable')
        sample = dict(timestamp_utc=datetime.now(timezone.utc).isoformat(),
                      available_ram_bytes=memory.available, total_ram_bytes=memory.total)
        gpu = subprocess.run(['C:/Windows/System32/nvidia-smi.exe',
            '--query-gpu=memory.used,memory.total,utilization.gpu', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5)
        if gpu.returncode == 0:
            used, total, util = (int(x.strip()) for x in gpu.stdout.strip().splitlines()[0].split(','))
            sample.update(gpu_used_mib=used, gpu_total_mib=total, gpu_utilization_percent=util)
        with path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(sample)+'\n')
        records.append(sample)
        time.sleep(5)
    summary = dict(scope='whole_system_spot_samples_not_continuous_peak_or_model_exclusive',
        sample_count=len(records), start_utc=records[0]['timestamp_utc'], end_utc=records[-1]['timestamp_utc'],
        minimum_observed_available_ram_bytes=min(r['available_ram_bytes'] for r in records),
        maximum_observed_gpu_used_mib=max((r.get('gpu_used_mib', 0) for r in records), default=0))
    path.with_suffix('.summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Resource sampling only; no application or database imports.')
    parser.add_argument('--output', required=True)
    parser.add_argument('--stop')
    parser.add_argument('--score-sql')
    parser.add_argument('--chat-observations')
    arguments = parser.parse_args()
    if arguments.score_sql:
        from pathlib import Path
        corpus_path = Path(__file__).resolve().parents[1]/'tests/fixtures/leny_rag04_development.json'
        load = lambda p: json.loads(Path(p).read_text(encoding='utf-8'))
        result = analyze_layers(load(corpus_path), load(arguments.score_sql), load(arguments.chat_observations))
        Path(arguments.output).write_text(json.dumps(result, ensure_ascii=True, indent=2)+'\n', encoding='utf-8')
    elif arguments.stop:
        sample_resources(arguments.output, arguments.stop)
    else:
        parser.error('Select resource sampling (--stop) or deterministic replay (--score-sql and --chat-observations).')
