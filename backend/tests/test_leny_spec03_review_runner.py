"""Checkpoint and corpus contracts only: no HTTP, app startup or inference."""
import json
from collections import Counter
from pathlib import Path

import pytest
from scripts import run_leny_spec03_review as runner


def job():
    return dict(id='baseline-01',provider='gemini',quality_profile='baseline',omit_profile=True,
                cases=[dict(id='case-1',question='Pregunta sintética')])


def test_corpus_twenty_visible_development_cases_and_no_reserved_data():
    corpus=json.loads(runner.CORPUS.read_text(encoding='utf-8'))
    assert corpus['split']=='development' and corpus['gold_status']=='provisional_owner_review_required'
    assert len(corpus['cases'])==20 and len({c['id'] for c in corpus['cases']})==20
    assert Counter(c['category'] for c in corpus['cases'])==dict(comprehension=5,followup=5,retrieval=4,absence=3,guidance_security=3)
    facts={f for d in corpus['documents'] for p in d['fragments'] for f in p['fact_ids']}
    assert all(set(c['essential_fact_ids'])<=facts for c in corpus['cases'])
    runner.validate_job(dict(id='development',cases=[{k:c[k] for k in ('id','question','conversation','depends_on') if k in c} for c in corpus['cases']]),'development')


@pytest.mark.parametrize('change',[dict(id='../escape'),dict(provider='evil'),dict(quality_profile='holdout'),
    dict(url='https://elsewhere.invalid'),dict(quality_profile='spec03',omit_profile=True),
    dict(cases=[dict(id='a',question='x',depends_on='future')])])
def test_job_rejects_executable_arbitrary_targets_and_invalid_profiles(change):
    with pytest.raises(ValueError):runner.validate_job(job()|change,'baseline-01')


def test_job_allows_future_twenty_eight_without_opening_reserved_corpus():
    data=job();data['cases']=[dict(id='c'+str(i),question='Caso sintético') for i in range(28)]
    assert runner.validate_job(data,'baseline-01') is data
    data['cases'].append(dict(id='extra',question='Otro'))
    with pytest.raises(ValueError):runner.validate_job(data,'baseline-01')


def test_completed_or_quota_paused_job_never_requests_http(tmp_path):
    data=job();path=tmp_path/'results/baseline-01.json'
    for state in ('complete','paused_quota'):
        runner.save(path,dict(job=data['id'],job_sha256=runner.fingerprint(data),cases=[],conversations={},state=state,resume_token=''))
        runner.run_job(None,tmp_path,data)
        assert json.loads(path.read_text())['state']==state


def test_changed_job_cannot_reuse_completed_checkpoint(tmp_path):
    data=job();runner.save(tmp_path/'results/baseline-01.json',dict(job_sha256='different',cases=[]))
    with pytest.raises(ValueError,match='changed'):runner.run_job(None,tmp_path,data)


def test_retry_after_is_bounded_and_not_a_day_sleep():
    assert runner.retry_delay('999999')==60
    assert runner.retry_delay('0')==13
    assert runner.retry_delay('nonsense')==13


def test_error_codes_never_echo_arbitrary_provider_details():
    assert runner.event_code('LENY_EVALUATION_QUOTA')=='LENY_EVALUATION_QUOTA'
    assert runner.event_code('private credential or document text')=='STREAM_ERROR'


def test_quota_attempt_is_persisted_before_post_and_never_replayed(tmp_path, monkeypatch):
    data=job()
    data['cases'].append(dict(id='case-2',question='Segundo caso'))
    monkeypatch.setattr(runner,'refresh_auth',lambda client:None)
    class Response:
        status_code=429
        headers={'Retry-After':'90000'}
        def json(self):return dict(detail=dict(code='LENY_EVALUATION_QUOTA'))
    class Client:
        calls=0
        def post(self,url,**kwargs):
            checkpoint=json.loads((tmp_path/'results/baseline-01.json').read_text())
            assert checkpoint['cases'][0]['termination']=='attempt_started'
            assert checkpoint['cases'][0]['consumed'] is True
            self.calls+=1
            return Response()
    client=Client()
    runner.run_job(client,tmp_path,data)
    saved=json.loads((tmp_path/'results/baseline-01.json').read_text())
    assert saved['state']=='paused_quota' and len(saved['cases'])==1
    assert saved['cases'][0]['error_code']=='LENY_EVALUATION_QUOTA'
    runner.run_job(client,tmp_path,data)
    assert client.calls==1
