"""Runner safety/selection/checkpoint tests without PostgreSQL or Ollama."""
import io
import asyncio
import json
from types import SimpleNamespace

import pytest

from scripts import run_leny_rag_quality as runner


def corpus():
    return json.loads(runner.CORPUS.read_text(encoding='utf-8'))


def test_pilot_prioritizes_natural_and_conversational_failures():
    selected = runner.select_cases(corpus(), 'pilot')
    assert len(selected) == 9
    assert [row['category'] for row in selected[:7]] == ['natural']*4+['followup']*3
    assert selected[0]['critical_natural'] is True
    assert runner.select_cases(corpus(), 'pilot', 2) == selected[:2]
    assert len(runner.select_cases(corpus(), 'development')) == 84


def test_diagnostic_selection_is_explicit_seen_development_failures_not_holdout():
    selected = runner.select_cases(corpus(), 'diagnostic')
    assert len(selected) == 14
    assert 'rag04-followup-07' in {case['id'] for case in selected}
    assert all(case['id'] in {row['id'] for row in corpus()['cases']} for case in selected)


def test_supervised_preservation_check_is_six_frozen_cases_not_a_new_corpus():
    original = corpus()
    selected = runner.select_cases(original, 'supervised')
    assert [case['id'] for case in selected] == ['rag04-natural-01', 'rag04-natural-08',
        'rag04-acl-01', 'rag04-no_evidence-02', 'rag04-followup-03', 'rag04-acl-07']
    assert all(case in original['cases'] for case in selected)
    args = runner.parser().parse_args(['--profile','rag4_v1','--mode','supervised','--output','synthetic.json'])
    assert args.mode == 'supervised' and len(original['cases']) == 84


def test_quality_diagnostic_is_twelve_paired_existing_cases_not_a_holdout():
    selected = runner.select_cases(corpus(), 'quality')
    assert len(selected) == 12
    assert {item['id'] for item in selected} >= {'rag04-natural-01','rag04-acl-01','rag04-acl-08','rag04-no_evidence-02'}
    assert all(item in corpus()['cases'] for item in selected)


def test_layered_modes_keep_all_natural_questions_and_seen_failures_without_replacing_corpus():
    original = corpus()
    selected = runner.select_cases(original, 'focused')
    assert len(selected) == 48
    assert sum(c['category'] == 'natural' for c in selected) == 14
    assert {c['id'] for c in selected} >= {'rag04-acl-03', 'rag04-acl-10', 'rag04-formats-05',
        'rag04-formats-06', 'rag04-literal-03', 'rag04-synonyms-11', 'rag04-no_evidence-03'}
    assert runner.select_cases(original, 'retrieval') == selected
    assert [c['id'] for c in runner.select_cases(original, 'stability')] == ['rag04-formats-05', 'rag04-acl-10']
    assert len(original['cases']) == 84


def test_contract_regression_mode_is_explicit_and_keeps_model_evaluation_separate():
    args = runner.parser().parse_args(['--profile','rag4_v1','--mode','contracts','--output','synthetic.json'])
    assert args.mode == 'contracts'


def test_checkpoint_fsync_precedes_effect_and_consumed_attempt_never_replayed(tmp_path):
    path = tmp_path/'checkpoint.jsonl'
    contract = {'profile': 'legacy', 'corpus_sha256': 'synthetic'}
    journal = runner.Journal(path, contract)
    journal.append({'event': 'attempt', 'case_id': 'natural-1', 'request_id': 'synthetic-id'})
    assert json.loads(path.read_text().splitlines()[-1])['event'] == 'attempt'
    resumed = runner.Journal(path, contract)
    assert resumed.consumed('natural-1')
    assert resumed.completed() == {}
    resumed.append({'event': 'case', 'case_id': 'natural-1', 'observation': {'case_id': 'natural-1', 'status': 'failed'}})
    assert resumed.completed()['natural-1']['status'] == 'failed'
    with pytest.raises(ValueError):
        runner.Journal(path, {'profile': 'rag4_v1', 'corpus_sha256': 'synthetic'})


def test_torn_checkpoint_is_rejected_instead_of_assuming_request_not_admitted(tmp_path):
    path = tmp_path/'checkpoint.jsonl'
    path.write_text('{"event":"attempt"', encoding='utf-8')
    with pytest.raises(json.JSONDecodeError):
        runner.Journal(path, {})


def test_quota_wait_preserves_limit_with_progress_every_thirty_seconds():
    delays, progress = [], []
    runner.wait_retry('60', sleep=delays.append, progress=lambda value, **_: progress.append(json.loads(value)))
    assert delays == [30, 30]
    assert [row['remaining_seconds'] for row in progress] == [60, 30]


def test_configuration_preserves_resource_safety_without_credentials_in_report(monkeypatch, tmp_path):
    from app.core.config import Settings
    monkeypatch.setenv('TEST_DATABASE_URL', 'postgresql+psycopg2://synthetic:private@127.0.0.1:55432/bab_vdos_testing')
    monkeypatch.chdir(tmp_path)
    args = SimpleNamespace(profile='rag4_v1', evidence_mode='adaptive', budget=2304,
                           ranking='semantic', neighbors=False, token_probe=True)
    settings = Settings(_env_file=None)
    proof = runner.configuration(settings, args)
    assert settings.leny_keep_alive == '0'
    assert (settings.leny_num_ctx, settings.leny_num_predict) == (4096, 768)
    assert (settings.leny_rate_limit, settings.leny_rate_window_seconds) == (5, 60)
    assert (settings.leny_rag_cpu_threads, settings.leny_rag_batch_size) == (4, 2)
    assert settings.leny_rag_min_ram_bytes == 2*1024**3
    assert settings.leny_rag_min_resident_ram_bytes == 1024**3
    assert settings.leny_rag_adaptive_token_probe
    assert 'private' not in json.dumps(proof) and 'database_url' not in proof


