"""Read-only projections; these functions never invoke the provider."""
from datetime import datetime, time, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from app.models.currency import Moneda
from app.models.exchange_rate import TipoCambioMoneda
from app.models.exchange_rate_record import TipoCambioRegistro, STATES
from app.services.exchange_rate_history_service import AUTOMATIC_PROVIDER, LA_PAZ
from app.services.exchange_rate_schedule import decide_sync


STATE_MESSAGES = {
    "INICIADO": "Consulta iniciada; resultado pendiente de confirmación.",
    "EXITOSO": "Cotización oficial validada y registrada.",
    "ERROR_CONEXION": "No se pudo establecer comunicación con el proveedor.",
    "ERROR_API": "El proveedor respondió con un estado HTTP no válido.",
    "ERROR_DATOS": "La respuesta o el valor de cotización no cumple el contrato verificado.",
    "ERROR_VIGENCIA": "No se pudo demostrar la vigencia para la fecha objetivo.",
    "ERROR_EJECUCION": "La ejecución fue interrumpida o no pudo completarse de forma consistente.",
    "CARGA_HISTORICA": "Cotización histórica importada mediante procedimiento controlado.",
}


def usd_currency(db):
    return db.scalar(select(Moneda).where(Moneda.codigo == "USD"))


def automatic_records(db, moneda_id, start_date):
    query = select(TipoCambioRegistro).where(TipoCambioRegistro.moneda_id == moneda_id,
        TipoCambioRegistro.proveedor == AUTOMATIC_PROVIDER)
    if start_date:
        query = query.where(TipoCambioRegistro.fecha_objetivo >= start_date)
    return list(db.scalars(query.order_by(TipoCambioRegistro.fecha_intento, TipoCambioRegistro.id)))


def sync_state(db, *, config, now=None):
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(LA_PAZ).date()
    currency = usd_currency(db)
    rows = automatic_records(db, currency.id, config.exchange_rate_sync_start_date) if currency else []
    active = db.scalar(select(TipoCambioMoneda).where(TipoCambioMoneda.moneda_id == currency.id,
        TipoCambioMoneda.activo.is_(True))) if currency else None
    decision = decide_sync(rows, now=now, start_date=config.exchange_rate_sync_start_date,
        enabled=config.exchange_rate_sync_enabled, available=bool(currency and currency.habilitado and not currency.es_base))
    successful = [r for r in rows if r.estado == "EXITOSO"]
    today_records = [r for r in successful if r.fecha_objetivo == today]
    official_today = bool(today_records)
    latest_official = db.scalar(select(func.max(TipoCambioRegistro.fecha_objetivo)).where(
        TipoCambioRegistro.moneda_id == currency.id, TipoCambioRegistro.estado.in_(("EXITOSO", "CARGA_HISTORICA")))) if currency else None
    official_active = db.scalar(select(TipoCambioRegistro.fecha_objetivo).where(TipoCambioRegistro.tipo_cambio_id == active.id,
        TipoCambioRegistro.estado.in_(("EXITOSO", "CARGA_HISTORICA"))).order_by(TipoCambioRegistro.fecha_objetivo.desc()).limit(1)) if active else None
    status, message = "WAITING", "Sincronización pendiente según el calendario de Bolivia."
    if decision.reason == "DISABLED":
        status, message = "DISABLED", "La sincronización automática está deshabilitada."
    elif decision.reason == "PAUSED":
        status, message = "PAUSED", "Se requiere USD habilitado para ejecutar la sincronización."
    elif decision.reason == "NOT_STARTED":
        status, message = "NOT_STARTED", "La sincronización aún no alcanzó su fecha inicial configurada."
    elif active is None:
        status, message = "NO_ACTIVE_RATE", "No existe un tipo de cambio USD vigente. Se requiere intervención ADMIN antes de registrar nuevas operaciones en USD."
    elif official_today and active.origen == "MANUAL":
        status, message = "MANUAL_AFTER_OFFICIAL", "Cotización oficial consultada hoy; valor operativo actual: manual."
    elif official_today and any(r.tipo_cambio_id == active.id for r in today_records):
        status, message = "UPDATED", f"ACTUALIZADO TIPO DE CAMBIO HOY ({today.strftime('%d/%m/%Y')})"
    elif decision.used >= 10 and not official_today:
        status, message = "EXHAUSTED", "Se realizaron 10 intentos hoy y aún no se obtuvo el tipo de cambio oficial del día. Se intentará nuevamente mañana."
    else:
        failures = [r for r in rows if r.fecha_objetivo == today and r.estado.startswith("ERROR_")]
        if active.origen == "MANUAL":
            status, message = "MANUAL_FALLBACK", "Tipo de cambio manual temporal; la actualización automática lo sustituirá cuando se obtenga una cotización válida."
        elif failures and failures[-1].estado == "ERROR_CONEXION":
            status, message = "CONNECTION_ERROR", "No se pudo establecer conexión para actualizar el tipo de cambio del dólar. Se utiliza el último valor registrado; puede modificarse manualmente. Reintento pendiente."
        elif failures:
            status, message = "ERROR", "ERROR: NO SE PUEDE ACTUALIZAR EL TIPO DE CAMBIO. Se utiliza el último valor registrado o puede modificarse manualmente."
    return dict(enabled=config.exchange_rate_sync_enabled, start_date=config.exchange_rate_sync_start_date,
        local_date=today, status=status, message=message,
        operational_rate=dict(id=active.id, valor_bob=format(active.valor_bob, ".4f"), origen=active.origen,
            fuente=active.fuente, fecha_registro=active.fecha_registro, fecha_oficial=official_active) if active else None,
        last_official_date=latest_official, official_today=official_today, attempts_used=decision.used,
        attempts_remaining=max(10-decision.used, 0), next_attempt_at=decision.next_at,
        consecutive_missing_days=decision.missing_days, backlog_count=decision.backlog)


