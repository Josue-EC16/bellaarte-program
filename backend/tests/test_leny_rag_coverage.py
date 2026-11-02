"""Coverage contracts with synthetic review records; no real human approval."""
from copy import deepcopy
from dataclasses import replace
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.services.leny_rag_coverage import (
    Approval, CoverageDecision, CoverageVerifier, Manifest, MemoryCoverageProvider,
    Vocabulary, digest, resolve_request,
)


def support():
    # Simulated approvals exercise the approved branch; never written as a
    # human-reviewed artefact or used to approve the draft experimental corpus.
    approval = dict(state='approved', reviewed_by='synthetic-test-only',
                    reviewed_at='2026-10-21T00:00:00+00:00', human_reviewed=True)
    vocabulary = dict(version='test-v1', approval=approval, concepts=[
        dict(id='stock', kind='topic', aliases=['inventario', 'botones']),
        dict(id='garment', kind='topic', aliases=['confección']),
        dict(id='embroidery', kind='topic', aliases=['bordados'], parents=['garment']),
        dict(id='money', kind='topic', aliases=['tarifa']),
        dict(id='quantity', kind='aspect', aliases=['cantidad']),
        dict(id='procedure', kind='aspect', aliases=['procedimiento']),
        dict(id='condition', kind='aspect', aliases=['condición']),
        dict(id='duration', kind='aspect', aliases=['duración']),
        dict(id='linen', kind='qualifier', aliases=['de lino']),
    ], grammar_words=['que', 'indica', 'el', 'la', 'del', 'de', 'completo', 'y'],
        complete_phrases=['completo'], followup_phrases=['y después'])
    text = 'Mínimo 17 unidades de botones. Registrar diferencias antes de reponer.'
    row = dict(document_id=str(uuid4()), version_id=str(uuid4()), indexation_id=str(uuid4()),
               fragment_id=str(uuid4()), text=text, source_sha256=digest('synthetic original'))
    unit = dict(fragment_id=row['fragment_id'], text_sha256=digest(text),
                spans=[dict(start=0, end=len(text), sha256=digest(text))],
                topics=['stock'], aspects=['quantity', 'condition', 'procedure'])
    manifest = dict(revision=1, document_id=row['document_id'], version_id=row['version_id'],
                    indexation_id=row['indexation_id'], source_sha256=row['source_sha256'],
                    source_hash_basis='synthetic_virtual_document', vocabulary_version='test-v1',
                    approval=approval, units=[unit])
    return vocabulary, manifest, row


def verifier(vocabulary, *manifests):
    return CoverageVerifier(MemoryCoverageProvider(vocabulary, list(manifests)))


def test_original_question_not_a_selector_label_is_the_only_intent_authority():
    v, m, r = support()
    checked = verifier(v, m).evaluate('¿Qué cantidad indica el inventario?', [r])
    assert checked.release_allowed and checked.fragment_ids == (r['fragment_id'],)
    assert checked.signature['topics'] == ['stock']
    # The same authorized text cannot become a tariff by a selector self-label.
    checked = verifier(v, m).evaluate('Consulta la tarifa', [r])
    assert not checked.release_allowed and checked.reason == 'coverage_terms_uncertain'
    checked = verifier(v, m).evaluate('tarifa', [r])
    assert checked.verdict == 'not_covered' and checked.reason == 'coverage_subject_mismatch'


def test_unreviewed_annotations_and_research_results_cannot_authorize_streaming():
    v, m, r = support()
    v['approval'] = m['approval'] = dict(state='draft', human_reviewed=False)
    strict = verifier(v, m).evaluate('inventario', [r])
    research = verifier(v, m).evaluate('inventario', [r], research=True)
    assert strict.reason == 'coverage_human_review_pending' and not strict.release_allowed
    assert research.verdict == 'approved' and not research.authoritative and not research.release_allowed
    with pytest.raises(ValidationError):
        Approval(state='approved')


@pytest.mark.parametrize('field', ['version_id', 'indexation_id', 'document_id'])
def test_recontextualization_or_new_publication_never_inherits_approval(field):
    v, m, r = support()
    r[field] = str(uuid4())
    assert verifier(v, m).evaluate('inventario', [r]).reason == 'coverage_manifest_missing'


