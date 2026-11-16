"""TC-01 persistence only: no provider client, scheduler, retry loop or audit hook.

insert_rate deliberately never commits. Attempt coordinators commit at their
documented boundaries so INICIADO survives a later external interruption.
"""
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.currency import Moneda
from app.models.exchange_rate import TipoCambioMoneda
from app.models.exchange_rate_record import TipoCambioRegistro


LA_PAZ = ZoneInfo("America/La_Paz")
FAILURE_STATES = frozenset({"ERROR_CONEXION", "ERROR_API", "ERROR_DATOS", "ERROR_VIGENCIA", "ERROR_EJECUCION"})
AUTOMATIC_PROVIDER = "FACTURA_BO_BCB"
HISTORICAL_PROVIDER = "BCB_CARGA_INICIAL"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def aware_datetime(value: datetime, field: str = "fecha") -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise HTTPException(422, detail=f"{field} requiere fecha y zona horaria explícita.")
    return value.astimezone(timezone.utc)


def validate_rate(value) -> Decimal:
    if isinstance(value, (bool, float)):
        raise HTTPException(422, detail="El tipo de cambio requiere un decimal exacto, no FLOAT.")
    try:
        result = Decimal(value)
        if not result.is_finite() or result <= 0 or result >= Decimal("100000000"):
            raise ValueError()
        exact = result.quantize(Decimal("0.0001"))
        if exact != result:
            raise ValueError()
        return exact
    except (InvalidOperation, ValueError, TypeError, OverflowError):
        raise HTTPException(422, detail="Tipo de cambio inválido: positivo, NUMERIC(12,4), sin redondeo implícito.") from None


def lock_currency(db: Session, moneda_id: int) -> Moneda:
    currency = db.execute(select(Moneda).where(Moneda.id == moneda_id).with_for_update()
                          .execution_options(populate_existing=True)).scalar_one_or_none()
    if currency is None:
        raise HTTPException(404, detail="Moneda no encontrada.")
    return currency


def insert_rate(db: Session, *, moneda_id: int, valor_bob, usuario_id: int | None,
                origen: str = "MANUAL", fuente: str | None = "MANUAL", fec_consulta: datetime | None = None,
                observaciones: str | None = None, operativo: bool = True) -> TipoCambioMoneda:
    currency = lock_currency(db, moneda_id)
    value = validate_rate(valor_bob)
    if not currency.habilitado:
        raise HTTPException(409, detail="No puedes operar con monedas deshabilitadas.")
    if (currency.es_base or currency.codigo == "BOB") and value != Decimal("1.0000"):
        raise HTTPException(409, detail="La moneda base BOB conserva valor 1.")
    if origen not in {"MANUAL", "AUTOMATICO"}:
        raise HTTPException(422, detail="Origen de cotización inválido.")
    if origen == "MANUAL" and (usuario_id is None or fuente != "MANUAL" or fec_consulta is not None):
        raise HTTPException(422, detail="La cotización MANUAL requiere usuario y procedencia manual.")
    if origen == "AUTOMATICO":
        if currency.codigo != "USD" or currency.es_base or usuario_id is not None:
            raise HTTPException(409, detail="Solo USD admite cotizaciones automáticas atribuidas a SISTEMA.")
        if fuente not in {"BCB_VIA_FACTURA_BO", "BCB_CARGA_INICIAL"}:
            raise HTTPException(422, detail="Fuente automática no admitida.")
        if fuente == "BCB_CARGA_INICIAL" and (operativo or fec_consulta is not None):
            raise HTTPException(422, detail="La carga histórica debe ser inactiva y no simular una consulta.")
        if fuente == "BCB_VIA_FACTURA_BO" and fec_consulta is None:
            raise HTTPException(422, detail="La cotización consultada requiere fecha de captura.")
    if fec_consulta is not None:
        fec_consulta = aware_datetime(fec_consulta, "Fecha de consulta")
    if operativo:
        # Flush the old active state before INSERT: the partial index is immediate.
        db.execute(update(TipoCambioMoneda).where(TipoCambioMoneda.moneda_id == moneda_id,
            TipoCambioMoneda.activo.is_(True)).values(activo=False).execution_options(synchronize_session="fetch"))
        db.flush()
    item = TipoCambioMoneda(moneda_id=moneda_id, usuario_id=usuario_id, valor_bob=value,
        origen=origen, fuente=fuente, fecha_consulta=fec_consulta, observaciones=observaciones, activo=operativo)
    db.add(item)
    db.flush()
    return item