def _record_projection(row):
    return dict(id=row.id, moneda_codigo="USD", fecha_objetivo=row.fecha_objetivo, numero_intento=row.numero_intento,
        fecha_intento=row.fecha_intento, estado=row.estado, codigo_http=row.codigo_http,
        proximo_intento=row.proximo_intento, proveedor=row.proveedor, tipo_cambio_id=row.tipo_cambio_id,
        valor_bob=format(row.tipo_cambio.valor_bob, ".4f") if row.tipo_cambio else None,
        message=STATE_MESSAGES[row.estado])


def sync_records(db, *, page=1, page_size=25, date_from=None, date_to=None,
                 execution_from=None, execution_to=None, estado=None, proveedor=None, record_id=None):
    if estado is not None and estado not in STATES:
        raise HTTPException(422, detail="Estado de sincronización no válido.")
    if (date_from and date_to and date_from > date_to) or (execution_from and execution_to and execution_from > execution_to):
        raise HTTPException(422, detail="El inicio del rango no puede superar su fin.")
    query = select(TipoCambioRegistro).join(Moneda, Moneda.id == TipoCambioRegistro.moneda_id).where(Moneda.codigo == "USD")
    for value, expression in ((date_from, TipoCambioRegistro.fecha_objetivo.__ge__), (date_to, TipoCambioRegistro.fecha_objetivo.__le__),
            (estado, TipoCambioRegistro.estado.__eq__), (proveedor, TipoCambioRegistro.proveedor.__eq__), (record_id, TipoCambioRegistro.id.__eq__)):
        if value is not None:
            query = query.where(expression(value))
    if execution_from:
        query = query.where(TipoCambioRegistro.fecha_intento >= datetime.combine(execution_from, time.min, tzinfo=LA_PAZ))
    if execution_to:
        query = query.where(TipoCambioRegistro.fecha_intento < datetime.combine(execution_to+timedelta(days=1), time.min, tzinfo=LA_PAZ))
    count = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.options(joinedload(TipoCambioRegistro.tipo_cambio)).order_by(
        TipoCambioRegistro.fecha_intento.desc(), TipoCambioRegistro.id.desc()).offset((page-1)*page_size).limit(page_size))
    return dict(items=[_record_projection(row) for row in rows], total=count, page=page, page_size=page_size)


def sync_record(db, record_id):
    result = sync_records(db, record_id=record_id)
    if not result["items"]:
        raise HTTPException(404, detail="Registro de sincronización no encontrado.")
    return result["items"][0]