@pytest.mark.parametrize('mutate,reason', [
    ('original', 'coverage_original_hash_unverified'),
    ('text', 'coverage_fragment_hash_changed'),
    ('span', 'coverage_span_hash_changed'),
    ('tail', 'coverage_span_incomplete'),
    ('withdrawn', 'coverage_manifest_withdrawn'),
    ('vocabulary', 'coverage_vocabulary_stale'),
])
def test_exact_binding_and_full_emitted_content_are_required(mutate, reason):
    v, m, r = support()
    if mutate == 'original': r['source_sha256'] = digest('other original')
    elif mutate == 'text': r['text'] += ' Añadido no revisado.'
    elif mutate == 'span': m['units'][0]['spans'][0]['sha256'] = digest('foreign span')
    elif mutate == 'tail':
        m['units'][0]['spans'][0]['end'] -= 1
        m['units'][0]['spans'][0]['sha256'] = digest(r['text'][:-1])
    elif mutate == 'withdrawn': m['approval'] = dict(state='withdrawn')
    elif mutate == 'vocabulary': m['vocabulary_version'] = 'test-v0'
    assert verifier(v, m).evaluate('inventario', [r]).reason == reason


def test_metadata_provider_never_returns_unselected_foreign_document_annotations():
    v, m, r = support()
    other = deepcopy(m)
    other['document_id'] = str(uuid4())
    provider = MemoryCoverageProvider(v, [m, other])
    assert len(provider.manifests([r])) == 1
    assert provider.manifests([]) == []
    assert verifier(v, m).evaluate('inventario', []).reason == 'coverage_evidence_empty'


def test_general_parent_is_not_an_entailment_of_a_specialty_or_material():
    v, m, r = support()
    m['units'][0]['topics'] = ['garment']
    assert verifier(v, m).evaluate('confección', [r]).release_allowed
    assert verifier(v, m).evaluate('bordados', [r]).reason == 'coverage_subject_mismatch'
    assert verifier(v, m).evaluate('confección de lino', [r]).reason == 'coverage_specialization_not_supported'
    m['units'][0]['qualifiers'] = ['linen']
    assert verifier(v, m).evaluate('confección de lino', [r]).release_allowed
    assert verifier(v, m).evaluate('confección', [r]).reason == 'coverage_narrower_scope'


@pytest.mark.parametrize('question,reason', [
    ('inventario no tarifa', 'coverage_logic_uncertain'),
    ('inventario o tarifa', 'coverage_logic_uncertain'),
    ('inventario si hay pérdidas', 'coverage_logic_uncertain'),
    ('inventario de abalorios fotoluminiscentes', 'coverage_terms_uncertain'),
    ('inventario 99', 'coverage_terms_uncertain'),
])
def test_qualifiers_logic_and_values_cannot_be_erased_as_stopwords(question, reason):
    v, m, r = support()
    assert verifier(v, m).evaluate(question, [r]).reason == reason


def test_normalization_preserves_original_offsets_and_does_not_change_the_question():
    v, _, _ = support()
    question = '¿Qué cantidad indica el inventário?'
    signature = resolve_request(question, Vocabulary.model_validate(v))
    assert [question[s['start']:s['end']] for s in signature['spans']] == ['cantidad', 'inventário']


def test_complete_procedures_and_inseparable_conditions_cannot_be_trimmed():
    v, m, r = support()
    assert verifier(v, m).evaluate('inventario completo', [r]).reason == 'coverage_completeness_undeclared'
    second = deepcopy(m['units'][0]); second['fragment_id'] = str(uuid4())
    m['units'].append(second)
    m['procedures'] = [dict(topic='stock', fragments=[r['fragment_id'], second['fragment_id']])]
    assert verifier(v, m).evaluate('inventario completo', [r]).reason == 'coverage_procedure_incomplete'
    m['procedures'] = []
    m['units'][0]['required_fragment_ids'] = [second['fragment_id']]
    assert verifier(v, m).evaluate('inventario', [r]).reason == 'coverage_condition_dependency_missing'


