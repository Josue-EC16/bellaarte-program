"""Pure offline evaluation contracts; never import the application or persistence."""
import json
from pathlib import Path
from uuid import UUID

import pytest

from app.services.leny_rag_evaluation import (DEVELOPMENT_COUNTS, HOLDOUT_COUNTS,
    compare_reports, digest, evaluate, snapshot_manifest, validate_corpus)

CORPUS = Path(__file__).parent / "fixtures/leny_rag04_development.json"


def corpus():
    return json.loads(CORPUS.read_text(encoding="utf-8"))


def observations():
    rows = []
    for index, case in enumerate(corpus()["cases"]):
        gold = case["gold"]
        rows.append({"case_id": case["id"], "route": gold["route"],
            "status": "completed", "latency_ms": 12.5,
            "request_id": str(UUID(int=index + 1)), "latency_scope": "generation_request",
            "candidate_fragment_ids": gold["relevant_fragment_ids"],
            "selected_fragment_ids": gold["relevant_fragment_ids"],
            "sent_fragment_ids": gold["relevant_fragment_ids"],
            "citation_fragment_ids": gold["relevant_fragment_ids"],
            "abstained": gold["route"] == "no_evidence",
            "review": {"method": "human", "reviewer_id": "synthetic-test-reviewer",
                "covered_fact_ids": gold["required_fact_ids"],
                "covered_condition_ids": gold["required_condition_ids"],
                "covered_step_ids": gold["required_step_ids"], "step_order_correct": True,
                "claim_count": 1, "supported_claim_count": 1, "exact_numbers": True,
                "invented_operational_claims": 0, "source_attribution_correct": True,
                "capabilities_acknowledged": True, "authorization_violation": False}})
    return {"data_classification": "synthetic", "profile": "rag4_v1",
        "corpus_sha256": digest(CORPUS),
        "model_identity": {"chat_digest": "a" * 64, "embedding_digest": "b" * 64},
        "configuration_sha256": "c" * 64, "comparison_contract_sha256": "e" * 64, "cases": rows}


def score(value=None):
    return evaluate(corpus(), value or observations(), corpus_sha256=digest(CORPUS))


def test_frozen_distribution_and_reserved_manifest_are_honest():
    value = validate_corpus(corpus())
    assert len(value["cases"]) == sum(DEVELOPMENT_COUNTS.values()) == 84
    manifest = json.loads(CORPUS.with_name("leny_rag04_holdout_manifest.json").read_text())
    assert manifest["category_counts"] == HOLDOUT_COUNTS
    assert sum(HOLDOUT_COUNTS.values()) == 36
    assert manifest["status"] == "pending_independent_custodian"
    assert not manifest["cases_included"] and not manifest["executed"]


def test_complete_synthetic_observations_do_not_claim_actual_execution():
    result = score()
    assert result["acceptance"] == "passed_development_observations"
    assert result["metrics"]["sent_recall_at_5"] == 1
    assert result["metrics"]["latency_p95_ms"] == 12.5
    assert result["scope"] == "synthetic_offline_observations"
    assert not result["business_e2e_executed"] and not result["holdout_executed"]
    assert len(result["by_category"]) == 10
    assert "MODISTA" in result["by_role"]


@pytest.mark.parametrize("classification", [None, "business", "real", "unknown"])
def test_business_or_unclassified_observations_fail_closed(classification):
    value = observations()
    value["data_classification"] = classification
    with pytest.raises(ValueError, match="authorization"):
        score(value)


def test_wrong_corpus_hash_and_duplicate_requests_are_rejected():
    value = observations()
    value["corpus_sha256"] = "wrong"
    with pytest.raises(ValueError, match="hash"):
        score(value)
    value = observations()
    value["cases"].append(value["cases"][0])
    with pytest.raises(ValueError, match="repeated"):
        score(value)


def test_missing_review_is_missing_not_a_semantic_success():
    value = observations()
    value["cases"][0].pop("review")
    result = score(value)
    assert result["cases"][0]["grounding"] is None
    assert "human_review_incomplete" in result["acceptance_failures"]


@pytest.mark.parametrize("field,new_value,code", [
    ("invented_operational_claims", 1, "invented_operational_claim"),
    ("authorization_violation", True, "authorization_violation"),
    ("source_attribution_correct", False, "incorrect_source"),
    ("covered_step_ids", ["step-1"], "incomplete_procedure"),
    ("step_order_correct", False, "incomplete_procedure"),
    ("covered_fact_ids", [], "missing_essential_fact"),
    ("covered_condition_ids", [], "missing_essential_condition")])
