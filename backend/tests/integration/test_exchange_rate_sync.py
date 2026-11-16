"""TC02 integration: manifest-protected PG only, simulated clock and provider."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from threading import Barrier
from types import SimpleNamespace

from fastapi import HTTPException
import pytest
from sqlalchemy import select, text, func
from sqlalchemy.orm import Session

from test_exchange_rate_history import tc, tc_api, _manual, _today, _setup
from app.models.exchange_rate import TipoCambioMoneda
from app.models.exchange_rate_record import TipoCambioRegistro
from app.services.exchange_rate_history_service import LA_PAZ, begin_attempt
from app.services.exchange_rate_provider import ProviderError, ProviderQuote
from app.services.exchange_rate_sync_service import run_sync, sync_job_lock
from app.services.exchange_rate_sync_query import sync_state


class Clock:
    def __init__(self, day=None, hour=5):
        day=day or _today()
        self.value=datetime(day.year,day.month,day.day,hour,tzinfo=LA_PAZ)
    def __call__(self):
        return self.value
    def advance(self, **kwargs):
        self.value += timedelta(**kwargs)


class Provider:
    def __init__(self, *, error=None, value="12.0600"):
        self.error,self.value,self.calls=error,value,[]
    def fetch(self, target):
        self.calls.append(target)
        if self.error:
            raise ProviderError(self.error, 503 if self.error == "ERROR_API" else None)
        return ProviderQuote(Decimal(self.value))


def config(start=None, enabled=True):
    return SimpleNamespace(exchange_rate_sync_enabled=enabled,exchange_rate_sync_start_date=start or _today(),
        exchange_rate_sync_http_timeout_seconds=30,exchange_rate_sync_reconcile_seconds=120)


def rates(tc):
    tc.db.expire_all()
    return list(tc.db.scalars(select(TipoCambioMoneda).where(TipoCambioMoneda.moneda_id==tc.usd.id)))


def test_first_valid_quote_is_active_and_same_day_is_idempotent(tc):
    previous=_manual(tc)
    provider,clock=Provider(),Clock()
    before=tc.db.scalar(text("SELECT count(*) FROM auditoria_sistema"))
    result=run_sync(tc.db,config=config(),provider=provider,clock=clock)
    assert result["successes"] == 1 and provider.calls == [_today()]
    assert not tc.db.get(TipoCambioMoneda,previous.id).activo
    active=next(r for r in rates(tc) if r.activo)
    assert active.origen == "AUTOMATICO" and active.usuario_id is None and active.valor_bob==Decimal("12.0600")
    assert run_sync(tc.db,config=config(),provider=provider,clock=clock)["requests"] == 0
    assert len(provider.calls)==1
    assert tc.db.scalar(text("SELECT count(*) FROM auditoria_sistema"))==before


def test_same_value_on_next_day_creates_distinct_official_rows(tc):
    clock,provider=Clock(),Provider(value="6.9600")
    settings=config()
    run_sync(tc.db,config=settings,provider=provider,clock=clock)
    clock.advance(days=1)
    run_sync(tc.db,config=settings,provider=provider,clock=clock)
    rows=list(tc.db.scalars(select(TipoCambioRegistro).where(TipoCambioRegistro.moneda_id==tc.usd.id,
        TipoCambioRegistro.estado=="EXITOSO")))
    assert len(rows)==2 and rows[0].tipo_cambio_id != rows[1].tipo_cambio_id
    assert sum(r.activo for r in rates(tc))==1


@pytest.mark.parametrize("state", ["ERROR_CONEXION","ERROR_API","ERROR_DATOS","ERROR_VIGENCIA"])
def test_errors_preserve_previous_active_and_do_not_call_again_before_one_hour(tc,state):
    previous=_manual(tc)
    clock,provider=Clock(),Provider(error=state)
    result=run_sync(tc.db,config=config(),provider=provider,clock=clock)
    assert result["reason"]==state and len(provider.calls)==1
    assert tc.db.get(TipoCambioMoneda,previous.id).activo
    clock.advance(minutes=59)
    assert run_sync(tc.db,config=config(),provider=provider,clock=clock)["requests"]==0
    clock.advance(minutes=1)
    assert run_sync(tc.db,config=config(),provider=provider,clock=clock)["requests"]==1


def test_ten_http_failures_limit_and_new_day_budget_at_five(tc):
    clock,provider=Clock(),Provider(error="ERROR_API")
    for ordinal in range(1,11):
        result=run_sync(tc.db,config=config(),provider=provider,clock=clock)
        assert result["requests"]==1
        clock.advance(hours=1)
    assert len(provider.calls)==10
    assert run_sync(tc.db,config=config(),provider=provider,clock=clock)["requests"]==0
    clock.value=Clock(day=_today()+timedelta(days=1),hour=4).value
    assert run_sync(tc.db,config=config(),provider=provider,clock=clock)["requests"]==0
    clock.advance(hours=1)
    assert run_sync(tc.db,config=config(),provider=provider,clock=clock)["requests"]==1
    last=tc.db.scalar(select(TipoCambioRegistro).where(TipoCambioRegistro.moneda_id==tc.usd.id).order_by(TipoCambioRegistro.id.desc()).limit(1))
    assert last.numero_intento==1


def test_recovery_prioritizes_today_and_old_days_are_inactive(tc):
    start=_today()-timedelta(days=2)
    clock,provider=Clock(),Provider()
    result=run_sync(tc.db,config=config(start),provider=provider,clock=clock)
    assert result["requests"]==3 and provider.calls==[_today(),start,start+timedelta(days=1)]
    rows=list(tc.db.scalars(select(TipoCambioRegistro).where(TipoCambioRegistro.moneda_id==tc.usd.id)))
    for row in rows:
        assert tc.db.get(TipoCambioMoneda,row.tipo_cambio_id).activo == (row.fecha_objetivo==_today())
    assert min(provider.calls)==start


def test_large_backlog_is_recovered_over_multiple_days_with_shared_budget(tc):
    start=_today()-timedelta(days=20)
    clock,provider=Clock(),Provider()
    assert run_sync(tc.db,config=config(start),provider=provider,clock=clock)["requests"]==10
    assert run_sync(tc.db,config=config(start),provider=provider,clock=clock)["requests"]==0
    clock.advance(days=1)
    assert run_sync(tc.db,config=config(start),provider=provider,clock=clock)["requests"]==10
    assert len(provider.calls)==20 and sum(r.activo for r in rates(tc))==1


def test_missing_historical_day_is_not_invented_and_other_days_continue_after_wait(tc):
    before=len([r for r in rates(tc) if r.origen=="AUTOMATICO"])
    start=_today()-timedelta(days=2)
    clock,provider=Clock(),Provider()
    original=provider.fetch
    def fetch(target):
        if target==start:
            provider.calls.append(target)
            raise ProviderError("ERROR_VIGENCIA",200)
        return original(target)
    provider.fetch=fetch
    run_sync(tc.db,config=config(start),provider=provider,clock=clock)
    assert provider.calls==[_today(),start]
    clock.advance(hours=1)
    run_sync(tc.db,config=config(start),provider=provider,clock=clock)
    assert provider.calls==[_today(),start,start+timedelta(days=1)]
    assert len([r for r in rates(tc) if r.origen=="AUTOMATICO"])-before==2


def test_manual_after_official_remains_until_next_valid_day(tc):
    clock,provider=Clock(),Provider()
    run_sync(tc.db,config=config(),provider=provider,clock=clock)
    manual=_manual(tc,"7.0100")
    run_sync(tc.db,config=config(),provider=provider,clock=clock)
    assert len(provider.calls)==1 and tc.db.get(TipoCambioMoneda,manual.id).activo
    assert sync_state(tc.db,config=config(),now=clock())["status"]=="MANUAL_AFTER_OFFICIAL"
    clock.advance(days=1)
    run_sync(tc.db,config=config(),provider=provider,clock=clock)
    tc.db.expire_all()
    assert not tc.db.get(TipoCambioMoneda,manual.id).activo


def test_interrupted_initiated_is_reconciled_without_refunding_ordinal(tc):
    clock,provider=Clock(),Provider()
    item=begin_attempt(tc.db,moneda_id=tc.usd.id,fecha_objetivo=_today(),now=clock())
    assert run_sync(tc.db,config=config(),provider=provider,clock=clock)["requests"]==0
    clock.advance(seconds=121)
    result=run_sync(tc.db,config=config(),provider=provider,clock=clock)
    assert result["reconciled"]==1 and not provider.calls
    assert tc.db.get(TipoCambioRegistro,item.id).estado=="ERROR_EJECUCION"
    clock.advance(hours=1)
    run_sync(tc.db,config=config(),provider=provider,clock=clock)
    last=tc.db.scalar(select(TipoCambioRegistro).where(TipoCambioRegistro.moneda_id==tc.usd.id).order_by(TipoCambioRegistro.id.desc()).limit(1))
    assert last.numero_intento==2


def test_disabled_and_backup_do_not_reserve_or_call(tc):
    clock,provider=Clock(),Provider()
    assert run_sync(tc.db,config=config(enabled=False),provider=provider,clock=clock)["requests"]==0
    assert run_sync(tc.db,config=config(),provider=provider,clock=clock,backup_active=lambda:True)["reason"]=="BACKUP_ACTIVE"
    assert not provider.calls


def test_midnight_between_reservation_and_http_does_not_send_a_request(tc):
    clock,provider=Clock(hour=23),Provider()
    clock.value=clock.value.replace(minute=59,second=59)
    checks=0
    def check():
        nonlocal checks
        checks+=1
        if checks==2:
            clock.advance(seconds=2)
    result=run_sync(tc.db,config=config(),provider=provider,clock=clock,check_lease=check)
    assert not provider.calls and result["reason"]=="CALENDAR_CHANGED_BEFORE_HTTP"
    record=tc.db.scalar(select(TipoCambioRegistro).where(TipoCambioRegistro.moneda_id==tc.usd.id).order_by(TipoCambioRegistro.id.desc()).limit(1))
    assert record.estado=="ERROR_EJECUCION" and record.numero_intento==1


def test_lease_loss_after_reservation_never_calls_provider(tc):
    provider,clock=Provider(),Clock()
    count=0
    def check():
        nonlocal count
        count+=1
        if count>=2:
            raise RuntimeError("synthetic lost connection")
    with pytest.raises(RuntimeError):
        run_sync(tc.db,config=config(),provider=provider,clock=clock,check_lease=check)
    assert not provider.calls
    record=tc.db.scalar(select(TipoCambioRegistro).where(TipoCambioRegistro.moneda_id==tc.usd.id).order_by(TipoCambioRegistro.id.desc()).limit(1))
    assert record.estado=="INICIADO" and record.numero_intento==1


def test_no_active_usd_reports_intervention_but_does_not_block_automatic_repair(tc):
    for rate in rates(tc):
        rate.activo=False
    tc.db.flush()
    clock,provider=Clock(),Provider()
    assert sync_state(tc.db,config=config(),now=clock())["status"]=="NO_ACTIVE_RATE"
    run_sync(tc.db,config=config(),provider=provider,clock=clock)
    state=sync_state(tc.db,config=config(),now=clock())
    assert state["status"]=="UPDATED" and state["last_official_date"]==_today()


def test_direct_api_permissions_and_paginated_records_are_read_only(tc,tc_api,monkeypatch):
    client,headers=tc_api
    from app.core.config import settings
    monkeypatch.setattr(settings,"exchange_rate_sync_enabled",True)
    monkeypatch.setattr(settings,"exchange_rate_sync_start_date",_today())
    run_sync(tc.db,config=config(),provider=Provider(),clock=Clock())
    base="/api/v1/monedas/tipos-cambio/sincronizacion"
    admin=headers(tc.admin)
    cashier=headers(tc.cashier)
    response=client.get(base+"/estado",headers=cashier)
    assert response.status_code==200 and isinstance(response.json()["operational_rate"]["valor_bob"],str)
    assert client.get(base+"/registros",headers=cashier).status_code==403
    response=client.get(base+"/registros?page=1&page_size=1",headers=admin)
    assert response.status_code==200 and response.json()["total"]==1
    record=response.json()["items"][0]
    assert client.get(base+"/registros/"+str(record["id"]),headers=admin).status_code==200
    assert client.get(base+"/registros/"+str(record["id"]),headers=cashier).status_code==403
    assert client.get(base+"/registros?date_from=2026-11-02&date_to=2026-11-01",headers=admin).status_code==422
    assert client.get(base+"/registros").status_code==401


def test_two_logical_sync_workers_cannot_hold_the_lock_together(pg_cluster):
    barrier=Barrier(2)
    results=[]
    def worker():
        with sync_job_lock(pg_cluster.engine) as check:
            results.append(check is not None)
            barrier.wait(timeout=10)
            if check:
                check()
    with ThreadPoolExecutor(max_workers=2) as pool:
        a,b=pool.submit(worker),pool.submit(worker)
        a.result(timeout=15);b.result(timeout=15)
    assert sorted(results)==[False,True]


def test_official_reporting_uses_target_not_consultation_date(tc):
    from app.services.module_report_service import get_currencies_report
    start=_today()-timedelta(days=2)
    run_sync(tc.db,config=config(start),provider=Provider(),clock=Clock())
    report=get_currencies_report(tc.db,currency_id=tc.usd.id)
    assert [r["label"] for r in report.series["official_exchange_rate_series"]]==[
        (start+timedelta(days=n)).isoformat() for n in range(3)]
