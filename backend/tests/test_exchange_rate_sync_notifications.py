"""TC-02 notice semantics without application settings, provider or database."""
from datetime import date, datetime, timedelta
from types import SimpleNamespace
import sys
from zoneinfo import ZoneInfo

import casbin
import pytest

from app.core.notification_catalog import (
    EXCHANGE_RATE_NOTIFICATION_TYPES, build_notification_action_path, can_resolve_manually, recipient_roles,
)
from app.core.permissions import build_permissions_for_role
from app.services.exchange_rate_notification_service import _events, can_view_exchange_rate_notifications


LA_PAZ = ZoneInfo("America/La_Paz")
TODAY = date(2026, 11, 4)
NOW = datetime(2026, 11, 4, 16, tzinfo=LA_PAZ)


def record(identifier=1, *, target=TODAY, executed=None, state="ERROR_CONEXION", ordinal=1, rate_id=None):
    return SimpleNamespace(id=identifier, fecha_objetivo=target,
        fecha_intento=executed or datetime.combine(target, datetime.min.time(), LA_PAZ) + timedelta(hours=5),
        estado=state, numero_intento=ordinal, tipo_cambio_id=rate_id)


def events(records, *, now=NOW, start=TODAY):
    return _events(records, now=now, start_date=start)[0]


def test_first_error_daily_uses_a_stable_execution_day_reference():
    first = record(41)
    later = record(42, ordinal=2, target=TODAY - timedelta(days=1), executed=first.fecha_intento + timedelta(hours=1))
    result = events([later, first])
    assert len(result) == 1 and result[0]["tipo"] == "TC_SYNC_PRIMER_ERROR"
    assert result[0]["record_id"] == 41


def test_inflight_tenth_request_is_not_yet_an_exhaustion_failure():
    assert not events([record(10, ordinal=10, state="INICIADO")])
    assert "TC_SYNC_AGOTADO" in {event["tipo"] for event in events([record(10, ordinal=10)])}


def test_historical_success_does_not_claim_that_today_was_updated():
    previous = record(9, target=TODAY - timedelta(days=1), executed=NOW - timedelta(minutes=2), state="EXITOSO", rate_id=19)
    assert "TC_SYNC_EXITOSO" not in {event["tipo"] for event in events([previous], start=TODAY - timedelta(days=5))}


def test_historical_failure_notice_names_its_objective_instead_of_claiming_today_failed():
    goal = TODAY - timedelta(days=2)
    failed = record(4, target=goal, executed=NOW)
    result = events([failed], start=goal)
    assert f"correspondiente al {goal:%d/%m/%Y}" in result[0]["message"]


@pytest.mark.parametrize("closed_days,expected", [(0, False), (1, False), (2, False), (3, True), (4, True)])
def test_prolonged_failure_counts_closed_calendar_days_only(closed_days, expected):
    result = events([record(1)], start=TODAY - timedelta(days=closed_days))
    assert ("TC_SYNC_PROLONGADO" in {event["tipo"] for event in result}) is expected


def test_prolonged_episode_reuses_its_reference_on_following_days():
    origin = record(5, target=TODAY - timedelta(days=3))
    first = next(event for event in events([origin], start=origin.fecha_objetivo) if event["tipo"] == "TC_SYNC_PROLONGADO")
    tomorrow = NOW + timedelta(days=1)
    later = next(event for event in events([origin, record(6, target=tomorrow.date())], now=tomorrow,
        start=origin.fecha_objetivo) if event["tipo"] == "TC_SYNC_PROLONGADO")
    assert first["record_id"] == later["record_id"] == 5


def test_success_combines_recovery_and_suppresses_exhaustion_and_prolonged_notice():
    first = record(1, executed=NOW - timedelta(hours=1))
    success = record(2, executed=NOW, state="EXITOSO", ordinal=10, rate_id=70)
    result = events([first, success], start=TODAY - timedelta(days=4))
    assert {event["tipo"] for event in result} == {"TC_SYNC_PRIMER_ERROR", "TC_SYNC_EXITOSO"}
    message = next(event for event in result if event["tipo"] == "TC_SYNC_EXITOSO")
    assert message["record_id"] == 70 and "recuperó" in message["message"]
    assert "manual posterior" in message["message"]


def test_catalog_is_admin_only_read_only_and_has_module_specific_links():
    for kind in EXCHANGE_RATE_NOTIFICATION_TYPES:
        assert recipient_roles(kind) == {"ADMIN"}
        assert not can_resolve_manually(kind)
    assert build_notification_action_path("TIPO_CAMBIO_REGISTROS", 7) == "/app/monedas/tipos-cambio/registros?record_id=7"
    assert build_notification_action_path("TIPO_CAMBIO_MONEDA", 8) == "/app/monedas/tipos-cambio?rate_id=8"
    for code in ("CAJA", "MODISTA", "INV_BOUTIQUE", "INV_TALLER", "DOC"):
        assert not set(build_permissions_for_role(code)) & {"exchange_rates_sync:list", "exchange_rates_sync:view"}


def account(code="ADMIN", **changes):
    result = SimpleNamespace(is_active=True, usuario=SimpleNamespace(activo=True), rol=SimpleNamespace(activo=True, codigo=code))
    result.__dict__.update(changes)
    return result


def test_effective_admin_checks_real_casbin_and_rejects_other_roles_even_with_policy(monkeypatch):
    from pathlib import Path
    security = Path(__file__).resolve().parents[1] / "app/security"
    enforcer = casbin.Enforcer(str(security / "model.conf"), str(security / "policy.csv"))
    monkeypatch.setitem(sys.modules, "app.api.router", SimpleNamespace(enforcer=enforcer))
    assert can_view_exchange_rate_notifications(account())
    enforcer.remove_policy("ADMIN", "exchange_rates_sync:view", "use")
    assert not can_view_exchange_rate_notifications(account())
    for permission in ("exchange_rates_sync:list", "exchange_rates_sync:view"):
        enforcer.add_policy("CAJA", permission, "use")
    assert not can_view_exchange_rate_notifications(account("CAJA"))


@pytest.mark.parametrize("changes", [{"is_active": False}, {"usuario": SimpleNamespace(activo=False)},
    {"rol": SimpleNamespace(codigo="ADMIN", activo=False)}])
def test_disabled_account_person_or_role_cannot_receive_technical_notices(changes):
    assert not can_view_exchange_rate_notifications(account(**changes))
