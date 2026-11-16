"""ADMIN-only exchange-rate notices derived from durable TC-01 records.

No commits, provider requests, general audit hooks, or new persistence. The
coordinator commits and can reconcile a crash between a result and its notices.
"""
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

import casbin
from sqlalchemy import select, true, update
from sqlalchemy.orm import Session

from app.core.notification_catalog import EXCHANGE_RATE_NOTIFICATION_TYPES
from app.models.boutique_enums import PrioridadNotificacionEnum
from app.models.currency import Moneda
from app.models.exchange_rate_record import TipoCambioRegistro
from app.models.notification import Notificacion
from app.services.notification_sync_service import _get_active_accounts_for_roles, create_notification_for_user


LA_PAZ = ZoneInfo("America/La_Paz")
PROVIDER = "FACTURA_BO_BCB"
FAILURE_NOTICE_TYPES = EXCHANGE_RATE_NOTIFICATION_TYPES - {"TC_SYNC_EXITOSO"}


@lru_cache(maxsize=2)
def _file_enforcer(model_path: str, policy_path: str, _policy_revision: int):
    # A standalone scheduler must not import the API router: importing it can
    # synchronize policy.csv. Reading the reviewed policy is sufficient here.
    return casbin.Enforcer(model_path, policy_path)


def can_view_exchange_rate_notifications(account) -> bool:
    """Check the current effective role as well as its real Casbin permissions."""
    role, user = getattr(account, "rol", None), getattr(account, "usuario", None)
    if not (getattr(account, "is_active", False) and getattr(user, "activo", False)
            and getattr(role, "activo", False) and getattr(role, "codigo", None) == "ADMIN"):
        return False
    router = sys.modules.get("app.api.router")
    enforcer = getattr(router, "enforcer", None)
    if enforcer is None:
        security = Path(__file__).resolve().parents[1] / "security"
        policy = security / "policy.csv"
        enforcer = _file_enforcer(str(security / "model.conf"), str(policy), policy.stat().st_mtime_ns)
    return all(enforcer.enforce("ADMIN", permission, "use")
               for permission in ("exchange_rates_sync:list", "exchange_rates_sync:view"))


def exchange_rate_notification_visibility(account):
    """Only TC notices are hidden from ineligible recipients; other types stay intact."""
    return true() if can_view_exchange_rate_notifications(account) else Notificacion.tipo.not_in(EXCHANGE_RATE_NOTIFICATION_TYPES)


def _events(records, *, now: datetime, start_date: date):
    """Pure projection: stable event references survive reads, closes and restarts."""
    today = now.astimezone(LA_PAZ).date()
    successes = {row.fecha_objetivo: row for row in records if row.estado == "EXITOSO"}
    current = successes.get(today)
    today_rows = [row for row in records if row.fecha_intento.astimezone(LA_PAZ).date() == today]
    failures = [row for row in today_rows if row.estado.startswith("ERROR_")]
    events = []
    if failures:
        first = min(failures, key=lambda row: (row.fecha_intento, row.id))
        events.append(dict(tipo="TC_SYNC_PRIMER_ERROR", record_id=first.id, table="TIPO_CAMBIO_REGISTROS",
            priority=PrioridadNotificacionEnum.ALTA, title="ERROR DE SINCRONIZACIÓN USD/BOB",
            message=f"No se pudo obtener la cotización oficial correspondiente al {first.fecha_objetivo:%d/%m/%Y} "
                    f"en el primer error del {today:%d/%m/%Y}. "
                    "Se conserva el último valor activo, si existe. Consulta los registros y la próxima ejecución."))
    if not current:
        tenth = next((row for row in today_rows if row.numero_intento == 10 and row.estado.startswith("ERROR_")), None)
        if tenth:
            events.append(dict(tipo="TC_SYNC_AGOTADO", record_id=tenth.id, table="TIPO_CAMBIO_REGISTROS",
                priority=PrioridadNotificacionEnum.ALTA, title="DIEZ INTENTOS USD/BOB AGOTADOS",
                message="Se realizaron 10 intentos hoy y aún no se obtuvo el tipo de cambio oficial del día. "
                        "Se intentará nuevamente mañana a partir de las 05:00, hora de Bolivia."))
    previous_dates = [day for day in successes if start_date <= day < today]
    episode_start = max(start_date, max(previous_dates) + timedelta(days=1)) if previous_dates else start_date
    missing_closed = max((today - episode_start).days, 0)
    if not current and missing_closed >= 3:
        episode_rows = [row for row in records if row.fecha_objetivo >= episode_start]
        if episode_rows:
            anchor = min(episode_rows, key=lambda row: (row.fecha_intento, row.id))
            events.append(dict(tipo="TC_SYNC_PROLONGADO", record_id=anchor.id, table="TIPO_CAMBIO_REGISTROS",
                priority=PrioridadNotificacionEnum.URGENTE, title="TRES DÍAS SIN COTIZACIÓN OFICIAL USD/BOB",
                message=f"El tipo de cambio oficial no se actualiza desde hace al menos 3 días calendario cerrados consecutivos "
                        f"(episodio desde {episode_start:%d/%m/%Y}). Se recomienda contactar a soporte técnico. "
                        "Se mantiene el último valor activo, si existe."))
    if current:
        recovered = bool([row for row in records if row.estado.startswith("ERROR_")
                          and row.fecha_objetivo >= episode_start and row.fecha_intento <= current.fecha_intento]) or missing_closed > 0
        events.append(dict(tipo="TC_SYNC_EXITOSO", record_id=current.tipo_cambio_id, table="TIPO_CAMBIO_MONEDA",
            priority=PrioridadNotificacionEnum.MEDIA, title="COTIZACIÓN OFICIAL USD/BOB OBTENIDA",
            message=f"Cotización oficial del {today:%d/%m/%Y} obtenida mediante factura.bo. "
                    + ("La sincronización se recuperó tras un período sin actualización. " if recovered else "")
                    + "Consulta el valor operativo actual en Tipos de Cambio; una tasa manual posterior puede seguir activa."))
    return events, current