def test_multiple_subject_aspect_relationships_cannot_be_certified_by_a_union():
    v, m, r = support()
    _, n, s = support()
    n['units'][0]['topics'] = ['money']
    n['units'][0]['aspects'] = ['duration']
    assert verifier(v, m, n).evaluate('cantidad del inventario y duración de la tarifa', [r, s]).reason == 'coverage_relations_uncertain'


def test_every_expanded_source_is_checked_not_only_the_semantic_seed():
    v, m, r = support()
    _, other, extra = support()
    other['units'][0]['topics'] = ['money']
    assert verifier(v, m, other).evaluate('inventario', [r, extra]).reason == 'coverage_tangential_unit'


def test_partial_requires_a_requested_supported_aspect_and_lists_what_is_missing():
    v, m, r = support()
    result = verifier(v, m).evaluate('cantidad y duración del inventario', [r])
    assert result.verdict == 'partial' and result.release_allowed
    assert result.signature['uncovered_aspects'] == ['duration']
    assert verifier(v, m).evaluate('duración del inventario', [r]).reason == 'coverage_aspect_not_supported'


def test_conflicts_compare_same_subject_predicate_unit_and_condition_only():
    v, m, r = support()
    _, n, s = support()
    s['text'] = s['text'].replace('17', '23')
    n['units'][0]['text_sha256'] = digest(s['text'])
    n['units'][0]['spans'] = [dict(start=0, end=len(s['text']), sha256=digest(s['text']))]
    m['units'][0]['assertions'] = [dict(predicate='minimum', value='17', unit='units', condition='active')]
    n['units'][0]['assertions'] = [dict(predicate='minimum', value='23', unit='units', condition='active')]
    assert verifier(v, m, n).evaluate('inventario', [r, s]).verdict == 'conflicting'
    n['units'][0]['assertions'][0]['condition'] = 'damaged'
    assert verifier(v, m, n).evaluate('inventario', [r, s]).verdict == 'approved'


def test_unbacked_assertion_and_tangential_aspect_cannot_authorize_a_response():
    v, m, r = support()
    m['units'][0]['assertions'] = [dict(predicate='minimum', value='991', unit='units')]
    assert verifier(v, m).evaluate('inventario', [r]).reason == 'coverage_assertion_unbacked'
    m['units'][0]['assertions'] = []
    _, n, s = support()
    n['units'][0]['aspects'] = ['duration']
    assert verifier(v, m, n).evaluate('cantidad del inventario', [r, s]).reason == 'coverage_tangential_aspect'


def test_followup_uses_only_bounded_user_topic_and_current_manifest():
    v, m, r = support()
    history = [dict(role='assistant', documentary=True, content='inventario')]
    assert verifier(v, m).evaluate('y después', [r], history=history).reason == 'coverage_anchor_uncertain'
    history = [dict(role='user', documentary=True, content='inventario')]
    assert verifier(v, m).evaluate('y después', [r], history=history).release_allowed
    m['approval'] = dict(state='withdrawn')
    assert not verifier(v, m).evaluate('y después', [r], history=history).release_allowed
    history[0]['content'] = 'inventario ' + 'x'*400
    assert resolve_request('y después', Vocabulary.model_validate(v), history)['reason'] == 'coverage_anchor_uncertain'


def test_catalogue_cycles_duplicates_and_foreign_dependencies_are_invalid():
    v, m, r = support()
    v['concepts'][1]['parents'] = ['embroidery']
    with pytest.raises(ValidationError): Vocabulary.model_validate(v)
    m['units'][0]['required_fragment_ids'] = ['foreign']
    with pytest.raises(ValidationError): Manifest.model_validate(m)
    v, m, r = support()
    with pytest.raises(ValueError): verifier(v, m).evaluate('inventario', [r, r])


def test_alias_collision_requires_clarification_instead_of_first_alphabetical_label():
    v, m, r = support()
    v['concepts'][3]['aliases'].append('inventario')
    assert verifier(v, m).evaluate('inventario', [r]).reason == 'coverage_alias_ambiguous'