def test_zero_critical_gate_cannot_be_averaged_away(field, new_value, code):
    value = observations()
    value["cases"][0]["review"][field] = new_value
    result = score(value)
    assert code in result["cases"][0]["critical"]
    assert result["acceptance"] == "not_accepted"


def test_incorrect_material_number_is_critical():
    value = observations()
    target = next(row for row in value["cases"] if "price-1" in row["sent_fragment_ids"])
    target["review"]["exact_numbers"] = False
    result = score(value)
    assert any("incorrect_material_number" in row["critical"] for row in result["cases"])


def test_current_acl_and_citation_identity_are_checked_independently():
    value = observations()
    target = next(row for row in value["cases"] if row["case_id"] == "rag04-acl-02")
    target["sent_fragment_ids"] = ["price-1"]
    target["citation_fragment_ids"] = ["invented-fragment"]
    result = score(value)
    row = next(row for row in result["cases"] if row["case_id"] == target["case_id"])
    assert set(row["critical"]) >= {"unauthorized_evidence", "incorrect_source"}


def test_empty_citations_cannot_complete_documentary_response():
    value = observations()
    value["cases"][0]["citation_fragment_ids"] = []
    assert "documentary_completion_without_citation" in score(value)["cases"][0]["critical"]


def test_abstention_remains_a_failed_natural_answer_without_being_mislabeled_as_citation_failure():
    value = observations()
    value['cases'][0].update(route='no_evidence', citation_fragment_ids=[],
                             sent_fragment_ids=[], abstained=True, review=None)
    result = score(value)
    row = result['cases'][0]
    assert not row['route_correct'] and row['sent_hit_at_5'] == 0
    assert 'critical_natural_question' in row['critical']
    assert 'documentary_completion_without_citation' not in row['critical']
    assert result['acceptance'] == 'not_accepted'


def test_unexpected_documentary_completion_still_requires_citations():
    value = observations()
    target = next(row for row in value['cases'] if row['case_id'] == 'rag04-no_evidence-03')
    target.update(route='rag', citation_fragment_ids=[], review=None)
    result = score(value)
    row = next(row for row in result['cases'] if row['case_id'] == target['case_id'])
    assert not row['route_correct']
    assert 'documentary_completion_without_citation' in row['critical']
    assert result['acceptance'] == 'not_accepted'


def test_duplicates_do_not_inflate_recall_and_missing_latency_is_not_zero():
    value = observations()
    value["cases"] = value["cases"][:1]
    value["cases"][0]["sent_fragment_ids"] = ["proc-1"] * 5
    value["cases"][0].pop("latency_ms")
    result = score(value)
    assert result["cases"][0]["sent_recall_at_5"] == .25
    assert 'sent_duplicate_fragments' in result['cases'][0]['critical']
    assert result['acceptance'] == 'not_accepted'
    assert result["metrics"]["latency_sample_count"] == 0
    assert result["metrics"]["latency_p95_ms"] is None
    assert result["metrics"]["latency_p95_unavailable_reason"] == "fewer_than_30_samples"


def test_failed_or_interrupted_attempts_are_not_silently_removed():
    value = observations()
    value["cases"][-1]["status"] = "interrupted"
    assert "unsuccessful_attempts" in score(value)["acceptance_failures"]


def test_reports_never_copy_input_text_or_reviewer_identity():
    value = observations()
    value["cases"][0]["answer"] = "DO-NOT-PERSIST-ANSWER"
    value["cases"][0]["question"] = "DO-NOT-PERSIST-QUESTION"
    value["cases"][0]["review"]["reviewer_id"] = "DO-NOT-PERSIST-REVIEWER"
    encoded = json.dumps(score(value))
    assert "DO-NOT-PERSIST" not in encoded


def test_arbitrary_metadata_cannot_smuggle_text_to_report():
    value = observations()
    value["model_identity"] = {"secret": "private"}
    with pytest.raises(ValueError, match="digests"):
        score(value)


def test_paired_comparison_requires_frozen_identity():
    candidate = score()
    value = observations()
    value["profile"] = "legacy"
    baseline = score(value)
    assert compare_reports(baseline, candidate)["metric_deltas"]["sent_recall_at_5"] == 0
    candidate["comparison_contract_sha256"] = "d" * 64
    with pytest.raises(ValueError, match="must match"):
        compare_reports(baseline, candidate)


