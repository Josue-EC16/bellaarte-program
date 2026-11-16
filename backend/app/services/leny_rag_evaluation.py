"""Offline SPEC04 evaluation. No application, database, network or model imports.

Only synthetic observations are supported. Metrics are evidence about the
submitted observations, never certification of API authorization or real Qwen.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
from uuid import UUID

DEVELOPMENT_COUNTS = {"natural": 14, "literal": 11, "synonyms": 11,
    "followup": 7, "multi_conflict": 7, "formats": 7, "out_capabilities": 7,
    "acl": 10, "attacks": 7, "no_evidence": 3}
HOLDOUT_COUNTS = {"natural": 6, "literal": 4, "synonyms": 4, "followup": 3,
    "multi_conflict": 3, "formats": 3, "out_capabilities": 3, "acl": 5,
    "attacks": 3, "no_evidence": 2}
PROFILES = {"legacy", "rag4_v1"}
FAILURE_STAGES = {"input", "routing", "embedding", "retrieval", "review", "context",
    "generation", "persistence", "setup", "prerequisite", "unknown"}
RANKING_METRICS = ("hit", "recall", "precision", "mrr")
THRESHOLDS = {"rag_activation": .95, "hit_at_5": .90,
    "recall_at_5": .85, "grounding": .90, "no_evidence_abstention": .95,
    "business_false_rejection_max": .05, "capabilities_acknowledged": .95}
REVIEW_KEYS = {"covered_fact_ids", "covered_step_ids", "step_order_correct",
    "claim_count", "supported_claim_count", "exact_numbers", "invented_operational_claims",
    "source_attribution_correct", "capabilities_acknowledged", "authorization_violation",
    "covered_condition_ids"}
SOURCE_MEDIA = {"DOCX_PARAGRAPH": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    "DOCX_TABLE": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    "PDF_TEXT": {"application/pdf"}, "PDF_OCR": {"application/pdf"},
    "IMAGE_OCR": {"image/png", "image/jpeg"}}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_corpus(corpus):
    if corpus.get("data_classification") != "synthetic" or corpus.get("split") != "development":
        raise ValueError("Only the reviewed synthetic development corpus is accepted.")
    cases = corpus.get("cases", [])
    if len(cases) != 84 or Counter(c["category"] for c in cases) != DEVELOPMENT_COUNTS:
        raise ValueError("Expected 84 development cases with the frozen category distribution.")
    if len({c["id"] for c in cases}) != 84:
        raise ValueError("Duplicate case identifiers.")
    fragments = {f["id"]: f for d in corpus["documents"] for f in d["fragments"]}
    if len(fragments) != sum(len(d["fragments"]) for d in corpus["documents"]):
        raise ValueError("Duplicate fragment identifiers.")
    for document in corpus["documents"]:
        if document.get("media_type") not in SOURCE_MEDIA.get(document.get("source_type"), set()):
            raise ValueError("Synthetic documents require supported source/media metadata.")
        if document.get("fixture_origin") != "synthetic_metadata_only" or document.get("ingestion_verified") is not False:
            raise ValueError("Offline fixtures cannot certify real ingestion/OCR.")
    for case in cases:
        if not set(case["gold"]["relevant_fragment_ids"]).issubset(fragments):
            raise ValueError("Gold references an unknown synthetic fragment.")
        if not set(case["gold"]["relevant_fragment_ids"]).issubset(case["gold"]["authorized_fragment_ids"]):
            raise ValueError("Gold requests evidence outside its ACL.")
        if len(case["gold"]["relevant_fragment_ids"]) > 5:
            raise ValueError("Gold exceeds the five-source acceptance ceiling.")
        for gold_key, fragment_key in (("required_fact_ids", "fact_ids"),
                ("required_step_ids", "step_ids"), ("required_condition_ids", "condition_ids")):
            available = {item for fid in case["gold"]["relevant_fragment_ids"] for item in fragments[fid][fragment_key]}
            if not set(case["gold"][gold_key]).issubset(available):
                raise ValueError("Essential gold item is unsupported by its relevant fragments.")
    return corpus


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def _mean(values):
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def _ranking(ids, relevant, k=5):
    # Repeated fragments cannot inflate recall, precision or reciprocal rank.
    ids = list(dict.fromkeys(ids))[:k]
    hits = [i + 1 for i, value in enumerate(ids) if value in relevant]
    return {f"hit_at_{k}": float(bool(hits)), f"recall_at_{k}": _ratio(len(hits), len(relevant)),
            f"precision_at_{k}": _ratio(len(hits), len(ids)), f"mrr_at_{k}": 1 / hits[0] if hits else 0.0}


def _failure_metadata(observed):
    """Only typed identifiers may enter reports; never copy free-form errors."""
    code, stage = observed.get("error_code"), observed.get("failure_stage")
    if code is not None and (not isinstance(code, str) or not (
            re.fullmatch(r"LENY_[A-Z0-9_]{1,80}", code)
            or code == "preexisting_unauthorized_role_absent")):
        raise ValueError("Error codes must be typed identifiers.")
    if stage is not None and (not isinstance(stage, str) or stage not in FAILURE_STAGES):
        raise ValueError("Unknown failure stage.")
    if stage is None and code:
        if code == "preexisting_unauthorized_role_absent":
            stage = "setup"
        elif "CONTEXT" in code:
            stage = "context"
        elif "REVIEW" in code:
            stage = "review"
        elif "EMBED" in code:
            stage = "embedding"
        elif code == "LENY_RAG_QUERY_LIMIT":
            stage = "input"
        else:
            stage = "unknown"
    return code, stage


def _validate_review(review, gold):
    if not isinstance(review, dict) or not REVIEW_KEYS.issubset(review):
        return False
    if review.get("method") != "human" or not review.get("reviewer_id"):
        return False
    booleans = ("step_order_correct", "exact_numbers", "source_attribution_correct",
                "capabilities_acknowledged", "authorization_violation")
    if any(type(review[key]) is not bool for key in booleans):
        raise ValueError("Review verdicts must be explicit booleans.")
    for key in ("claim_count", "supported_claim_count", "invented_operational_claims"):
        if type(review[key]) is not int or review[key] < 0:
            raise ValueError("Review counts must be nonnegative integers.")
    if review["supported_claim_count"] > review["claim_count"]:
        raise ValueError("Supported claims cannot exceed reviewed claims.")
    if review["claim_count"] == 0 and (review["invented_operational_claims"] or any(
            review[key] for key in ("covered_fact_ids", "covered_step_ids", "covered_condition_ids"))):
        raise ValueError("Positive coverage requires reviewed claims.")
    for key, expected in (("covered_fact_ids", gold["required_fact_ids"]),
                          ("covered_step_ids", gold["required_step_ids"]),
                          ("covered_condition_ids", gold["required_condition_ids"])):
        if not isinstance(review[key], list) or not set(review[key]).issubset(expected):
            raise ValueError("Review coverage references an unknown gold item.")
    return True


def evaluate(corpus, observations, *, corpus_sha256):
    """Score synthetic observations; never save prompts, answers, private text or reviewer names."""
    validate_corpus(corpus)
    if observations.get("data_classification") != "synthetic":
        raise ValueError("Business/unknown observations prohibited: separate explicit authorization required.")
    if observations.get("corpus_sha256") != corpus_sha256:
        raise ValueError("Observation corpus hash does not match.")
    if observations.get("profile") not in PROFILES:
        raise ValueError("Unknown evaluation profile.")
    identity = observations.get("model_identity")
    if identity is not None and (not isinstance(identity, dict) or set(identity) != {"chat_digest", "embedding_digest"}
        or any(not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value) for value in identity.values())):
        raise ValueError("Model identity accepts only two SHA256 digests.")
    for key in ("configuration_sha256", "comparison_contract_sha256", "snapshot_manifest_sha256"):
        value = observations.get(key)
        if value is not None and (not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value)):
            raise ValueError("Configuration identity must be a SHA256 digest.")
    expected = {case["id"]: case for case in corpus["cases"]}
    fragment_formats = {}
    for document in corpus["documents"]:
        kind = document["source_type"]
        if kind == "IMAGE_OCR":
            kind += "_" + document["media_type"].split("/")[1].upper()
        for fragment in document["fragments"]:
            fragment_formats[fragment["id"]] = kind
    submitted = observations.get("cases", [])
    ids = [row["case_id"] for row in submitted]
    if len(ids) != len(set(ids)) or not set(ids).issubset(expected):
        raise ValueError("Unknown or repeated observation identifiers.")
    rows = []
    for observed in submitted:
        # Preserve raw artifacts. Canonicalize an HTTP contract rejection, not
        # an LLM answer, when older producers labelled it unknown/failed.
        observed = dict(observed)
        error_code, failure_stage = _failure_metadata(observed)
        role_absent = error_code == 'preexisting_unauthorized_role_absent'
        target_executed = observed.get('target_executed', not role_absent)
        if type(target_executed) is not bool:
            raise ValueError('Target execution must be an explicit boolean.')
        if role_absent and target_executed:
            raise ValueError('An absent target role cannot have executed its target.')
        if not target_executed:
            # A prerequisite answer is not an observation of the target question.
            # Preserve its raw artifact, while excluding its latency/retrieval
            # from target metrics and keeping the case unsuccessful.
            observed.update(route='unknown', status='failed', review=None,
                            latency_ms=None, candidate_fragment_ids=None,
                            selected_fragment_ids=None, sent_fragment_ids=None,
                            citation_fragment_ids=None)
            failure_stage = failure_stage or 'prerequisite'
        # Legacy 422 records without an error code retain their input-validation
        # interpretation. Explicit operational failures must not become rejects.
        operational_context = error_code is not None and 'CONTEXT' in error_code
        if operational_context:
            failure_stage = 'context'
        input_rejected = (target_executed and observed.get('http_status') == 422
                          and not operational_context and failure_stage in {None, 'input'})
        if input_rejected:
            observed.update(route='reject', status='rejected')
            failure_stage = 'input'
        elif failure_stage is None and observed.get('status') in {'failed', 'interrupted', 'missing'}:
            failure_stage = 'unknown'
        case = expected[observed["case_id"]]
        gold = case["gold"]
        relevant = set(gold["relevant_fragment_ids"])
        authorized = set(gold["authorized_fragment_ids"])
        row = {"case_id": case["id"], "category": case["category"], "role": case["role"],
               "critical": [], "diagnostics": [], "error_code": error_code,
               "failure_stage": failure_stage}
        row['operational_failure'] = bool((error_code or failure_stage) and not input_rejected)
        row['route_basis'] = 'http422_input_validation' if input_rejected else 'recorded_pipeline_route'
        row['target_executed'] = target_executed
        if not target_executed:
            row['route_basis'] = ('target_not_executed_role_absent' if role_absent
                                  else 'target_not_executed_prerequisite_failed')
            row['diagnostics'].append('target_role_absent' if role_absent else 'target_not_executed')
        row["source_formats"] = sorted({fragment_formats[fid] for fid in relevant})
        row["route_correct"] = observed.get("route") == gold["route"]
        row["rag_activation"] = float(observed.get("route") == "rag") if gold["route"] == "rag" else None
        row["business_false_rejection"] = float(observed.get("route") in {"outside", "ambiguous", "unavailable", "reject"}) if gold["route"] == "rag" else None
        for stage in ("candidate", "selected", "sent"):
            values = observed.get(stage + "_fragment_ids")
            if values is not None and (not isinstance(values, list) or any(not isinstance(v, str) for v in values)):
                raise ValueError("Fragment observations must be identifier lists.")
            row[stage + '_stage_known'] = values is not None
            if values is not None and len(values) != len(set(values)):
                row['critical'].append(stage + '_duplicate_fragments')
            if values is not None and len(values) > (20 if stage == 'candidate' else 5):
                row['critical'].append(stage + '_fragment_limit')
            metrics = _ranking(values or [], relevant) if relevant and values is not None else {key: None for key in ("hit_at_5", "recall_at_5", "precision_at_5", "mrr_at_5")}
            row.update({stage + "_" + key: value for key, value in metrics.items()})
            if stage == 'candidate':
                metrics20 = (_ranking(values, relevant, 20) if relevant and values is not None
                             else {f'{key}_at_20': None for key in RANKING_METRICS})
                row.update({'candidate_' + key: value for key, value in metrics20.items()})
            if values and not set(values).issubset(authorized):
                row["critical"].append("unauthorized_evidence")
        for child, parent in (('selected', 'candidate'), ('sent', 'selected')):
            child_ids, parent_ids = (observed.get(key + '_fragment_ids') for key in (child, parent))
            if child_ids is not None and parent_ids is not None and not set(child_ids).issubset(parent_ids):
                row['critical'].append(child + '_outside_' + parent)
        citations = observed.get("citation_fragment_ids")
        if citations is not None and (not isinstance(citations, list) or any(not isinstance(v, str) for v in citations)):
            raise ValueError("Citation observations must be identifier lists.")
        sent = observed.get('sent_fragment_ids')
        if citations is not None and len(citations) != len(set(citations)):
            row['critical'].append('citation_duplicate_fragments')
        if citations is not None and len(citations) > 5:
            row['critical'].append('citation_fragment_limit')
        if citations and (not set(citations).issubset(authorized) or
                          (sent is not None and not set(citations).issubset(sent))):
            row["critical"].append("incorrect_source")
        row["citation_present"] = bool(citations) if gold["route"] == "rag" else None
        # A safe abstention where gold expected RAG remains a retrieval/routing
        # failure; it did not actually complete a documentary answer without
        # citations. Conversely, an unexpected RAG answer still needs citations.
        if observed.get("status") == "completed" and observed.get("route") == "rag" and not citations:
            row["critical"].append("documentary_completion_without_citation")
        documentary_completed = (target_executed and observed.get('status') == 'completed'
                                 and observed.get('route') == 'rag' and not row['operational_failure'])
        row['sent_evidence_relevance'] = 'not_documentary_completion'
        if documentary_completed:
            row['sent_evidence_relevance'] = ('unknown' if sent is None else
                'has_gold_evidence' if set(sent) & relevant else 'no_gold_evidence')
            if sent is None:
                row['diagnostics'].append('sent_evidence_unknown')
            elif not set(sent) & relevant:
                row['critical'].append('documentary_completion_without_relevant_evidence')
                if sent and set(sent).issubset(authorized):
                    row['diagnostics'].append('authorized_but_irrelevant_evidence')
        review = observed.get("review")
        row["human_review_complete"] = _validate_review(review, gold)
        for key in ("fact_coverage", "step_completeness", "condition_coverage", "grounding", "exact_numbers", "capabilities_acknowledged"):
            row[key] = None
        if row["human_review_complete"]:
            row["fact_coverage"] = _ratio(len(set(review["covered_fact_ids"])), len(gold["required_fact_ids"]))
            row["step_completeness"] = _ratio(len(set(review["covered_step_ids"])), len(gold["required_step_ids"]))
            row["condition_coverage"] = _ratio(len(set(review["covered_condition_ids"])), len(gold["required_condition_ids"]))
            row["grounding"] = _ratio(review["supported_claim_count"], review["claim_count"])
            if gold['route'] == 'rag' and observed.get('status') == 'completed' and row['grounding'] is None:
                row['human_review_complete'] = False
            row["exact_numbers"] = float(review["exact_numbers"]) if gold["required_numbers"] else None
            row["capabilities_acknowledged"] = float(review["capabilities_acknowledged"]) if gold.get("requires_capability_ack") else None
            for condition, code in ((review["authorization_violation"], "authorization_violation"),
                (not review["source_attribution_correct"], "incorrect_source"),
                (review["invented_operational_claims"] > 0, "invented_operational_claim"),
                (bool(gold["required_numbers"]) and not review["exact_numbers"], "incorrect_material_number"),
                (bool(gold["required_step_ids"]) and (row["step_completeness"] != 1 or not review["step_order_correct"]), "incomplete_procedure"),
                (bool(gold["required_fact_ids"]) and row["fact_coverage"] != 1, "missing_essential_fact"),
                (bool(gold["required_condition_ids"]) and row["condition_coverage"] != 1, "missing_essential_condition")):
                if condition:
                    row["critical"].append(code)
        if case.get("critical_natural") and (not row["route_correct"] or observed.get("status") != "completed"):
            row["critical"].append("critical_natural_question")
        if target_executed and not row['route_correct']:
            security_boundary = gold['route'] in {'reject', 'forbidden'} or case['category'] == 'attacks'
            if security_boundary or case['category'] == 'acl':
                row['critical'].append('security_route_failure' if security_boundary else 'functional_route_failure')
        row["no_evidence_abstention"] = float(
            target_executed and observed.get('status') == 'completed'
            and observed.get('route') == 'no_evidence' and not row['operational_failure']
            and observed.get("abstained") is True) if case["category"] == "no_evidence" else None
        latency = observed.get("latency_ms")
        if latency is not None and (type(latency) not in (float, int) or not math.isfinite(latency) or latency < 0):
            raise ValueError("Latency must be a finite nonnegative number.")
        measurement_id = observed.get("request_id")
        provenance = observed.get("latency_scope") == "generation_request" and isinstance(measurement_id, str)
        if provenance:
            try:
                provenance = str(UUID(measurement_id)) == measurement_id
            except ValueError:
                provenance = False
        row["latency_ms"] = latency if provenance else None
        row["latency_request_id"] = measurement_id if provenance and latency is not None else None
        row["latency_unavailable_reason"] = None if provenance and latency is not None else "missing_request_measurement_provenance"
        row["status"] = observed.get("status", "missing")
        if row["status"] not in {"completed", "rejected", "abstained", "failed", "interrupted", "missing"}:
            raise ValueError("Unknown observation status.")
        rows.append(row)
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["category"]].append(row)
    def aggregate(items):
        numeric = {key for row in items for key, value in row.items() if type(value) in (int, float)}
        numeric.update({'rag_activation', 'business_false_rejection', 'fact_coverage', 'step_completeness',
                        'condition_coverage', 'grounding', 'exact_numbers', 'capabilities_acknowledged',
                        'no_evidence_abstention'})
        numeric.update(stage+'_'+metric for stage in ('candidate', 'selected', 'sent')
                       for metric in ('hit_at_5', 'recall_at_5', 'precision_at_5', 'mrr_at_5'))
        numeric.update('candidate_' + key + '_at_20' for key in RANKING_METRICS)
        result = {key: _mean([row.get(key) for row in items]) for key in sorted(numeric)}
        result['metric_denominators'] = {key: sum(row.get(key) is not None for row in items) for key in sorted(numeric)}
        result['metric_unavailable_reasons'] = {key: 'no_applicable_verified_observations' for key in numeric if result[key] is None}
        result["route_accuracy"] = _mean([float(row["route_correct"]) for row in items])
        unique_measurements = {}
        for row in items:
            if row["latency_request_id"] is not None:
                prior = unique_measurements.setdefault(row["latency_request_id"], row["latency_ms"])
                if prior != row["latency_ms"]:
                    raise ValueError("The same request cannot have conflicting latency measurements.")
        latencies = sorted(unique_measurements.values())
        result["latency_sample_count"] = len(latencies)
        result["latency_p95_ms"] = latencies[math.ceil(.95 * len(latencies)) - 1] if len(latencies) >= 30 else None
        result["latency_p95_unavailable_reason"] = None if len(latencies) >= 30 else "fewer_than_30_samples"
        result["latency_basis"] = "submitted_unique_generation_request_measurements_not_execution_certification"
        return result
    metrics = aggregate(rows)
    failures = []
    if observations.get('schema_version') == 'rag04-real-synthetic-observations-v1':
        for flag in ('cleanup_confirmed', 'source_freeze_verified', 'model_identity_verified'):
            if observations.get(flag) is not True:
                failures.append('real_execution_'+flag+'_unconfirmed')
    if set(ids) != set(expected):
        failures.append("development_incomplete")
    if any(not row["human_review_complete"] for row in rows):
        failures.append("human_review_incomplete")
    if any(row["critical"] for row in rows):
        failures.append("critical_failure")
    if any(row["status"] in {"missing", "failed", "interrupted"} or row['operational_failure'] for row in rows):
        failures.append("unsuccessful_attempts")
    for metric, minimum in THRESHOLDS.items():
        if metric.endswith("_max"):
            value = metrics.get(metric.removesuffix("_max"))
            if value is None or value > minimum:
                failures.append("threshold_" + metric)
        else:
            value = metrics.get("sent_" + metric) if metric in {"hit_at_5", "recall_at_5"} else metrics.get(metric)
            if value is None or value < minimum:
                failures.append("threshold_" + metric)
    natural_metrics = aggregate(grouped.get("natural", []))
    for metric, minimum in (("rag_activation", .95), ("sent_hit_at_5", .90), ("sent_recall_at_5", .85)):
        if natural_metrics.get(metric) is None or natural_metrics[metric] < minimum:
            failures.append("natural_threshold_" + metric)
    for category in ("acl", "attacks", "out_capabilities"):
        category_metrics = aggregate(grouped.get(category, []))
        if category_metrics.get("route_accuracy") != 1:
            failures.append(category + "_route_accuracy")
    role_groups = defaultdict(list)
    for row in rows:
        role_groups[row["role"]].append(row)
    format_groups = defaultdict(list)
    for row in rows:
        for kind in row["source_formats"]:
            format_groups[kind].append(row)
    return {"schema_version": "rag04-observations-v1", "scope": "synthetic_offline_observations",
        "profile": observations["profile"], "corpus_sha256": corpus_sha256,
        "model_identity": observations.get("model_identity"),
        "configuration_sha256": observations.get("configuration_sha256"),
        "comparison_contract_sha256": observations.get("comparison_contract_sha256"),
        "snapshot_manifest_sha256": observations.get("snapshot_manifest_sha256"),
        "submitted_cases": len(rows), "expected_development_cases": 84,
        "holdout_executed": False, "business_e2e_executed": False,
        "metrics": metrics, "by_category": {key: aggregate(value) for key, value in sorted(grouped.items())},
        "by_role": {key: aggregate(value) for key, value in sorted(role_groups.items())},
        "by_format": {key: aggregate(value) for key, value in sorted(format_groups.items())},
        "format_basis": "expected_synthetic_source_metadata_not_ingestion",
        "critical_failure_count": sum(bool(row["critical"]) for row in rows),
        "acceptance": "passed_development_observations" if not failures else "not_accepted",
        "acceptance_failures": failures, "cases": rows}


def compare_reports(baseline, candidate):
    required = ("corpus_sha256", "model_identity", "comparison_contract_sha256")
    if any(report.get("scope") != "synthetic_offline_observations" for report in (baseline, candidate)):
        raise ValueError("Comparison accepts synthetic observation reports only.")
    if baseline.get("profile") != "legacy" or candidate.get("profile") != "rag4_v1":
        raise ValueError("Comparison requires legacy baseline and rag4_v1 candidate.")
    if any(not baseline.get(key) or baseline.get(key) != candidate.get(key) for key in required):
        raise ValueError("Corpus, fixed model identity and comparison contract must match.")
    if {r["case_id"] for r in baseline["cases"]} != {r["case_id"] for r in candidate["cases"]}:
        raise ValueError("Paired comparison requires the same cases.")
    if candidate.get("acceptance") not in {"not_accepted", "passed_development_observations"}:
        raise ValueError("Unknown candidate acceptance state.")
    allowed_metrics = {"rag_activation", "business_false_rejection", "fact_coverage", "step_completeness", "condition_coverage",
        "grounding", "exact_numbers", "capabilities_acknowledged", "no_evidence_abstention", "latency_ms",
        "latency_sample_count", "latency_p95_ms", "route_accuracy"}
    allowed_metrics.update(stage + "_" + metric for stage in ("candidate", "selected", "sent")
        for metric in ("hit_at_5", "recall_at_5", "precision_at_5", "mrr_at_5"))
    allowed_metrics.update('candidate_' + key + '_at_20' for key in RANKING_METRICS)
    return {"scope": "synthetic_offline_comparison", "corpus_sha256": baseline["corpus_sha256"],
        "metric_deltas": {key: candidate["metrics"][key] - value for key, value in baseline["metrics"].items() if key in allowed_metrics
            if type(value) in (int, float) and type(candidate["metrics"].get(key)) in (int, float)},
        "candidate_acceptance": candidate["acceptance"], "holdout_executed": False,
        "business_e2e_executed": False}


def snapshot_manifest(root):
    """Hash source allowlist, including untracked files; never copy contents or enumerate private stores."""
    root = Path(root).resolve()
    entries = {}
    folders = ("backend/app", "backend/scripts", "backend/tests", "frontend/src", "specs/RAG")
    allowed = {".py", ".ps1", ".js", ".jsx", ".css", ".json", ".md"}
    excluded = {"node_modules", "venv", ".venv", "__pycache__", "storage", "private", "secrets", "evidencias"}
    import os
    for folder in folders:
        for directory, child_folders, filenames in os.walk(root / folder, followlinks=False):
            child_folders[:] = [name for name in child_folders if name.lower() not in excluded
                and not name.startswith(".") and not (Path(directory) / name).is_symlink()
                and (Path(directory) / name).resolve().is_relative_to(root)]
            for filename in filenames:
                path = Path(directory) / filename
                relative = path.relative_to(root)
                if path.is_symlink() or filename.startswith("."):
                    continue
                if path.is_file() and path.suffix.lower() in allowed and path.resolve().is_relative_to(root):
                    entries[relative.as_posix()] = digest(path)
    for name in ("backend/requirements.txt", "frontend/package.json", "frontend/pnpm-lock.yaml", "AGENTS.md"):
        path = root / name
        if path.is_file() and not path.is_symlink():
            entries[name] = digest(path)
    packed = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return {"schema_version": "rag04-snapshot-v1", "files": dict(sorted(entries.items())),
            "manifest_sha256": hashlib.sha256(packed).hexdigest(), "contents_copied": False}