def test_service_hook_is_absent_by_default_and_separates_history_when_injected():
    from app.services.leny_service import effective_policy
    from app.services.leny_rag_coverage import COVERAGE_POLICY_VERSION
    from test_leny_security import service_mocks
    from app.core.config import Settings
    env = service_mocks()
    env.service.config = Settings(_env_file=None, leny_rag_profile='rag4_v1')
    assert env.service.coverage_verifier is None
    assert effective_policy(env.service) == 'rag4-v4'
    env.service.coverage_verifier = Mock()
    assert effective_policy(env.service) == COVERAGE_POLICY_VERSION
    env.service.config = Settings(_env_file=None, leny_rag_profile='legacy')
    assert effective_policy(env.service) != COVERAGE_POLICY_VERSION


def test_stream_revalidation_rejects_manifest_withdrawal_or_research_approval():
    from app.services.leny_service import PreparedTurn
    from app.services.leny_ollama import LenyError
    from test_leny_security import service_mocks
    env = service_mocks('inventario')
    v, m, r = support()
    env.service.coverage_verifier = verifier(v, m)
    turn = PreparedTurn(env.service, env.actor, env.payload, uuid4(), [], env.provider, env.lease)
    turn.fragments = [r]
    turn.coverage_binding = asyncio.run(turn.check_coverage([r]))
    asyncio.run(turn.revalidate_coverage())
    m['approval'] = dict(state='withdrawn')
    env.service.coverage_verifier = verifier(v, m)
    with pytest.raises(LenyError) as error: asyncio.run(turn.revalidate_coverage())
    assert error.value.code == 'LENY_RAG_COVERAGE_CHANGED'
    assert env.provider.classify.await_count == 0


def test_diagnostics_accept_codes_and_counts_never_raw_query_or_source_text():
    from app.services.leny_rag_diagnostics import RagDiagnostics
    diagnostics = RagDiagnostics('rag4_v1')
    diagnostics.duration('coverage', .001)
    diagnostics.count('coverage_checked', 3)
    diagnostics.reason = 'coverage_subject_mismatch'
    assert 'inventario' not in str(diagnostics.snapshot())
    with pytest.raises(ValueError): diagnostics.count('source_text', 'secret')


def stream_environment(monkeypatch, decision):
    from app.core.config import Settings
    from app.services import leny_rag_common
    from test_leny_security import service_mocks
    env = service_mocks('Consulta la tarifa')
    env.store.topic_history.return_value = []
    env.service.config = Settings(_env_file=None, leny_rag_profile='rag4_v1', leny_rag_chat_enabled=True)
    _, _, row = support()
    row.update(text='Tarifa sintética: Bs 315.50; saldo antes de entregar.', locator={'page': 1}, source_type='PDF_TEXT')
    env.service.retrieval = Mock()
    env.service.retrieval.ready.return_value = True
    env.service.retrieval.search.return_value = [row]
    env.service.sources = Mock()
    env.service.sources.for_messages.return_value = {}
    env.service.embedding_factory = lambda _: SimpleNamespace(embed=AsyncMock(return_value=[[1.0]+[0.0]*1023]),
                                                              owned_model=False, response_complete=True)
    env.service.coverage_verifier = SimpleNamespace(evaluate=Mock(return_value=decision))
    env.provider.classify.return_value = '{"aspect":"price","scope":"matched","relation":"direct","sources":[1]}'
    monkeypatch.setattr(leny_rag_common, 'available_ram', lambda: 4*1024**3)
    return env, row


@pytest.mark.parametrize('decision', [
    CoverageDecision('not_covered', 'coverage_subject_mismatch'),
    CoverageDecision('uncertain', 'coverage_human_review_pending'),
    CoverageDecision('approved', 'coverage_verified', authoritative=False),
])
def test_full_ndjson_path_veto_precedes_source_persistence_and_documentary_delta(monkeypatch, decision):
    import json
    env, row = stream_environment(monkeypatch, decision)
    async def run():
        turn = await env.service.prepare(env.actor, env.payload)
        return turn, [json.loads(event) async for event in turn.events()]
    turn, events = asyncio.run(run())
    assert events[-1]['type'] == 'done' and events[-1]['outcome'] == 'clarification'
    assert row['text'] not in ''.join(e.get('text', '') for e in events)
    env.service.sources.persist.assert_not_called()
    env.provider.stream.assert_not_called()
    env.lease.close.assert_called_once()
    assert env.store.save.call_args.kwargs['reason'] == 'rag_evidence_insufficient'
    assert turn.diagnostics.reason == decision.reason


