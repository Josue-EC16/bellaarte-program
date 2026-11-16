"""One bounded scheduler invocation; each external GET has one durable ordinal."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.services.exchange_rate_history_service import LA_PAZ, begin_attempt, finish_failure, finish_success
from app.services.exchange_rate_provider import FacturaBoClient, ProviderError
from app.services.exchange_rate_schedule import decide_sync, next_after_failure
from app.services.exchange_rate_sync_query import automatic_records, usd_currency


LOCK_NAMESPACE, LOCK_JOB = 184914, 2


@contextmanager
def sync_job_lock(engine):
    with engine.connect() as connection:
        acquired = connection.scalar(text("SELECT pg_try_advisory_lock(:namespace,:job)"), {"namespace":LOCK_NAMESPACE,"job":LOCK_JOB})
        connection.commit()
        backend_pid = connection.scalar(text("SELECT pg_backend_pid()"))
        connection.commit()
        def check():
            if not acquired or connection.closed or connection.invalidated:
                raise RuntimeError("SYNC_COORDINATION_LOST")
            if connection.scalar(text("SELECT pg_backend_pid()")) != backend_pid:
                raise RuntimeError("SYNC_COORDINATION_LOST")
            connection.commit()
        try:
            yield check if acquired else None
        finally:
            if acquired:
                try:
                    connection.execute(text("SELECT pg_advisory_unlock(:namespace,:job)"), {"namespace":LOCK_NAMESPACE,"job":LOCK_JOB})
                    connection.commit()
                except Exception:
                    connection.invalidate()


def run_sync(db, *, config, provider=None, clock=None, check_lease=None, backup_active=None):
    clock = clock or (lambda: datetime.now(timezone.utc))
    check_lease = check_lease or (lambda: None)
    backup_active = backup_active or (lambda: False)
    now = clock()
    result = {"status":"skipped", "reason":"DISABLED", "requests":0, "successes":0, "reconciled":0}
    if not config.exchange_rate_sync_enabled:
        return result
    if config.exchange_rate_sync_start_date is None:
        raise RuntimeError("SYNC_START_DATE_REQUIRED")
    if backup_active():
        return dict(result, reason="BACKUP_ACTIVE")
    from app.services.exchange_rate_notification_service import reconcile_exchange_rate_notifications
    provider = provider or FacturaBoClient(timeout_seconds=config.exchange_rate_sync_http_timeout_seconds)
    def notify():
        reconcile_exchange_rate_notifications(db, now=clock(), start_date=config.exchange_rate_sync_start_date)
        db.commit()
    currency = usd_currency(db)
    if currency is None:
        return dict(result, reason="USD_UNAVAILABLE")
    currency_id = currency.id
    rows = automatic_records(db, currency_id, config.exchange_rate_sync_start_date)
    for item in rows:
        if item.estado == "INICIADO" and item.fecha_intento + timedelta(seconds=config.exchange_rate_sync_reconcile_seconds) <= now:
            check_lease()
            finish_failure(db, attempt_id=item.id, estado="ERROR_EJECUCION", proximo_intento=next_after_failure(now))
            result["reconciled"] += 1
    notify()
    for _ in range(10):
        check_lease()
        if backup_active():
            result["reason"] = "BACKUP_ACTIVE"
            break
        db.expire_all()
        currency = usd_currency(db)
        rows = automatic_records(db, currency_id, config.exchange_rate_sync_start_date)
        decision = decide_sync(rows, now=clock(), start_date=config.exchange_rate_sync_start_date,
            enabled=True, available=bool(currency and currency.habilitado and not currency.es_base))
        result["reason"] = decision.reason
        if decision.target is None:
            break
        item = begin_attempt(db, moneda_id=currency_id, fecha_objetivo=decision.target, now=clock())
        # Stop before HTTP if coordination was lost. The durable reservation is
        # later reconciled, never refunded into a potentially duplicate request.
        check_lease()
        started = clock()
        if (started.astimezone(LA_PAZ).date() != item.fecha_intento.astimezone(LA_PAZ).date()
                or started.astimezone(LA_PAZ).hour < 5):
            finish_failure(db, attempt_id=item.id, estado="ERROR_EJECUCION",
                proximo_intento=next_after_failure(started))
            result["reason"] = "CALENDAR_CHANGED_BEFORE_HTTP"
            notify()
            break
        result["requests"] += 1
        try:
            quote = provider.fetch(decision.target)
            check_lease()
            captured = clock()
            finish_success(db, attempt_id=item.id, valor_bob=quote.value, fec_consulta=captured,
                codigo_http=quote.http_code, now=captured)
            result["successes"] += 1
        except ProviderError as error:
            check_lease()
            finish_failure(db, attempt_id=item.id, estado=error.state, codigo_http=error.http_code,
                proximo_intento=next_after_failure(clock()))
            result["reason"] = error.state
            notify()
            break
        except Exception:
            db.rollback()
            # A failed lease must not permit another write or another request.
            check_lease()
            finish_failure(db, attempt_id=item.id, estado="ERROR_EJECUCION",
                proximo_intento=next_after_failure(clock()))
            notify()
            raise
        notify()
    if result["requests"] or result["reconciled"]:
        result["status"] = "ok"
    return result
