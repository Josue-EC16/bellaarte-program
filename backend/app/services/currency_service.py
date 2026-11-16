from fastapi import HTTPException, status
from functools import wraps
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.audit import register_audit_event
from app.models.account import Cuenta
from app.models.currency import Moneda
from app.models.exchange_rate import TipoCambioMoneda
from app.models.exchange_rate_record import TipoCambioRegistro
from app.services.exchange_rate_history_service import insert_rate, lock_currency, validate_rate
from app.schemas.currency import (
    MonedaCreateRequest,
    MonedaResponse,
    MonedaUpdateRequest,
    TipoCambioCreateRequest,
    TipoCambioDetailResponse,
    TipoCambioListItem,
    TipoCambioUpdateRequest,
)


def _atomic_write(operation):
    @wraps(operation)
    def coordinated(db, *args, **kwargs):
        try:
            return operation(db, *args, **kwargs)
        except Exception:
            db.rollback()
            raise
    return coordinated


def _ensure_exchange_admin(account: Cuenta) -> None:
    if (account.rol.codigo != "ADMIN" or not account.is_active or not account.usuario.activo
            or not account.rol.activo or account.must_change_password):
        raise HTTPException(status_code=403, detail="Solo ADMIN puede gestionar tipos de cambio manuales.")


def _ensure_manual(rate: TipoCambioMoneda) -> None:
    if rate.origen != "MANUAL":
        raise HTTPException(status_code=409, detail="Las cotizaciones AUTOMATICO no admiten modificación ni activación manual.")


def _to_currency_response(currency: Moneda) -> MonedaResponse:
    return MonedaResponse(
        id=currency.id,
        codigo=currency.codigo,
        nombre=currency.nombre,
        simbolo=currency.simbolo,
        es_base=currency.es_base,
        habilitado=currency.habilitado,
        fecha_registro=currency.fecha_registro,
    )


def _to_exchange_rate_list_item(rate: TipoCambioMoneda) -> TipoCambioListItem:
    return TipoCambioListItem(
        id=rate.id,
        moneda_id=rate.moneda.id,
        moneda_codigo=rate.moneda.codigo,
        moneda_nombre=rate.moneda.nombre,
        valor_bob=rate.valor_bob,
        activo=rate.activo,
        registrado_por=rate.usuario.nombre_completo if rate.usuario is not None else "SISTEMA",
        fecha_registro=rate.fecha_registro,
        origen=rate.origen, fuente=rate.fuente, fecha_consulta=rate.fecha_consulta,
    )


def _to_exchange_rate_detail(rate: TipoCambioMoneda) -> TipoCambioDetailResponse:
    return TipoCambioDetailResponse(
        id=rate.id,
        moneda=_to_currency_response(rate.moneda),
        valor_bob=rate.valor_bob,
        observaciones=rate.observaciones,
        activo=rate.activo,
        registrado_por=rate.usuario.nombre_completo if rate.usuario is not None else "SISTEMA",
        fecha_registro=rate.fecha_registro,
        origen=rate.origen, fuente=rate.fuente, fecha_consulta=rate.fecha_consulta,
    )


def seed_default_currency(db: Session, *, admin_account: Cuenta | None = None) -> None:
    existing_bob = db.execute(select(Moneda).where(func.upper(Moneda.codigo) == "BOB")).scalar_one_or_none()
    if existing_bob is None:
        existing_bob = Moneda(codigo="BOB", nombre="BOLIVIANO", simbolo="Bs", es_base=True, habilitado=True)
        db.add(existing_bob)
        db.flush()
    else:
        existing_bob.es_base = True
        existing_bob.habilitado = True

    active_base_rate = db.execute(
        select(TipoCambioMoneda).where(TipoCambioMoneda.moneda_id == existing_bob.id, TipoCambioMoneda.activo.is_(True))
    ).scalar_one_or_none()
    if active_base_rate is None and admin_account is not None:
        db.add(
            TipoCambioMoneda(
                moneda_id=existing_bob.id,
                usuario_id=admin_account.usuario_id,
                valor_bob=1,
                observaciones="TIPO DE CAMBIO BASE DEL SISTEMA",
                activo=True,
            )
        )
    db.commit()


def _get_currency_entity(db: Session, currency_id: int) -> Moneda:
    currency = db.execute(select(Moneda).where(Moneda.id == currency_id)).scalar_one_or_none()
    if currency is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Moneda no encontrada.")
    return currency