def test_snapshot_includes_untracked_source_but_excludes_secrets_and_content(tmp_path):
    folder = tmp_path / "backend/app"
    folder.mkdir(parents=True)
    (folder / "new.py").write_text("private contents are never copied")
    (folder / ".env").write_text("SECRET=value")
    (folder / "storage").mkdir()
    (folder / "storage/private.py").write_text("not included")
    result = snapshot_manifest(tmp_path)
    assert set(result["files"]) == {"backend/app/new.py"}
    assert not result["contents_copied"]
    assert "private contents" not in json.dumps(result)


def test_review_cannot_claim_unknown_gold_steps():
    value = observations()
    value["cases"][0]["review"]["covered_step_ids"] = ["invented-step"]
    with pytest.raises(ValueError, match="unknown gold"):
        score(value)


def test_focused_questions_only_require_the_requested_phase():
    cases = {case["id"]: case for case in corpus()["cases"]}
    for i in range(1, 11):
        assert len(cases[f"rag04-natural-{i:02d}"]["gold"]["required_step_ids"]) == 9
    assert cases["rag04-natural-11"]["gold"]["relevant_fragment_ids"] == ["proc-1"]
    assert cases["rag04-natural-13"]["gold"]["required_step_ids"] == ["step-6"]
    gold = cases["rag04-natural-14"]["gold"]
    assert gold["required_fact_ids"] == ["quality"]
    assert gold["required_step_ids"] == ["step-8"]
    assert not gold["required_condition_ids"]
    assert cases["rag04-literal-04"]["gold"]["required_numbers"] == ["250.00"]
    assert cases["rag04-literal-05"]["gold"]["required_numbers"] == ["40%"]
    assert cases["rag04-synonyms-05"]["gold"]["required_step_ids"] == ["step-3"]
    assert cases["rag04-followup-01"]["gold"]["required_step_ids"] == ["step-3"]
    assert len(cases["rag04-followup-03"]["gold"]["required_step_ids"]) == 9


def test_extra_approval_condition_is_not_required_and_inventing_it_is_not_accepted():
    value = observations()
    quality = next(row for row in value["cases"] if row["case_id"] == "rag04-natural-14")
    assert quality["review"]["covered_condition_ids"] == []
    assert score(value)["acceptance"] == "passed_development_observations"
    # Reviewer observes an invented approval prerequisite for quality inspection.
    quality["review"]["invented_operational_claims"] = 1
    result = score(value)
    quality_row = next(row for row in result["cases"] if row["case_id"] == quality["case_id"])
    assert "invented_operational_claim" in quality_row["critical"]
    assert result["acceptance"] == "not_accepted"


def test_by_format_is_synthetic_metadata_not_real_ingestion_evidence():
    result = score()
    assert set(result["by_format"]) == {"DOCX_PARAGRAPH", "DOCX_TABLE", "PDF_TEXT",
        "PDF_OCR", "IMAGE_OCR_PNG", "IMAGE_OCR_JPEG"}
    assert result["format_basis"] == "expected_synthetic_source_metadata_not_ingestion"
    for document in corpus()["documents"]:
        assert document["fixture_origin"] == "synthetic_metadata_only"
        assert document["ingestion_verified"] is False
    assert result["by_format"]["IMAGE_OCR_PNG"]["sent_hit_at_5"] == 1


@pytest.mark.parametrize("case_id", ["rag04-acl-01", "rag04-acl-02", "rag04-attacks-01",
    "rag04-out_capabilities-07", "rag04-out_capabilities-01"])
def test_category_gates_do_not_accept_rejecting_everything_or_allowing_everything(case_id):
    value = observations()
    target = next(row for row in value["cases"] if row["case_id"] == case_id)
    target["route"] = "general" if target["route"] in {"reject", "outside"} else "reject"
    result = score(value)
    assert result["acceptance"] == "not_accepted"
    category = next(row for row in result["cases"] if row["case_id"] == case_id)["category"]
    assert category + "_route_accuracy" in result["acceptance_failures"]
    if category in {"acl", "attacks"}:
        expected = 'security_route_failure' if category == 'attacks' else 'functional_route_failure'
        assert expected in next(row for row in result['cases'] if row['case_id'] == case_id)['critical']


