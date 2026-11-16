"""Private review rendering and public counters; no network, database or model."""
import importlib.util
from pathlib import Path
import sys

SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location('spec03_review_package',SCRIPTS/'build_leny_spec03_review.py')
package=importlib.util.module_from_spec(spec);spec.loader.exec_module(package)


def case(scope='documented',**changes):
    return dict(id='one',question='Pregunta empresarial',response='PRIVATE_RESPONSE_SENTINEL',seconds=4,
        termination='done',http_status=200,history_matches_response=True,
        final=dict(outcome='answered',response_scope=scope,sources=[{'source_id':'private-id'}] if scope!='general' else []),
        events=[{'type':'done'}],sources=[dict(http_status=200,detail={'text':'PRIVATE_SOURCE_SENTINEL'})] if scope!='general' else [],**changes)


def test_public_summary_has_no_private_question_response_source_or_id():
    import json
    summary=package.phase_summary('baseline',dict(cases=[case()],state='complete'))
    serialized=json.dumps(summary)
    assert all(word not in serialized for word in ('PRIVATE_RESPONSE_SENTINEL','PRIVATE_SOURCE_SENTINEL','private-id','Pregunta empresarial'))
    assert summary['documentary_response_n']==1 and summary['semantic_success_rate'] is None


def test_general_and_failed_turns_are_not_documentary_successes():
    summary=package.phase_summary('baseline',dict(cases=[case('general'),
        dict(id='failed',termination='error',seconds=1,error_code='LENY_RAG_MEMORY')]))
    assert summary['documentary_response_n']==0 and summary['general_response_n']==1
    assert summary['cases_n']==2 and summary['p95'] is None and summary['human_acceptance'] is None


def test_html_escapes_untrusted_response_and_never_attaches_synthetic_gold_by_id():
    row=case();row['response']='<script>PRIVATE_ATTACK</script>'
    jobs={phase:dict(cases=[row],state='complete') for phase in package.PHASES}
    corpus={'cases':[dict(id='one',question='Different synthetic question',expected_intent='SECRET_SYNTHETIC_GOLD',
        essential_fact_ids=['unrelated-policy'],forbidden=[])]}
    rendered=package.render(Path('.'),jobs,['one'],corpus)
    assert '&lt;script&gt;PRIVATE_ATTACK&lt;/script&gt;' in rendered
    assert '<script>PRIVATE_ATTACK</script>' not in rendered
    assert 'SECRET_SYNTHETIC_GOLD' not in rendered and 'unrelated-policy' not in rendered
    assert 'fetch(' not in rendered and 'localStorage' not in rendered


def test_review_keeps_both_candidate_attempts_and_eight_reserved_slots():
    assert 'C1-Gemini-spec03' in package.PHASES and 'C2-Gemini-spec03' in package.PHASES
    jobs={phase:dict(cases=[],state='missing') for phase in package.PHASES}
    rendered=package.render(Path('.'),jobs,[],{'cases':[]})
    assert 'data-review="reserved.8.question"' in rendered
    assert 'data-review="reserved.9.question"' not in rendered