def _usd(currency):
    if not currency.habilitado or currency.codigo != "USD" or currency.es_base:
        raise HTTPException(409, detail="La persistencia automática requiere USD habilitado, sin usar IDs fijos.")


def _target_day(value, now):
    if not isinstance(value, date) or isinstance(value, datetime) or value > now.astimezone(LA_PAZ).date():
        raise HTTPException(422, detail="La fecha objetivo debe ser una fecha verificada no futura.")


def begin_attempt(db: Session, *, moneda_id: int, fecha_objetivo: date,
                  proveedor: str = AUTOMATIC_PROVIDER, now: datetime | None = None) -> TipoCambioRegistro:
    try:
        instant = aware_datetime(now or utc_now(), "Inicio del intento")
        _target_day(fecha_objetivo, instant)
        if proveedor != AUTOMATIC_PROVIDER:
            raise HTTPException(422, detail="Proveedor de consulta no admitido.")
        _usd(lock_currency(db, moneda_id))
        previous = db.scalar(select(TipoCambioRegistro.id).where(TipoCambioRegistro.moneda_id == moneda_id,
            TipoCambioRegistro.proveedor == proveedor, TipoCambioRegistro.fecha_objetivo == fecha_objetivo,
            TipoCambioRegistro.estado == "EXITOSO").limit(1))
        if previous is not None:
            raise HTTPException(409, detail="La fecha objetivo ya tiene una consulta exitosa.")
        day = instant.astimezone(LA_PAZ).date()
        start = datetime.combine(day, time.min, tzinfo=LA_PAZ).astimezone(timezone.utc)
        end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=LA_PAZ).astimezone(timezone.utc)
        ordinal = db.scalar(select(func.coalesce(func.max(TipoCambioRegistro.numero_intento), 0)).where(
            TipoCambioRegistro.moneda_id == moneda_id, TipoCambioRegistro.proveedor == proveedor,
            TipoCambioRegistro.fecha_intento >= start, TipoCambioRegistro.fecha_intento < end,
            TipoCambioRegistro.numero_intento > 0)) + 1
        if ordinal > 10:
            raise HTTPException(409, detail="Se agotaron los diez intentos del día de ejecución.")
        item = TipoCambioRegistro(moneda_id=moneda_id, fecha_objetivo=fecha_objetivo,
            numero_intento=ordinal, fecha_intento=instant, estado="INICIADO", proveedor=proveedor)
        db.add(item)
        db.flush()
        db.commit()  # Durable intent before any future external consultation.
        return item
    except Exception:
        db.rollback()
        raise


def _locked_attempt(db, attempt_id):
    moneda_id = db.scalar(select(TipoCambioRegistro.moneda_id).where(TipoCambioRegistro.id == attempt_id))
    if moneda_id is None:
        raise HTTPException(404, detail="Intento no encontrado.")
    lock_currency(db, moneda_id)
    item = db.execute(select(TipoCambioRegistro).where(TipoCambioRegistro.id == attempt_id).with_for_update()
                      .execution_options(populate_existing=True)).scalar_one()
    if item.proveedor != AUTOMATIC_PROVIDER:
        raise HTTPException(409, detail="El registro no corresponde a una consulta automática.")
    return item


