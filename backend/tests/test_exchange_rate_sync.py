from datetime import date, datetime, timedelta
import asyncio
from decimal import Decimal
import json
from types import SimpleNamespace

import httpx
import pytest

from app.services.exchange_rate_history_service import LA_PAZ
from app.services.exchange_rate_provider import FacturaBoClient, ProviderError, parse_quote, validity_range
from app.services.exchange_rate_schedule import decide_sync, next_after_failure


DAY = date(2026, 11, 4)


def body(**changes):
    data = dict(usd_bob="12.0600", moneda_base="BOB", fuente="Banco Central de Bolivia", fuente_usd="tco_publico",
        url_fuente="https://www.bcb.gob.bo/bcb_tco_publico_ultima_cotizacion.php",
        vigencia_usd="VIGENCIA: MIÉRCOLES 4 DE NOVIEMBRE DE 2026", fecha_actualizacion="2026-11-04T04:05:10Z")
    data.update(changes)
    return json.dumps(dict(ok=True, datos=data, error=None)).encode()


def test_observed_dated_quote_is_decimal_and_large_changes_are_not_blocked():
    assert parse_quote(body(), DAY).value == Decimal("12.0600")
    assert parse_quote(body(usd_bob="99999999.9999"), DAY).value == Decimal("99999999.9999")


def test_observed_weekend_validity_includes_every_date_and_not_capture_date():
    phrase = "VIGENCIA: DEL SÁBADO 31 DE OCTUBRE DE 2026 AL MARTES 3 DE NOVIEMBRE DE 2026"
    assert validity_range(phrase) == (date(2026,10,31), date(2026,11,3))
    for day in (date(2026,10,31), date(2026,11,1), date(2026,11,3)):
        assert parse_quote(body(vigencia_usd=phrase), day).value == Decimal("12.0600")
    with pytest.raises(ProviderError) as error:
        parse_quote(body(vigencia_usd=phrase, fecha_actualizacion="2026-11-04T10:00:00Z"), DAY)
    assert error.value.state == "ERROR_VIGENCIA"


@pytest.mark.parametrize("phrase", [None,"", "2026-11-04", "VIGENCIA: MARTES 4 DE NOVIEMBRE DE 2026",
    "VIGENCIA: JUEVES 5 DE NOVIEMBRE DE 2026", "VIGENCIA: MIÉRCOLES 32 DE NOVIEMBRE DE 2026"])
def test_unverified_or_contradictory_validity_is_never_today(phrase):
    with pytest.raises(ProviderError) as error:
        parse_quote(body(vigencia_usd=phrase), DAY)
    assert error.value.state == "ERROR_VIGENCIA"


@pytest.mark.parametrize("changes", [{"usd_bob":"0"},{"usd_bob":"-1"},{"usd_bob":"NaN"},
    {"usd_bob":"Infinity"},{"usd_bob":True},{"usd_bob":"6.12345"},{"usd_bob":"100000000"},
    {"moneda_base":"USD"},{"fuente_usd":"parallel"},{"fuente":"Other"},
    {"url_fuente":"https://evil.example/bcb_tco_publico_ultima_cotizacion.php"}])
def test_invalid_values_and_sources_are_data_errors(changes):
    with pytest.raises(ProviderError) as error:
        parse_quote(body(**changes), DAY)
    assert error.value.state == "ERROR_DATOS"


@pytest.mark.parametrize("raw", [b'not json',b'{"ok":true,"ok":false}',b'{"ok":true,"datos":{"usd_bob":NaN}}', b'[]'])
def test_invalid_json_envelope(raw):
    with pytest.raises(ProviderError) as error:
        parse_quote(raw, DAY)
    assert error.value.state == "ERROR_DATOS"


@pytest.mark.parametrize("code", [301,302,429,500,503])
def test_http_errors_and_redirects_use_exactly_one_request(code):
    calls=[]
    def respond(request):
        calls.append(request)
        return httpx.Response(code, headers={"Location":"https://evil.example", "Content-Type":"application/json"})
    with pytest.raises(ProviderError) as error:
        FacturaBoClient(transport=httpx.MockTransport(respond)).fetch(DAY)
    assert error.value.state == "ERROR_API" and error.value.http_code == code
    assert len(calls) == 1 and str(calls[0].url).endswith("/history/2026-11-04")


def test_successful_transport_parses_real_contract():
    client = FacturaBoClient(transport=httpx.MockTransport(lambda request: httpx.Response(200,
        content=body(), headers={"Content-Type":"application/json"})))
    assert client.fetch(DAY).value == Decimal("12.0600")