def test_full_ndjson_success_retains_exact_quotes_and_rechecks_before_release(monkeypatch):
    import json
    initial = CoverageDecision('approved', 'coverage_verified', manifest_fingerprints=('binding',), authoritative=True)
    env, row = stream_environment(monkeypatch, initial)
    env.service.coverage_verifier.evaluate.return_value = replace(initial, fragment_ids=(row['fragment_id'],))
    async def run():
        turn = await env.service.prepare(env.actor, env.payload)
        return [json.loads(event) async for event in turn.events()]
    events = asyncio.run(run())
    assert events[-1]['type'] == 'done' and events[-1]['outcome'] == 'answered'
    assert row['text'] in ''.join(e.get('text', '') for e in events)
    assert env.service.coverage_verifier.evaluate.call_count >= 3
    assert env.service.coverage_verifier.evaluate.call_args.args[0] == env.payload.message
    env.service.sources.persist.assert_called_once()
    env.lease.close.assert_called_once()


def test_invalid_coverage_closes_lease_without_persisting_or_emitting(monkeypatch):
    import json
    env, row = stream_environment(monkeypatch, CoverageDecision('uncertain', 'coverage_human_review_pending'))
    env.service.coverage_verifier.evaluate.side_effect = ValueError('internal path must not escape')
    async def run():
        turn = await env.service.prepare(env.actor, env.payload)
        return [json.loads(event) async for event in turn.events()]
    events = asyncio.run(run())
    assert events[-1]['type'] == 'error' and events[-1]['code'] == 'LENY_RAG_COVERAGE_INVALID'
    assert 'internal path' not in str(events)
    env.service.sources.persist.assert_not_called()
    env.lease.close.assert_called_once()


def test_cancellation_during_gate_closes_lease_without_documentary_emission(monkeypatch):
    import json
    from app.services.leny_service import PreparedTurn
    env, row = stream_environment(monkeypatch, CoverageDecision('uncertain', 'coverage_human_review_pending'))
    async def run():
        entered = asyncio.Event()
        async def blocked_gate(_turn, _rows):
            entered.set()
            await asyncio.Event().wait()
        with patch.object(PreparedTurn, 'check_coverage', blocked_gate):
            turn = await env.service.prepare(env.actor, env.payload)
            stream = turn.events()
            first = json.loads(await stream.__anext__())
            assert first['type'] == 'start'
            pending = asyncio.create_task(stream.__anext__())
            await asyncio.wait_for(entered.wait(), 2)
            pending.cancel()
            with pytest.raises(asyncio.CancelledError): await pending
            await stream.aclose()
    asyncio.run(run())
    env.service.sources.persist.assert_not_called()
    env.lease.close.assert_called_once()


def test_withdrawal_after_initial_verification_stops_before_first_quote(monkeypatch):
    import json
    env, row = stream_environment(monkeypatch, CoverageDecision('approved', 'coverage_verified', authoritative=True))
    accepted = CoverageDecision('approved', 'coverage_verified', (row['fragment_id'],), ('stamp',), True)
    env.service.coverage_verifier.evaluate.side_effect = [accepted, CoverageDecision('uncertain', 'coverage_manifest_withdrawn')]
    async def run():
        turn = await env.service.prepare(env.actor, env.payload)
        return [json.loads(event) async for event in turn.events()]
    events = asyncio.run(run())
    assert events[-1]['type'] == 'error' and events[-1]['code'] == 'LENY_RAG_COVERAGE_CHANGED'
    assert row['text'] not in ''.join(e.get('text', '') for e in events)
    env.lease.close.assert_called_once()