def finish_success(db: Session, *, attempt_id: int, valor_bob, fec_consulta: datetime,
                   operativo: bool = True, codigo_http: int = 200, now: datetime | None = None) -> TipoCambioRegistro:
    try:
        item = _locked_attempt(db, attempt_id)
        _usd(lock_currency(db, item.moneda_id))
        value = validate_rate(valor_bob)
        capture = aware_datetime(fec_consulta, "Fecha de consulta")
        current = aware_datetime(now or utc_now(), "Fin del intento")
        _target_day(item.fecha_objetivo, current)
        if not isinstance(codigo_http, int) or isinstance(codigo_http, bool) or not 200 <= codigo_http <= 299:
            raise HTTPException(422, detail="Un éxito requiere respuesta HTTP válida.")
        if capture < item.fecha_intento or capture > current:
            raise HTTPException(422, detail="La captura no corresponde al intervalo de ejecución real.")
        if item.estado == "EXITOSO":
            existing = db.get(TipoCambioMoneda, item.tipo_cambio_id)
            if existing.valor_bob != value or existing.fecha_consulta != capture or item.codigo_http != codigo_http:
                raise HTTPException(409, detail="El intento finalizado no puede sobrescribirse.")
            db.commit()
            return item
        if item.estado != "INICIADO":
            raise HTTPException(409, detail="Solo un intento INICIADO puede finalizar exitosamente.")
        other = db.scalar(select(TipoCambioRegistro.id).where(TipoCambioRegistro.moneda_id == item.moneda_id,
            TipoCambioRegistro.proveedor == item.proveedor, TipoCambioRegistro.fecha_objetivo == item.fecha_objetivo,
            TipoCambioRegistro.estado == "EXITOSO").limit(1))
        if other is not None:
            raise HTTPException(409, detail="La fecha objetivo ya tiene resultado exitoso.")
        # Capturing on a later day always means recovery, never a new live rate.
        live = operativo and item.fecha_objetivo == current.astimezone(LA_PAZ).date()
        rate = insert_rate(db, moneda_id=item.moneda_id, valor_bob=value, usuario_id=None,
            origen="AUTOMATICO", fuente="BCB_VIA_FACTURA_BO", fec_consulta=capture, operativo=live)
        item.tipo_cambio_id, item.estado, item.codigo_http = rate.id, "EXITOSO", codigo_http
        item.proximo_intento = None
        db.flush()
        db.commit()
        return item
    except Exception:
        db.rollback()
        raise


def finish_failure(db: Session, *, attempt_id: int, estado: str, codigo_http: int | None = None,
                   proximo_intento: datetime | None = None) -> TipoCambioRegistro:
    try:
        item = _locked_attempt(db, attempt_id)
        if estado not in FAILURE_STATES:
            raise HTTPException(422, detail="Estado de error inválido.")
        if codigo_http is not None and (not isinstance(codigo_http, int) or isinstance(codigo_http, bool) or not 100 <= codigo_http <= 599):
            raise HTTPException(422, detail="Código HTTP inválido.")
        if estado == "ERROR_CONEXION" and codigo_http is not None:
            raise HTTPException(422, detail="Un error de conexión no implica respuesta HTTP.")
        if proximo_intento is not None:
            proximo_intento = aware_datetime(proximo_intento, "Próximo intento")
            if proximo_intento <= item.fecha_intento:
                raise HTTPException(422, detail="El próximo intento debe ser posterior al inicio.")
        if item.estado != "INICIADO":
            if (item.estado, item.codigo_http, item.proximo_intento) != (estado, codigo_http, proximo_intento):
                raise HTTPException(409, detail="El intento finalizado no puede sobrescribirse.")
        else:
            item.estado, item.codigo_http, item.proximo_intento = estado, codigo_http, proximo_intento
        db.flush()
        db.commit()
        return item
    except Exception:
        db.rollback()
        raise


