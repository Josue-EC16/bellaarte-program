from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.audit import register_audit_event
from app.models.account import Cuenta
from app.models.currency import Moneda
from app.models.exchange_rate import TipoCambioMoneda
from app.schemas.currency import (
    MonedaCreateRequest,
    MonedaResponse,
    MonedaUpdateRequest,
    TipoCambioCreateRequest,
    TipoCambioDetailResponse,
    TipoCambioListItem,
    TipoCambioUpdateRequest,
)


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
        valor_bob=float(rate.valor_bob),
        activo=rate.activo,
        registrado_por=rate.usuario.nombre_completo,
        fecha_registro=rate.fecha_registro,
    )


def _to_exchange_rate_detail(rate: TipoCambioMoneda) -> TipoCambioDetailResponse:
    return TipoCambioDetailResponse(
        id=rate.id,
        moneda=_to_currency_response(rate.moneda),
        valor_bob=float(rate.valor_bob),
        observaciones=rate.observaciones,
        activo=rate.activo,
        registrado_por=rate.usuario.nombre_completo,
        fecha_registro=rate.fecha_registro,
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


def _deactivate_existing_active_rates(db: Session, currency_id: int, *, exclude_id: int | None = None) -> None:
    stmt = select(TipoCambioMoneda).where(TipoCambioMoneda.moneda_id == currency_id, TipoCambioMoneda.activo.is_(True))
    if exclude_id is not None:
        stmt = stmt.where(TipoCambioMoneda.id != exclude_id)
    for rate in db.execute(stmt).scalars().all():
        rate.activo = False


def list_exchange_rates(
    db: Session,
    *,
    moneda_id: int | None = None,
    is_active: bool | None = None,
) -> list[TipoCambioListItem]:
    stmt = (
        select(TipoCambioMoneda)
        .options(joinedload(TipoCambioMoneda.moneda), joinedload(TipoCambioMoneda.usuario))
        .order_by(TipoCambioMoneda.fecha_registro.desc())
    )
    if moneda_id is not None:
        stmt = stmt.where(TipoCambioMoneda.moneda_id == moneda_id)
    if is_active is not None:
        stmt = stmt.where(TipoCambioMoneda.activo.is_(is_active))
    return [_to_exchange_rate_list_item(rate) for rate in db.execute(stmt).scalars().all()]


def get_exchange_rate(db: Session, rate_id: int) -> TipoCambioDetailResponse:
    return _to_exchange_rate_detail(_get_exchange_rate_entity(db, rate_id))


def create_exchange_rate(
    db: Session,
    *,
    payload: TipoCambioCreateRequest,
    created_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> TipoCambioDetailResponse:
    currency = _get_currency_entity(db, payload.moneda_id)
    if not currency.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes operar con monedas deshabilitadas.")
    if currency.es_base and float(payload.valor_bob) != 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La moneda base debe registrar valor 1.")
    if payload.activo:
        _deactivate_existing_active_rates(db, currency.id)
    rate = TipoCambioMoneda(
        moneda_id=currency.id,
        usuario_id=created_by.usuario_id,
        valor_bob=payload.valor_bob,
        observaciones=payload.observaciones,
        activo=payload.activo,
    )
    db.add(rate)
    db.flush()
    register_audit_event(
        db,
        action="EXCHANGE_RATE_CREATED",
        description=f"Se creó el tipo de cambio para '{currency.codigo}'.",
        account=created_by,
        user=created_by.usuario,
        reference=str(rate.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_exchange_rate(db, rate.id)


def update_exchange_rate(
    db: Session,
    *,
    rate_id: int,
    payload: TipoCambioUpdateRequest,
    updated_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> TipoCambioDetailResponse:
    rate = _get_exchange_rate_entity(db, rate_id)
    if rate.moneda.es_base and float(payload.valor_bob) != 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La moneda base debe registrar valor 1.")
    if payload.activo and not rate.moneda.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes activar tipos de cambio para monedas deshabilitadas.")
    if payload.activo:
        _deactivate_existing_active_rates(db, rate.moneda_id, exclude_id=rate.id)
    rate.valor_bob = payload.valor_bob
    rate.observaciones = payload.observaciones
    rate.activo = payload.activo
    register_audit_event(
        db,
        action="EXCHANGE_RATE_UPDATED",
        description=f"Se actualizó el tipo de cambio de '{rate.moneda.codigo}'.",
        account=updated_by,
        user=updated_by.usuario,
        reference=str(rate.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_exchange_rate(db, rate.id)


def set_exchange_rate_status(
    db: Session,
    *,
    rate_id: int,
    active: bool,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> TipoCambioDetailResponse:
    rate = _get_exchange_rate_entity(db, rate_id)
    if rate.moneda.es_base and not active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes desactivar el tipo de cambio de la moneda base.")
    if active:
        if not rate.moneda.habilitado:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes activar tipos de cambio para monedas deshabilitadas.")
        _deactivate_existing_active_rates(db, rate.moneda_id, exclude_id=rate.id)
    rate.activo = active
    register_audit_event(
        db,
        action="EXCHANGE_RATE_STATUS_CHANGED",
        description=f"Se actualizó el estado del tipo de cambio de '{rate.moneda.codigo}' a {'ACTIVO' if active else 'INACTIVO'}.",
        account=changed_by,
        user=changed_by.usuario,
        reference=str(rate.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_exchange_rate(db, rate.id)


def get_active_exchange_rate_for_currency(db: Session, currency_id: int) -> TipoCambioMoneda | None:
    return db.execute(
        select(TipoCambioMoneda)
        .options(joinedload(TipoCambioMoneda.moneda))
        .where(TipoCambioMoneda.moneda_id == currency_id, TipoCambioMoneda.activo.is_(True))
    ).scalar_one_or_none()
