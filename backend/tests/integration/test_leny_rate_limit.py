"""Real PostgreSQL quota concurrency and durable request identity, isolated only."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def rate_actor(synthetic_recipient):
    from app.services.leny_store import LenyActor
    return LenyActor(synthetic_recipient.account_id, synthetic_recipient.user_id, str(uuid4()))


@pytest.fixture
def limiter(pg_cluster):
    from app.services.leny_rate_limit import RateLimiter
    return RateLimiter(sessionmaker(bind=pg_cluster.engine))


def payload(request_id=None, message='Pregunta sintética'):
    return SimpleNamespace(conversation_id=uuid4(), request_id=request_id or uuid4(), message=message)


def test_concurrent_rolling_quota_is_atomic(limiter, rate_actor, pg_cluster):
    from app.services.leny_ollama import LenyError
    barrier = Barrier(8)
    def attempt(_):
        barrier.wait(timeout=10)
        try:
            limiter.admit(rate_actor, payload())
            return 'admitted'
        except LenyError as error:
            assert error.code == 'LENY_RATE_LIMITED'
            assert error.status == 429
            assert 1 <= error.retry_after <= 60
            return 'limited'
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(attempt, range(8)))
    assert results.count('admitted') == 5
    assert results.count('limited') == 3
    with pg_cluster.engine.connect() as connection:
        assert connection.execute(text('SELECT count(*) FROM leny.admissions WHERE user_id=:id'),
                                  {'id': rate_actor.user_id}).scalar_one() == 5
        assert connection.execute(text("SELECT count(*) FROM auditoria_sistema WHERE usu_id=:id AND aud_accion_funcional='LENY_QUOTA_EXCEEDED'"),
                                  {'id': rate_actor.user_id}).scalar_one() == 1


@pytest.mark.parametrize('outcome', ['completed', 'failed', 'rejected', 'interrupted', 'busy'])
def test_dedup_preserves_outcome_without_recharge(limiter, rate_actor, outcome, pg_cluster):
    from app.services.leny_store import LenyConflict
    item = payload()
    limiter.admit(rate_actor, item)
    limiter.finish(rate_actor, item.request_id, outcome)
    with pytest.raises(LenyConflict) as duplicate:
        limiter.admit(rate_actor, item)
    assert duplicate.value.code == 'LENY_REQUEST_DUPLICATE'
    assert duplicate.value.generation_status == outcome
    assert duplicate.value.request_id == item.request_id
    item.message = 'Otra pregunta'
    with pytest.raises(LenyConflict) as reused:
        limiter.admit(rate_actor, item)
    assert reused.value.code == 'LENY_REQUEST_REUSED'
    with pg_cluster.engine.connect() as connection:
        row = connection.execute(text('SELECT count(*),min(length(fingerprint)) FROM leny.admissions WHERE user_id=:id'),
                                 {'id': rate_actor.user_id}).one()
        assert tuple(row) == (1, 64)


def test_concurrent_duplicate_does_not_charge_twice(limiter, rate_actor, pg_cluster):
    from app.services.leny_store import LenyConflict
    item = payload()
    barrier = Barrier(2)
    def attempt(_):
        barrier.wait(timeout=10)
        try:
            limiter.admit(rate_actor, item)
            return 'admitted'
        except LenyConflict as error:
            assert error.code == 'LENY_REQUEST_DUPLICATE'
            assert error.generation_status == 'interrupted'
            return 'duplicate'
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(attempt, range(2))) == ['admitted', 'duplicate']


def test_bounded_retention_keeps_window_and_recent_ledger(limiter, rate_actor, pg_cluster):
    with pg_cluster.engine.begin() as connection:
        for seconds in (7200, 3500, 30):
            connection.execute(text('''
                INSERT INTO leny.admissions(user_id,request_id,fingerprint,admitted_at,outcome)
                VALUES(:user,:request,:hash,clock_timestamp()-make_interval(secs=>:age),'failed')
            '''), {'user': rate_actor.user_id, 'request': uuid4(), 'hash': 'f'*64, 'age': seconds})
    limiter.admit(rate_actor, payload())
    with pg_cluster.engine.connect() as connection:
        assert connection.execute(text('SELECT count(*) FROM leny.admissions WHERE user_id=:id'),
                                  {'id': rate_actor.user_id}).scalar_one() == 3
    # Every admitted failure remains a quota event until its rolling window ends.
    for _ in range(3):
        limiter.admit(rate_actor, payload())
    from app.services.leny_ollama import LenyError
    with pytest.raises(LenyError) as exceeded:
        limiter.admit(rate_actor, payload())
    assert exceeded.value.code == 'LENY_RATE_LIMITED'


def test_expired_quota_reopens_and_finish_is_owner_scoped(limiter, rate_actor, pg_cluster):
    item = payload()
    limiter.admit(rate_actor, item)
    other_actor = SimpleNamespace(user_id=-1)
    limiter.finish(other_actor, item.request_id, 'completed')
    with pg_cluster.engine.begin() as connection:
        assert connection.execute(text('SELECT outcome FROM leny.admissions WHERE user_id=:id'),
                                  {'id': rate_actor.user_id}).scalar_one() == 'admitted'
        connection.execute(text("UPDATE leny.admissions SET admitted_at=clock_timestamp()-interval '61 seconds' WHERE user_id=:id"),
                           {'id': rate_actor.user_id})
    for _ in range(5):
        limiter.admit(rate_actor, payload())


def test_cleanup_is_bounded_and_never_erases_active_long_window(rate_actor, pg_cluster):
    from app.services.leny_rate_limit import RateLimiter
    limiter = RateLimiter(sessionmaker(bind=pg_cluster.engine), limit=200, window_seconds=7200)
    with pg_cluster.engine.begin() as connection:
        rows = [{'user': rate_actor.user_id, 'request': uuid4(), 'hash': 'a'*64, 'age': age}
                for age in [10000]*102 + [4000]]
        connection.execute(text('''
            INSERT INTO leny.admissions(user_id,request_id,fingerprint,admitted_at,outcome)
            VALUES(:user,:request,:hash,clock_timestamp()-make_interval(secs=>:age),'failed')
        '''), rows)
    limiter.admit(rate_actor, payload())
    with pg_cluster.engine.connect() as connection:
        assert connection.execute(text('SELECT count(*) FROM leny.admissions WHERE user_id=:id'),
                                  {'id': rate_actor.user_id}).scalar_one() == 4
        assert connection.execute(text("SELECT count(*) FROM leny.admissions WHERE user_id=:id AND admitted_at>clock_timestamp()-interval '7200 seconds'"),
                                  {'id': rate_actor.user_id}).scalar_one() == 2


def test_quota_uses_person_not_account(limiter, rate_actor):
    from app.services.leny_ollama import LenyError
    for _ in range(5):
        limiter.admit(rate_actor, payload())
    # Account recreation/change never resets the actual person's quota.
    same_person = SimpleNamespace(user_id=rate_actor.user_id, account_id=-1,
                                  event_id=str(uuid4()), ip_address=None, user_agent=None)
    with pytest.raises(LenyError) as exceeded:
        limiter.admit(same_person, payload())
    assert exceeded.value.code == 'LENY_RATE_LIMITED'