def validate_history_rows(rows, provenance):
    """Validate a human-verified dataset; no claim to independently verify BCB."""
    if not isinstance(provenance, dict) or provenance.get("verified") is not True:
        raise HTTPException(422, detail="La carga requiere un manifiesto de verificación explícito.")
    for field in ("official_source", "verified_by", "dataset_sha256"):
        if not isinstance(provenance.get(field), str) or not provenance[field].strip():
            raise HTTPException(422, detail="Manifiesto de procedencia incompleto.")
    import re
    if not re.fullmatch(r"[a-fA-F0-9]{64}", provenance["dataset_sha256"]):
        raise HTTPException(422, detail="El manifiesto requiere SHA-256 del dataset.")
    try:
        first, last = date.fromisoformat(provenance["period_start"]), date.fromisoformat(provenance["period_end"])
        verification = datetime.fromisoformat(provenance["verified_at"].replace("Z", "+00:00"))
        aware_datetime(verification, "Verificación del dataset")
    except (ValueError, KeyError, AttributeError, TypeError):
        raise HTTPException(422, detail="El manifiesto requiere período y fecha de verificación válidos.") from None
    if first.day != 1 or first.year != last.year or first.month != last.month or (last + timedelta(days=1)).day != 1:
        raise HTTPException(422, detail="La carga inicial debe corresponder a un mes calendario completo.")
    if not rows:
        raise HTTPException(422, detail="El dataset está vacío.")
    normalized, seen = [], set()
    for row in rows:
        try:
            day = date.fromisoformat(row["fecha_objetivo"]) if isinstance(row["fecha_objetivo"], str) else row["fecha_objetivo"]
            _target_day(day, utc_now())
            value = validate_rate(row["valor_bob"])
        except (KeyError, ValueError, TypeError):
            raise HTTPException(422, detail="Fila histórica inválida.") from None
        if not first <= day <= last or day in seen:
            raise HTTPException(422, detail="Fecha duplicada o fuera del mes aprobado.")
        seen.add(day)
        normalized.append({"fecha_objetivo": day, "valor_bob": value})
    if len(seen) != (last - first).days + 1:
        raise HTTPException(422, detail="El dataset debe contener una cotización verificada por cada día del mes aprobado.")
    return sorted(normalized, key=lambda row: row["fecha_objetivo"])


def import_history(db: Session, *, rows, provenance) -> dict:
    try:
        normalized = validate_history_rows(rows, provenance)
        currency_id = db.scalar(select(Moneda.id).where(Moneda.codigo == "USD"))
        if currency_id is None:
            raise HTTPException(404, detail="No existe moneda USD; la carga no crea monedas.")
        _usd(lock_currency(db, currency_id))
        inserted = skipped = 0
        for row in normalized:
            previous = db.scalar(select(TipoCambioRegistro).where(TipoCambioRegistro.moneda_id == currency_id,
                TipoCambioRegistro.fecha_objetivo == row["fecha_objetivo"], TipoCambioRegistro.proveedor == HISTORICAL_PROVIDER,
                TipoCambioRegistro.estado == "CARGA_HISTORICA"))
            if previous is not None:
                rate = db.get(TipoCambioMoneda, previous.tipo_cambio_id)
                if (rate.valor_bob != row["valor_bob"] or rate.origen != "AUTOMATICO" or rate.fuente != HISTORICAL_PROVIDER
                        or rate.activo or rate.fecha_consulta is not None or rate.usuario_id is not None):
                    raise HTTPException(409, detail="La fecha histórica ya existe con otro valor o procedencia; no se sobrescribe.")
                skipped += 1
                continue
            started = utc_now()
            rate = insert_rate(db, moneda_id=currency_id, valor_bob=row["valor_bob"], usuario_id=None,
                origen="AUTOMATICO", fuente=HISTORICAL_PROVIDER, operativo=False)
            db.add(TipoCambioRegistro(moneda_id=currency_id, tipo_cambio_id=rate.id,
                fecha_objetivo=row["fecha_objetivo"], numero_intento=0, fecha_intento=started,
                estado="CARGA_HISTORICA", proveedor=HISTORICAL_PROVIDER))
            db.flush()
            inserted += 1
        db.commit()
        return {"inserted": inserted, "skipped": skipped, "active_rate_unchanged": True}
    except Exception:
        db.rollback()
        raise
