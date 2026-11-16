"""TC-02 notices only on the manifest-verified isolated PostgreSQL fixture."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select, text

from test_exchange_rate_history import tc


LA_PAZ = ZoneInfo("America/La_Paz")


def _failure(state, *, number=1, day=None, ordinal=1):
    from app.models.exchange_rate_record import TipoCambioRegistro
    now = datetime.now(LA_PAZ)
    day = day or now.date()
    midnight = datetime.combine(day, datetime.min.time(), LA_PAZ)
    executed = midnight + timedelta(hours=5, minutes=number)
    if day == now.date():
        executed = max(midnight, min(executed, now - timedelta(minutes=1)))
    item = TipoCambioRegistro(moneda_id=state.usd.id, fecha_objetivo=day,
        numero_intento=ordinal, fecha_intento=executed,
        estado="ERROR_API", codigo_http=503, proveedor="FACTURA_BO_BCB")
    state.db.add(item)
    state.db.flush()
    return item


def _own_notices(state):
    from app.core.notification_catalog import EXCHANGE_RATE_NOTIFICATION_TYPES
    from app.models.notification import Notificacion
    return list(state.db.scalars(select(Notificacion).where(
        Notificacion.usuario_id == state.admin.usuario_id, Notificacion.tipo.in_(EXCHANGE_RATE_NOTIFICATION_TYPES))))


def test_reconciliation_deduplicates_read_and_resolved_events_without_committing_or_auditing(tc, monkeypatch):
    from app.services.exchange_rate_notification_service import reconcile_exchange_rate_notifications
    from app.models.notification import Notificacion
    now = datetime.now(LA_PAZ)
    failure = _failure(tc)
    before = tc.db.scalar(text("SELECT count(*) FROM auditoria_sistema"))
    commit = Mock(side_effect=AssertionError("Notice reconciliation must not commit its caller's transaction"))
    monkeypatch.setattr(tc.db, "commit", commit)
    reconcile_exchange_rate_notifications(tc.db, now=now, start_date=now.date())
    rows = _own_notices(tc)
    assert len(rows) == 1 and rows[0].id_referencia == failure.id
    rows[0].leida, rows[0].fecha_leida = True, now
    rows[0].resuelta, rows[0].fecha_resuelta = True, now
    tc.db.flush()
    before_id = rows[0].id
    reconcile_exchange_rate_notifications(tc.db, now=now + timedelta(minutes=1), start_date=now.date())
    again = _own_notices(tc)
    assert len(again) == 1 and again[0].id == before_id and again[0].leida and again[0].resuelta
    assert tc.db.scalar(text("SELECT count(*) FROM auditoria_sistema")) == before
    assert tc.db.scalar(select(func.count()).select_from(Notificacion).where(
        Notificacion.usuario_id == tc.cashier.usuario_id, Notificacion.tipo.like("TC_SYNC_%"))) == 0
    commit.assert_not_called()


def test_prolonged_notice_is_one_per_episode_and_first_error_is_one_per_execution_day(tc):
    from app.services.exchange_rate_notification_service import reconcile_exchange_rate_notifications
    now = datetime.now(LA_PAZ)
    start = now.date() - timedelta(days=3)
    anchor = _failure(tc, day=start)
    _failure(tc, day=now.date())
    reconcile_exchange_rate_notifications(tc.db, now=now, start_date=start)
    extended = now + timedelta(days=1)
    _failure(tc, day=extended.date())
    reconcile_exchange_rate_notifications(tc.db, now=extended, start_date=start)
    rows = _own_notices(tc)
    prolonged = [row for row in rows if row.tipo == "TC_SYNC_PROLONGADO"]
    daily = [row for row in rows if row.tipo == "TC_SYNC_PRIMER_ERROR"]
    assert len(prolonged) == 1 and prolonged[0].id_referencia == anchor.id
    assert len(daily) == 2


def test_success_resolves_failure_notices_and_combines_recovery_without_duplicate(tc):
    from app.models.exchange_rate_record import TipoCambioRegistro
    from app.services.exchange_rate_history_service import insert_rate
    from app.services.exchange_rate_notification_service import reconcile_exchange_rate_notifications
    now = datetime.now(LA_PAZ)
    failure = _failure(tc)
    reconcile_exchange_rate_notifications(tc.db, now=now, start_date=now.date())
    rate = insert_rate(tc.db, moneda_id=tc.usd.id, valor_bob="12.0600", usuario_id=None,
        origen="AUTOMATICO", fuente="BCB_VIA_FACTURA_BO", fec_consulta=now, operativo=True)
    success = TipoCambioRegistro(moneda_id=tc.usd.id, tipo_cambio_id=rate.id, fecha_objetivo=now.date(),
        numero_intento=2, fecha_intento=now, estado="EXITOSO", codigo_http=200, proveedor="FACTURA_BO_BCB")
    tc.db.add(success)
    tc.db.flush()
    reconcile_exchange_rate_notifications(tc.db, now=now, start_date=now.date())
    reconcile_exchange_rate_notifications(tc.db, now=now, start_date=now.date())
    rows = _own_notices(tc)
    assert len(rows) == 2
    assert next(row for row in rows if row.id_referencia == failure.id and row.tipo == "TC_SYNC_PRIMER_ERROR").resuelta
    recovered = next(row for row in rows if row.tipo == "TC_SYNC_EXITOSO")
    assert "RECUPERÓ" in recovered.mensaje and recovered.id_referencia == rate.id


def test_historical_failure_is_not_resolved_until_its_own_goal_is_recovered(tc):
    from app.models.exchange_rate_record import TipoCambioRegistro
    from app.services.exchange_rate_history_service import insert_rate
    from app.services.exchange_rate_notification_service import reconcile_exchange_rate_notifications
    now = datetime.now(LA_PAZ)
    yesterday = now.date() - timedelta(days=1)
    live = insert_rate(tc.db, moneda_id=tc.usd.id, valor_bob="12.0600", usuario_id=None,
        origen="AUTOMATICO", fuente="BCB_VIA_FACTURA_BO", fec_consulta=now, operativo=True)
    tc.db.add(TipoCambioRegistro(moneda_id=tc.usd.id, tipo_cambio_id=live.id, fecha_objetivo=now.date(),
        numero_intento=1, fecha_intento=now, estado="EXITOSO", codigo_http=200, proveedor="FACTURA_BO_BCB"))
    failed = _failure(tc, day=yesterday, ordinal=2)
    failed.fecha_intento = now
    tc.db.flush()
    reconcile_exchange_rate_notifications(tc.db, now=now, start_date=yesterday)
    notice = next(row for row in _own_notices(tc) if row.tipo == "TC_SYNC_PRIMER_ERROR")
    assert not notice.resuelta and f"CORRESPONDIENTE AL {yesterday:%d/%m/%Y}" in notice.mensaje
    historical = insert_rate(tc.db, moneda_id=tc.usd.id, valor_bob="12.0900", usuario_id=None,
        origen="AUTOMATICO", fuente="BCB_VIA_FACTURA_BO", fec_consulta=now, operativo=False)
    tc.db.add(TipoCambioRegistro(moneda_id=tc.usd.id, tipo_cambio_id=historical.id, fecha_objetivo=yesterday,
        numero_intento=3, fecha_intento=now, estado="EXITOSO", codigo_http=200, proveedor="FACTURA_BO_BCB"))
    tc.db.flush()
    reconcile_exchange_rate_notifications(tc.db, now=now, start_date=yesterday)
    assert notice.resuelta and live.activo and not historical.activo


def test_exadmin_cannot_read_or_modify_old_technical_notices_but_retains_other_notifications(tc):
    from app.models.notification import Notificacion, PreferenciaNotificacion
    from app.models.role import Rol
    from app.schemas.notification import NotificationQueryFilters
    from app.services.exchange_rate_notification_service import reconcile_exchange_rate_notifications
    from app.services.notification_query_service import (
        get_notification_detail, get_notification_summary, list_notifications, mark_notification_read,
        mark_all_notifications_read, get_notification_report_summary,
    )
    from app.services.notification_delivery_service import claim_desktop_notifications
    now = datetime.now(LA_PAZ)
    _failure(tc)
    reconcile_exchange_rate_notifications(tc.db, now=now, start_date=now.date())
    private = _own_notices(tc)[0]
    private.resuelta, private.fecha_resuelta = True, now
    another = Notificacion(usuario_id=tc.admin.usuario_id, tipo="SISTEMA", titulo="QA", mensaje="QA",
        fecha=now, revision_fecha=now, revision=1, leida=False, resuelta=False)
    tc.db.add(another)
    tc.db.add(PreferenciaNotificacion(usuario_id=tc.admin.usuario_id, escritorio_habilitado_desde=now - timedelta(minutes=1)))
    tc.admin.rol = tc.db.get(Rol, tc.cashier.rol_id)
    tc.db.flush()
    for operation in (lambda: get_notification_detail(tc.db, notification_id=private.id, account=tc.admin),
                      lambda: mark_notification_read(tc.db, notification_id=private.id, account=tc.admin, revision=1)):
        with pytest.raises(HTTPException) as denied:
            operation()
        assert denied.value.status_code == 404
    own = list_notifications(tc.db, account=tc.admin, filters=NotificationQueryFilters())
    assert [row.id for row in own.items] == [another.id]
    assert get_notification_summary(tc.db, account=tc.admin).unread_count == 1
    report = get_notification_report_summary(tc.db, account=tc.admin)
    assert "TC_SYNC_PRIMER_ERROR" not in {bucket.label for bucket in report.by_type}
    # Make the TC notice open again to cover the desktop/read-all paths too.
    private.resuelta, private.fecha_resuelta = False, None
    tc.db.flush()
    desktop = claim_desktop_notifications(tc.db, account=tc.admin)
    assert [row.id for row in desktop.items] == [another.id]
    mark_all_notifications_read(tc.db, account=tc.admin)
    assert not private.leida