def test_latency_requires_30_distinct_request_measurements_not_turn_or_case_counts():
    value = observations()
    for row in value["cases"]:
        row["request_id"] = str(UUID(int=1))
        row["turn_count"] = 30
    result = score(value)
    assert result["submitted_cases"] == 84
    assert result["metrics"]["latency_sample_count"] == 1
    assert result["metrics"]["latency_p95_ms"] is None
    value = observations()
    for row in value["cases"][29:]:
        row.pop("request_id")
    assert score(value)["metrics"]["latency_p95_ms"] is None
    value["cases"][29]["request_id"] = str(UUID(int=30))
    assert score(value)["metrics"]["latency_sample_count"] == 30
    assert score(value)["metrics"]["latency_p95_ms"] == 12.5


def test_gold_cannot_require_unsupported_conditions():
    value = corpus()
    value["cases"][0]["gold"]["required_condition_ids"].append("invented-approval")
    with pytest.raises(ValueError, match="unsupported"):
        validate_corpus(value)


def test_semantic_families_are_shared_inside_development_not_falsely_independent():
    cases = {case["id"]: case for case in corpus()["cases"]}
    assert cases["rag04-natural-14"]["family_id"] == cases["rag04-synonyms-08"]["family_id"]
    assert cases["rag04-natural-01"]["family_id"] == cases["rag04-formats-01"]["family_id"]


def test_input_validation_rejection_is_not_mislabeled_as_model_attack_success():
    value = observations()
    observed = next(row for row in value['cases'] if row['case_id'] == 'rag04-attacks-04')
    observed.update(http_status=422, route='unknown', status='failed')
    result = score(value)
    case = next(row for row in result['cases'] if row['case_id'] == 'rag04-attacks-04')
    assert case['route_correct'] and case['status'] == 'rejected'
    assert case['route_basis'] == 'http422_input_validation'
    assert observed['route'] == 'unknown'  # The original first attempt is not rewritten.


def test_positive_semantic_coverage_with_zero_reviewed_claims_is_invalid():
    value = observations()
    value['cases'][0]['review'].update(claim_count=0, supported_claim_count=0)
    with pytest.raises(ValueError, match='coverage requires reviewed claims'):
        score(value)


def test_documentary_answer_with_no_reviewed_claims_cannot_disappear_from_gate():
    value = observations()
    review = value['cases'][0]['review']
    review.update(claim_count=0, supported_claim_count=0, covered_fact_ids=[],
                  covered_step_ids=[], covered_condition_ids=[])
    result = score(value)
    assert not result['cases'][0]['human_review_complete']
    assert 'human_review_incomplete' in result['acceptance_failures']


def test_prerequisite_answer_is_not_scored_as_target_followup_or_target_latency():
    value = observations()
    target = next(row for row in value['cases'] if row['case_id'] == 'rag04-followup-01')
    target.update(target_executed=False, http_status=422)
    result = score(value)
    row = next(row for row in result['cases'] if row['case_id'] == target['case_id'])
    assert row['status'] == 'failed' and not row['route_correct']
    assert row['route_basis'] == 'target_not_executed_prerequisite_failed'
    assert row['sent_recall_at_5'] is None and row['latency_ms'] is None
    assert not row['human_review_complete']
    assert result['acceptance'] == 'not_accepted'


def test_real_producer_requires_explicit_cleanup_and_freeze_evidence():
    value = observations()
    value['schema_version'] = 'rag04-real-synthetic-observations-v1'
    result = score(value)
    assert 'real_execution_source_freeze_verified_unconfirmed' in result['acceptance_failures']
    value.update(cleanup_confirmed=True, source_freeze_verified=True, model_identity_verified=True)
    assert score(value)['acceptance'] == 'passed_development_observations'


def test_candidates_beyond_top_five_can_supply_the_final_documentary_answer():
    value = observations()
    target = next(row for row in value['cases'] if row['case_id'] == 'rag04-formats-05')
    target['candidate_fragment_ids'] = ['proc-1', 'proc-2', 'proc-3', 'proc-4', 'work-1', 'price-1']
    result = score(value)
    row = next(row for row in result['cases'] if row['case_id'] == target['case_id'])
    assert row['candidate_hit_at_5'] == row['candidate_recall_at_5'] == 0
    assert row['candidate_hit_at_20'] == row['candidate_recall_at_20'] == 1
    assert row['candidate_mrr_at_20'] == pytest.approx(1 / 6)
    assert row['sent_hit_at_5'] == 1 and not row['critical']
    assert result['metrics']['metric_denominators']['candidate_hit_at_20'] == 61
    assert result['acceptance'] == 'passed_development_observations'
    baseline_value = observations()
    baseline_value['profile'] = 'legacy'
    assert compare_reports(score(baseline_value), result)['metric_deltas']['candidate_hit_at_20'] == 0