def reconcile_exchange_rate_notifications(db: Session, *, now: datetime, start_date: date) -> dict:
    if now.tzinfo is None or now.utcoffset() is None or isinstance(start_date, datetime) or not isinstance(start_date, date):
        raise ValueError("TC notifications require an aware instant and a stable start date.")
    result = {"created": 0, "unchanged": 0, "resolved": 0}
    if now.astimezone(LA_PAZ).date() < start_date:
        return result
    currency = db.execute(select(Moneda).where(Moneda.codigo == "USD").with_for_update()
                          .execution_options(populate_existing=True)).scalar_one_or_none()
    if currency is None or not currency.habilitado:
        return result
    records = list(db.scalars(select(TipoCambioRegistro).where(
        TipoCambioRegistro.moneda_id == currency.id, TipoCambioRegistro.proveedor == PROVIDER,
        TipoCambioRegistro.fecha_objetivo >= start_date, TipoCambioRegistro.fecha_intento <= now,
    ).order_by(TipoCambioRegistro.fecha_intento, TipoCambioRegistro.id)))
    events, current = _events(records, now=now, start_date=start_date)
    recipients = [account for account in _get_active_accounts_for_roles(db, ("ADMIN",))
                  if can_view_exchange_rate_notifications(account)]
    for event in events:
        for account in recipients:
            exists = db.scalar(select(Notificacion.id).where(
                Notificacion.usuario_id == account.usuario_id, Notificacion.tipo == event["tipo"],
                Notificacion.tabla_referencia == event["table"], Notificacion.id_referencia == event["record_id"],
            ).limit(1))
            if exists is not None:
                result["unchanged"] += 1
                continue
            create_notification_for_user(db, user=account.usuario, tipo=event["tipo"], prioridad=event["priority"],
                titulo=event["title"], mensaje=event["message"], modulo="MONEDAS",
                tabla_referencia=event["table"], id_referencia=event["record_id"])
            result["created"] += 1
    # A failure while recovering a past date is not resolved merely because
    # today's quote already exists. Its goal must actually have been recovered.
    success_dates = {row.fecha_objetivo for row in records if row.estado == "EXITOSO"}
    recovered_ids = [row.id for row in records if row.fecha_objetivo in success_dates
                     or (current and row.fecha_objetivo == row.fecha_intento.astimezone(LA_PAZ).date())]
    if recovered_ids:
        closed = db.execute(update(Notificacion).where(
            Notificacion.tipo == "TC_SYNC_PRIMER_ERROR", Notificacion.tabla_referencia == "TIPO_CAMBIO_REGISTROS",
            Notificacion.id_referencia.in_(recovered_ids), Notificacion.resuelta.is_(False),
        ).values(resuelta=True, fecha_resuelta=now, motivo_cierre="COTIZACION_ACTUAL_OBTENIDA"))
        result["resolved"] += closed.rowcount
    if current:
        ids = [row.id for row in records]
        closed = db.execute(update(Notificacion).where(
            Notificacion.tipo.in_(FAILURE_NOTICE_TYPES - {"TC_SYNC_PRIMER_ERROR"}),
            Notificacion.tabla_referencia == "TIPO_CAMBIO_REGISTROS",
            Notificacion.id_referencia.in_(ids), Notificacion.resuelta.is_(False),
        ).values(resuelta=True, fecha_resuelta=now, motivo_cierre="COTIZACION_ACTUAL_OBTENIDA"))
        result["resolved"] += closed.rowcount
        prior_rate_ids = [row.tipo_cambio_id for row in records if row.estado == "EXITOSO" and row.fecha_objetivo < current.fecha_objetivo]
        closed = db.execute(update(Notificacion).where(
            Notificacion.tipo == "TC_SYNC_EXITOSO", Notificacion.tabla_referencia == "TIPO_CAMBIO_MONEDA",
            Notificacion.id_referencia.in_(prior_rate_ids), Notificacion.resuelta.is_(False),
        ).values(resuelta=True, fecha_resuelta=now, motivo_cierre="NUEVA_COTIZACION_OFICIAL"))
        result["resolved"] += closed.rowcount
    db.flush()
    return result