def test_parser_requires_explicit_profile_and_defaults_to_pilot():
    args = runner.parser().parse_args(['--profile', 'legacy', '--output', 'synthetic.json'])
    assert args.mode == 'pilot' and args.budget == 2048
    assert not args.exclusive_window_confirmed and not args.token_probe
    with pytest.raises(SystemExit):
        runner.parser().parse_args(['--profile', 'unknown', '--output', 'synthetic.json'])


def test_main_without_exclusive_window_exits_before_any_database_or_model(monkeypatch):
    monkeypatch.setattr('sys.argv', ['runner', '--profile', 'legacy', '--output', 'synthetic.json'])
    assert runner.main() == 2


def test_generated_pdf_original_contains_synthetic_procedure_and_whole_pages():
    from pypdf import PdfReader
    document = {'fragments': [{'text': '1. Medir cintura de 75 cm. No cortar sin aprobación.'},
                              {'text': '2. Confirmar anticipo del 40 %. Entregar con saldo Bs 0.'}]}
    data, media, filename = runner.synthetic_original(document)
    assert media == 'application/pdf' and filename.endswith('.pdf')
    reader = PdfReader(io.BytesIO(data))
    assert len(reader.pages) == 2
    assert '75 cm' in reader.pages[0].extract_text()
    assert '40 %' in reader.pages[1].extract_text()


def test_generated_docx_is_valid_zip_and_preserves_literal_numbers():
    import zipfile
    from xml.etree import ElementTree
    document = {'source_type': 'DOCX_TABLE', 'fragments': [{'text': 'Anticipo 40 %; Bs 250.'}]}
    data, media, name = runner.synthetic_original(document)
    assert media.endswith('wordprocessingml.document') and name.endswith('.docx')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        root = ElementTree.fromstring(archive.read('word/document.xml'))
        assert 'Anticipo 40 %; Bs 250.' in ''.join(root.itertext())


def test_budget_stress_is_distinct_whole_fragment_data_not_tuned_gold():
    source = corpus()
    changed = runner.stress_procedure(source, 900)
    assert changed['cases'] == source['cases']
    assert changed != source
    for original, expanded in zip(source['documents'][0]['fragments'], changed['documents'][0]['fragments']):
        assert expanded['text'].startswith(original['text'])
        assert 900 <= len(expanded['text'].encode('utf-8')) <= 3072
        assert expanded['fact_ids'] == original['fact_ids']


def test_budget_sweep_uses_distinct_cases_and_one_frozen_question():
    selected = runner.select_cases(corpus(), 'budget')
    assert len(selected) == 4 == len({case['id'] for case in selected})
    assert len({case['question'] for case in selected}) == 1
    assert [case['budget_variant']['bytes'] for case in selected] == [2048, 2304, 2560, 2048]
    assert selected[-1]['budget_variant']['probe'] is True


def test_received_generation_evidence_survives_later_stream_error():
    provider = SimpleNamespace(response_complete=False, inference_started=True)
    traces = {'selected_fragment_ids': ['synthetic-proc-1']}
    async def content_then_failure():
        yield 'Synthetic answer'
        raise RuntimeError('synthetic failure')
    async def run():
        with pytest.raises(RuntimeError):
            async for _ in runner.trace_generation(provider, content_then_failure(), traces):
                pass
    asyncio.run(run())
    assert traces['sent_fragment_ids'] == ['synthetic-proc-1']
    assert traces['sent_evidence_basis'] == 'provider_content_received'


@pytest.mark.parametrize('started,complete,expected,basis', [
    (True, False, None, 'generation_attempt_unconfirmed'),
    (False, False, [], 'generation_not_started'),
    (True, True, ['synthetic-proc-1'], 'provider_completion_received')])
def test_generation_trace_distinguishes_unknown_from_no_evidence(started, complete, expected, basis):
    provider = SimpleNamespace(response_complete=complete, inference_started=started)
    traces = {'selected_fragment_ids': ['synthetic-proc-1']}
    async def empty():
        if False:
            yield ''
    async def run():
        async for _ in runner.trace_generation(provider, empty(), traces):
            pass
    asyncio.run(run())
    assert traces['sent_fragment_ids'] == expected and traces['sent_evidence_basis'] == basis


def test_failed_prerequisite_is_marked_separately_from_actual_followup():
    prior = runner.annotate_target({'status': 'failed'}, 0, 2)
    assert prior == {'status': 'failed', 'observed_turn': 0, 'target_turn': 2,
                     'target_executed': False, 'failure_stage': 'prerequisite'}
    target = runner.annotate_target({'status': 'completed'}, 2, 2)
    assert target['target_executed'] and 'failure_stage' not in target


def test_production_source_freeze_detects_changes_without_reading_outside_root(tmp_path):
    import hashlib
    path = tmp_path/'source.py'
    path.write_text('synthetic code', encoding='utf-8')
    files = {'source.py': hashlib.sha256(path.read_bytes()).hexdigest()}
    assert runner.frozen_sources_match(tmp_path, files)
    path.write_text('changed', encoding='utf-8')
    assert not runner.frozen_sources_match(tmp_path, files)
    assert not runner.frozen_sources_match(tmp_path, {'../outside.py': 'a'*64})
    assert not runner.frozen_sources_match(tmp_path, {})