@pytest.mark.parametrize('stage', ['candidate', 'selected', 'sent', 'citation'])
def test_duplicate_fragment_observations_are_critical_in_every_stage(stage):
    value = observations()
    row = next(row for row in value['cases'] if row['case_id'] == 'rag04-formats-05')
    row[stage + '_fragment_ids'] = ['price-1', 'price-1']
    result = score(value)
    scored = next(item for item in result['cases'] if item['case_id'] == row['case_id'])
    assert stage + '_duplicate_fragments' in scored['critical']
    assert result['acceptance'] == 'not_accepted'


@pytest.mark.parametrize('stage,limit', [('candidate', 20), ('selected', 5), ('sent', 5), ('citation', 5)])
def test_source_stage_limits_fail_closed_without_hiding_acl_observations(stage, limit):
    value = observations()
    target = next(row for row in value['cases'] if row['case_id'] == 'rag04-formats-05')
    target[stage + '_fragment_ids'] = [f'unknown-{index}' for index in range(limit)]
    at_limit = next(row for row in score(value)['cases'] if row['case_id'] == target['case_id'])
    assert stage + '_fragment_limit' not in at_limit['critical']
    target[stage + '_fragment_ids'].append('price-1')
    result = score(value)
    above_limit = next(row for row in result['cases'] if row['case_id'] == target['case_id'])
    assert stage + '_fragment_limit' in above_limit['critical']
    assert ('incorrect_source' if stage == 'citation' else 'unauthorized_evidence') in above_limit['critical']
    assert result['acceptance'] == 'not_accepted'


@pytest.mark.parametrize('child,parent', [('selected', 'candidate'), ('sent', 'selected')])
def test_known_empty_parent_cannot_supply_a_child_but_unknown_parent_is_not_empty(child, parent):
    value = observations()
    target = next(row for row in value['cases'] if row['case_id'] == 'rag04-formats-05')
    target[parent + '_fragment_ids'] = []
    row = next(row for row in score(value)['cases'] if row['case_id'] == target['case_id'])
    assert child + '_outside_' + parent in row['critical']
    assert row[parent + '_hit_at_5'] == 0 and row[parent + '_stage_known']
    target[parent + '_fragment_ids'] = None
    row = next(row for row in score(value)['cases'] if row['case_id'] == target['case_id'])
    assert child + '_outside_' + parent not in row['critical']
    assert row[parent + '_hit_at_5'] is None and not row[parent + '_stage_known']
    if parent == 'candidate':
        assert row['candidate_hit_at_20'] is None


def test_unknown_sent_stage_preserves_uncertainty_without_crashing_citation_validation():
    value = observations()
    target = value['cases'][0]
    target.update(sent_fragment_ids=None, review=None)
    row = score(value)['cases'][0]
    assert row['sent_hit_at_5'] is None
    assert row['sent_evidence_relevance'] == 'unknown'
    assert 'sent_evidence_unknown' in row['diagnostics']
    assert 'incorrect_source' not in row['critical']
    assert row['grounding'] is None and not row['human_review_complete']


@pytest.mark.parametrize('error_code', ['LENY_CONTEXT_LIMIT', 'LENY_RAG_CONTEXT_LIMIT'])
@pytest.mark.parametrize('http_status', [200, 422])
def test_operational_context_failure_never_becomes_input_rejection_or_abstention(error_code, http_status):
    value = observations()
    target = next(row for row in value['cases'] if row['case_id'] == 'rag04-no_evidence-03')
    target.update(status='failed', error_code=error_code, http_status=http_status,
                  failure_stage='input', abstained=True, review=None)
    result = score(value)
    row = next(row for row in result['cases'] if row['case_id'] == target['case_id'])
    assert row['status'] == 'failed' and row['error_code'] == error_code
    assert row['failure_stage'] == 'context' and row['operational_failure']
    assert row['route_basis'] == 'recorded_pipeline_route'
    assert row['no_evidence_abstention'] == 0
    assert 'unsuccessful_attempts' in result['acceptance_failures']