def test_total_timeout_cancels_single_slow_request():
    calls=[]
    async def respond(request):
        calls.append(request)
        await asyncio.sleep(1)
        return httpx.Response(200,content=body(),headers={"Content-Type":"application/json"})
    with pytest.raises(ProviderError) as error:
        FacturaBoClient(timeout_seconds=0.01,transport=httpx.MockTransport(respond)).fetch(DAY)
    assert error.value.state=="ERROR_CONEXION" and len(calls)==1


@pytest.mark.parametrize("content,media_type", [(b'x'*65537,'application/json'),(body(),'text/html')], ids=["over_size_limit","wrong_media_type"])
def test_response_size_and_media_type_are_bounded(content,media_type):
    client=FacturaBoClient(transport=httpx.MockTransport(lambda request:httpx.Response(200,
        content=content,headers={"Content-Type":media_type})))
    with pytest.raises(ProviderError) as error:
        client.fetch(DAY)
    assert error.value.state=="ERROR_DATOS"


@pytest.mark.parametrize("exception", [httpx.ConnectError,httpx.ConnectTimeout,httpx.ReadTimeout])
def test_network_failure_is_not_a_claim_about_internet(exception):
    def fail(request):
        raise exception("synthetic", request=request)
    with pytest.raises(ProviderError) as error:
        FacturaBoClient(transport=httpx.MockTransport(fail)).fetch(DAY)
    assert error.value.state == "ERROR_CONEXION" and error.value.http_code is None


def instant(hour=5, minute=0, day=DAY):
    return datetime(day.year,day.month,day.day,hour,minute,tzinfo=LA_PAZ)


def row(target=DAY, *, state="ERROR_API", ordinal=1, at=None, next_at=None):
    return SimpleNamespace(fecha_objetivo=target, estado=state,numero_intento=ordinal,
        fecha_intento=at or instant(),proximo_intento=next_at)


def decide(rows=(), *, now=None, start=None, **extra):
    return decide_sync(rows, now=now or instant(), start_date=start or DAY, enabled=True, **extra)


def test_no_request_before_five_and_immediate_after_returning_online():
    assert decide(now=instant(4,59)).target is None
    assert decide().target == DAY
    assert decide(now=instant(13,17)).target == DAY


def test_success_stops_today_even_when_manual_may_be_current():
    assert decide([row(state="EXITOSO")]).target is None
    assert decide([row(state="EXITOSO")]).reason == "COMPLETE"


def test_old_day_recovery_consumes_the_same_execution_budget():
    rows=[row(state="EXITOSO"),row(DAY-timedelta(days=3),ordinal=10,state="EXITOSO")]
    result=decide(rows,start=DAY-timedelta(days=4))
    assert result.used == 10 and result.target is None
    assert result.next_at == instant(day=DAY+timedelta(days=1))


def test_hourly_failure_delay_then_next_day_resets_budget_at_five():
    rows=[row(next_at=instant(6))]
    assert decide(rows, now=instant(5,59)).target is None
    assert decide(rows, now=instant(6)).target == DAY
    ten=[row(ordinal=n) for n in range(1,11)]
    assert decide(ten).reason == "EXHAUSTED"
    assert decide(ten,now=instant(4,59,DAY+timedelta(days=1))).target is None
    assert decide(ten,now=instant(day=DAY+timedelta(days=1))).target == DAY+timedelta(days=1)


def test_historical_failure_is_skipped_today_and_remaining_dates_continue_after_wait():
    start=DAY-timedelta(days=3)
    rows=[row(state="EXITOSO"),row(start,ordinal=2,next_at=instant(6))]
    assert decide(rows,start=start).target is None
    assert decide(rows,start=start,now=instant(6)).target == start+timedelta(days=1)


def test_prolonged_failure_counts_only_closed_dates_since_start():
    assert decide(start=DAY-timedelta(days=2)).missing_days == 2
    assert decide(start=DAY-timedelta(days=3)).missing_days == 3
    assert decide([row(DAY-timedelta(days=1),state="EXITOSO")],start=DAY-timedelta(days=3)).missing_days == 0
    assert decide([row(state="EXITOSO")],start=DAY-timedelta(days=3)).missing_days == 0


def test_initiated_reservation_blocks_calls_and_shutdown_hours_are_not_attempts():
    result=decide([row(state="INICIADO")],start=DAY-timedelta(days=30))
    assert result.target is None and result.used == 1 and result.backlog == 30


def test_utc_server_clock_and_late_failure_use_bolivian_calendar():
    assert decide(now=instant().astimezone(__import__('datetime').timezone.utc)).target == DAY
    assert next_after_failure(instant(23,30)) == instant(day=DAY+timedelta(days=1))


def test_disabled_paused_and_future_start_never_query():
    assert decide_sync([],now=instant(),start_date=DAY,enabled=False).target is None
    assert decide(available=False).reason == "PAUSED"
    assert decide(start=DAY+timedelta(days=1)).reason == "NOT_STARTED"