def _get_exchange_rate_entity(db: Session, rate_id: int) -> TipoCambioMoneda:
    rate = db.execute(
        select(TipoCambioMoneda)
        .options(joinedload(TipoCambioMoneda.moneda), joinedload(TipoCambioMoneda.usuario))
        .where(TipoCambioMoneda.id == rate_id)
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if rate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de cambio no encontrado.")
    return rate


def _ensure_unique_currency_code(db: Session, code: str, *, exclude_id: int | None = None) -> None:
    stmt = select(Moneda).where(func.upper(Moneda.codigo) == code.strip().upper())
    if exclude_id is not None:
        stmt = stmt.where(Moneda.id != exclude_id)
    if db.execute(stmt).scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe una moneda con ese código.")


def _ensure_base_constraints(db: Session, *, target: Moneda, es_base: bool, habilitado: bool) -> None:
    if es_base and not habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La moneda base debe permanecer habilitada.")
    if not es_base and target.es_base and not habilitado:
        other_base = db.execute(select(Moneda).where(Moneda.id != target.id, Moneda.es_base.is_(True))).scalar_one_or_none()
        if other_base is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes dejar al sistema sin moneda base activa.")


def _sync_base_currency(db: Session, *, current_id: int | None, make_base: bool) -> None:
    if not make_base:
        return
    for currency in db.execute(select(Moneda).where(Moneda.id != current_id, Moneda.es_base.is_(True))).scalars():
        currency.es_base = False


def list_currencies(db: Session, *, search: str | None = None, is_active: bool | None = None) -> list[MonedaResponse]:
    stmt = select(Moneda).order_by(Moneda.es_base.desc(), Moneda.codigo.asc())
    if is_active is not None:
        stmt = stmt.where(Moneda.habilitado.is_(is_active))
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.where(or_(func.upper(Moneda.codigo).like(term), func.upper(Moneda.nombre).like(term)))
    return [_to_currency_response(currency) for currency in db.execute(stmt).scalars().all()]


def get_currency(db: Session, currency_id: int) -> MonedaResponse:
    return _to_currency_response(_get_currency_entity(db, currency_id))


def create_currency(
    db: Session,
    *,
    payload: MonedaCreateRequest,
    created_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> MonedaResponse:
    if payload.es_base and payload.codigo.strip().upper() != "BOB":
        raise HTTPException(status_code=409, detail="BOB debe conservarse como moneda base del sistema.")
    _ensure_unique_currency_code(db, payload.codigo)
    currency = Moneda(
        codigo=payload.codigo,
        nombre=payload.nombre,
        simbolo=payload.simbolo,
        es_base=payload.es_base,
        habilitado=payload.habilitado or payload.es_base,
    )
    _sync_base_currency(db, current_id=None, make_base=currency.es_base)
    db.add(currency)
    db.flush()
    register_audit_event(
        db,
        action="CURRENCY_CREATED",
        description=f"Se creó la moneda '{currency.codigo}'.",
        account=created_by,
        user=created_by.usuario,
        reference=str(currency.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_currency(db, currency.id)


@_atomic_write
def update_currency(
    db: Session,
    *,
    currency_id: int,
    payload: MonedaUpdateRequest,
    updated_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> MonedaResponse:
    currency = _get_currency_entity(db, currency_id)
    db.execute(select(Moneda.id).where(Moneda.id == currency_id).with_for_update())
    db.refresh(currency)
    if currency.codigo == "BOB" and (payload.codigo.strip().upper() != "BOB" or not payload.es_base):
        raise HTTPException(status_code=409, detail="BOB debe conservar su código y condición de moneda base.")
    if payload.es_base and payload.codigo.strip().upper() != "BOB":
        raise HTTPException(status_code=409, detail="BOB debe conservarse como moneda base del sistema.")
    if (payload.codigo.strip().upper() != currency.codigo or payload.es_base != currency.es_base):
        automatic = db.scalar(select(TipoCambioMoneda.id).where(
            TipoCambioMoneda.moneda_id == currency_id, TipoCambioMoneda.origen == "AUTOMATICO").limit(1))
        attempt = db.scalar(select(TipoCambioRegistro.id).where(TipoCambioRegistro.moneda_id == currency_id).limit(1))
        if automatic is not None or attempt is not None:
            raise HTTPException(status_code=409, detail="No puedes cambiar la identidad de una moneda con historial automático.")
    _ensure_unique_currency_code(db, payload.codigo, exclude_id=currency.id)
    _ensure_base_constraints(db, target=currency, es_base=payload.es_base, habilitado=payload.habilitado)
    _sync_base_currency(db, current_id=currency.id, make_base=payload.es_base)
    currency.codigo = payload.codigo
    currency.nombre = payload.nombre
    currency.simbolo = payload.simbolo
    currency.es_base = payload.es_base
    currency.habilitado = payload.habilitado or payload.es_base
    register_audit_event(
        db,
        action="CURRENCY_UPDATED",
        description=f"Se actualizó la moneda '{currency.codigo}'.",
        account=updated_by,
        user=updated_by.usuario,
        reference=str(currency.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_currency(db, currency.id)


@_atomic_write
def set_currency_status(
    db: Session,
    *,
    currency_id: int,
    enabled: bool,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> MonedaResponse:
    currency = _get_currency_entity(db, currency_id)
    db.execute(select(Moneda.id).where(Moneda.id == currency_id).with_for_update())
    db.refresh(currency)
    if currency.es_base and not enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes deshabilitar la moneda base.")
    currency.habilitado = enabled
    register_audit_event(
        db,
        action="CURRENCY_STATUS_CHANGED",
        description=f"Se actualizó el estado de la moneda '{currency.codigo}' a {'ACTIVA' if enabled else 'INACTIVA'}.",
        account=changed_by,
        user=changed_by.usuario,
        reference=str(currency.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_currency(db, currency.id)


def list_exchange_rates(
    db: Session,
    *,
    moneda_id: int | None = None,
    is_active: bool | None = None,
) -> list[TipoCambioListItem]:
    stmt = (
        select(TipoCambioMoneda)
        .options(joinedload(TipoCambioMoneda.moneda), joinedload(TipoCambioMoneda.usuario))
        .order_by(TipoCambioMoneda.fecha_registro.desc(), TipoCambioMoneda.id.desc())
    )
    if moneda_id is not None:
        stmt = stmt.where(TipoCambioMoneda.moneda_id == moneda_id)
    if is_active is not None:
        stmt = stmt.where(TipoCambioMoneda.activo.is_(is_active))
    return [_to_exchange_rate_list_item(rate) for rate in db.execute(stmt).scalars().all()]


def get_exchange_rate(db: Session, rate_id: int) -> TipoCambioDetailResponse:
    return _to_exchange_rate_detail(_get_exchange_rate_entity(db, rate_id))


@_atomic_write
def create_exchange_rate(
    db: Session,
    *,
    payload: TipoCambioCreateRequest,
    created_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> TipoCambioDetailResponse:
    _ensure_exchange_admin(created_by)
    rate = insert_rate(db,
        moneda_id=payload.moneda_id,
        usuario_id=created_by.usuario_id,
        valor_bob=payload.valor_bob,
        observaciones=payload.observaciones,
        operativo=True,
    )
    db.commit()
    return get_exchange_rate(db, rate.id)


@_atomic_write
def update_exchange_rate(
    db: Session,
    *,
    rate_id: int,
    payload: TipoCambioUpdateRequest,
    updated_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> TipoCambioDetailResponse:
    _ensure_exchange_admin(updated_by)
    rate = _get_exchange_rate_entity(db, rate_id)
    lock_currency(db, rate.moneda_id)
    rate = _get_exchange_rate_entity(db, rate_id)
    _ensure_manual(rate)
    value_changed = payload.valor_bob is not None and validate_rate(payload.valor_bob) != rate.valor_bob
    if value_changed:
        if payload.activo is False:
            raise HTTPException(status_code=422, detail="Una nueva cotización operativa debe quedar activa.")
        rate = insert_rate(db, moneda_id=rate.moneda_id, valor_bob=payload.valor_bob,
            usuario_id=updated_by.usuario_id, observaciones=payload.observaciones, operativo=True)
    else:
        if payload.activo is not None and payload.activo != rate.activo:
            raise HTTPException(status_code=409, detail="Utiliza la acción de estado; una tasa antigua no puede reactivarse.")
        if "observaciones" in payload.model_fields_set:
            rate.observaciones = payload.observaciones
    db.commit()
    return get_exchange_rate(db, rate.id)


@_atomic_write
def set_exchange_rate_status(
    db: Session,
    *,
    rate_id: int,
    active: bool,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> TipoCambioDetailResponse:
    _ensure_exchange_admin(changed_by)
    rate = _get_exchange_rate_entity(db, rate_id)
    lock_currency(db, rate.moneda_id)
    rate = _get_exchange_rate_entity(db, rate_id)
    _ensure_manual(rate)
    if rate.moneda.es_base and not active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes desactivar el tipo de cambio de la moneda base.")
    if active and not rate.activo:
        raise HTTPException(status_code=409, detail="No puedes reactivar una cotización histórica. Registra una nueva tasa manual con ese valor.")
    rate.activo = active
    db.commit()
    return get_exchange_rate(db, rate.id)


def get_active_exchange_rate_for_currency(db: Session, currency_id: int) -> TipoCambioMoneda | None:
    return db.execute(
        select(TipoCambioMoneda)
        .options(joinedload(TipoCambioMoneda.moneda))
        .where(TipoCambioMoneda.moneda_id == currency_id, TipoCambioMoneda.activo.is_(True))
    ).scalar_one_or_none()