@pytest.mark.parametrize('update', [
    {'target_executed': False}, {'status': 'failed'}, {'status': 'abstained'},
    {'route': 'rag'}, {'error_code': 'LENY_RAG_REVIEW_INVALID'}, {'failure_stage': 'review'}])
def test_claimed_abstention_requires_a_successfully_completed_error_free_target(update):
    value = observations()
    target = next(row for row in value['cases'] if row['case_id'] == 'rag04-no_evidence-03')
    target.update(update)
    row = next(row for row in score(value)['cases'] if row['case_id'] == target['case_id'])
    assert row['no_evidence_abstention'] == 0


@pytest.mark.parametrize('legacy', [False, True])
def test_absent_doc_role_is_unexecuted_setup_not_an_observed_security_violation(legacy):
    value = observations()
    target = next(row for row in value['cases'] if row['case_id'] == 'rag04-acl-06')
    target.update(status='failed', route='unknown', error_code='preexisting_unauthorized_role_absent')
    if not legacy:
        target['target_executed'] = False
    result = score(value)
    row = next(row for row in result['cases'] if row['case_id'] == target['case_id'])
    assert not row['target_executed'] and row['failure_stage'] == 'setup'
    assert row['route_basis'] == 'target_not_executed_role_absent'
    assert row['diagnostics'] == ['target_role_absent']
    assert 'security_route_failure' not in row['critical']
    assert row['latency_ms'] is None and row['sent_hit_at_5'] is None
    assert not row['human_review_complete']
    assert {'unsuccessful_attempts', 'acl_route_accuracy'} <= set(result['acceptance_failures'])
    assert target['route'] == 'unknown' and target['review'] is not None


def test_executed_forbidden_role_answer_still_fails_the_security_gate():
    value = observations()
    target = next(row for row in value['cases'] if row['case_id'] == 'rag04-acl-06')
    target.update(target_executed=True, route='general')
    result = score(value)
    row = next(row for row in result['cases'] if row['case_id'] == target['case_id'])
    assert 'security_route_failure' in row['critical']
    assert result['acceptance'] == 'not_accepted'


def test_inventory_false_abstention_is_functional_failure_without_implying_a_security_breach():
    value = observations()
    target = next(row for row in value['cases'] if row['case_id'] == 'rag04-acl-03')
    target.update(route='no_evidence', sent_fragment_ids=[], citation_fragment_ids=[], review=None)
    result = score(value)
    row = next(row for row in result['cases'] if row['case_id'] == target['case_id'])
    assert 'functional_route_failure' in row['critical']
    assert 'security_route_failure' not in row['critical']
    assert 'acl_route_accuracy' in result['acceptance_failures']


@pytest.mark.parametrize('case_id,source', [
    ('rag04-acl-10', 'work-1'), ('rag04-formats-05', 'conflict-1'),
    ('rag04-synonyms-07', 'price-1'), ('rag04-synonyms-10', 'conflict-2'),
    ('rag04-no_evidence-03', 'conflict-1')])
def test_authorized_tangential_documentary_answer_is_critical_without_inventing_a_human_review(case_id, source):
    value = observations()
    target = next(row for row in value['cases'] if row['case_id'] == case_id)
    target.update(route='rag', candidate_fragment_ids=[source], selected_fragment_ids=[source],
                  sent_fragment_ids=[source], citation_fragment_ids=[source], review=None)
    result = score(value)
    row = next(row for row in result['cases'] if row['case_id'] == case_id)
    assert 'unauthorized_evidence' not in row['critical']
    assert 'documentary_completion_without_relevant_evidence' in row['critical']
    assert 'authorized_but_irrelevant_evidence' in row['diagnostics']
    assert row['grounding'] is None and not row['human_review_complete']
    assert result['acceptance'] == 'not_accepted'


@pytest.mark.parametrize('update,message', [
    ({'error_code': {'message': 'private'}}, 'typed identifiers'),
    ({'error_code': 'private free-form error'}, 'typed identifiers'),
    ({'failure_stage': 'private free-form stage'}, 'failure stage'),
    ({'failure_stage': []}, 'failure stage'),
    ({'citation_fragment_ids': [{}]}, 'identifier lists'),
    ({'target_executed': True, 'error_code': 'preexisting_unauthorized_role_absent'}, 'absent target role')])
def test_untyped_error_metadata_and_contradictory_execution_claims_are_rejected(update, message):
    value = observations()
    value['cases'][0].update(update)
    with pytest.raises(ValueError, match=message):
        score(value)
