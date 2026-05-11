from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps.auth import require_permission
from app.models.account import Cuenta
from app.schemas.currency import (
    MonedaCreateRequest,
    MonedaResponse,
    MonedaStatusUpdateRequest,
    MonedaUpdateRequest,
    TipoCambioCreateRequest,
    TipoCambioDetailResponse,
    TipoCambioListItem,
    TipoCambioStatusUpdateRequest,
    TipoCambioUpdateRequest,
)
from app.services.currency_service import (
    create_currency,
    create_exchange_rate,
    get_currency,
    get_exchange_rate,
    list_currencies,
    list_exchange_rates,
    set_currency_status,
    set_exchange_rate_status,
    update_currency,
    update_exchange_rate,
)


router = APIRouter()


# ── monedas ─────────────────────────────────────────────────

@router.get("", response_model=list[MonedaResponse])
def get_currencies(
    search: str | None = Query(default=None, min_length=1),
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("currencies:list")),
) -> list[MonedaResponse]:
    return list_currencies(db, search=search, is_active=is_active)


@router.post("", response_model=MonedaResponse, status_code=status.HTTP_201_CREATED)
def create_currency_record(
    payload: MonedaCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("currencies:create")),
) -> MonedaResponse:
    return create_currency(
        db,
        payload=payload,
        created_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


# ── tipos de cambio (rutas literales ANTES de las paramétricas) ──

@router.get("/tipos-cambio", response_model=list[TipoCambioListItem])
def get_exchange_rates(
    moneda_id: int | None = Query(default=None, gt=0),
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("exchange_rates:list")),
) -> list[TipoCambioListItem]:
    return list_exchange_rates(db, moneda_id=moneda_id, is_active=is_active)


@router.get("/tipos-cambio/{rate_id}", response_model=TipoCambioDetailResponse)
def get_exchange_rate_detail(
    rate_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("exchange_rates:view")),
) -> TipoCambioDetailResponse:
    return get_exchange_rate(db, rate_id)


@router.post("/tipos-cambio", response_model=TipoCambioDetailResponse, status_code=status.HTTP_201_CREATED)
def create_exchange_rate_record(
    payload: TipoCambioCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("exchange_rates:create")),
) -> TipoCambioDetailResponse:
    return create_exchange_rate(
        db,
        payload=payload,
        created_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/tipos-cambio/{rate_id}", response_model=TipoCambioDetailResponse)
def update_exchange_rate_record(
    rate_id: int,
    payload: TipoCambioUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("exchange_rates:update")),
) -> TipoCambioDetailResponse:
    return update_exchange_rate(
        db,
        rate_id=rate_id,
        payload=payload,
        updated_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/tipos-cambio/{rate_id}/status", response_model=TipoCambioDetailResponse)
def update_exchange_rate_record_status(
    rate_id: int,
    payload: TipoCambioStatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("exchange_rates:update_status")),
) -> TipoCambioDetailResponse:
    return set_exchange_rate_status(
        db,
        rate_id=rate_id,
        active=payload.activo,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


# ── monedas paramétricas (DESPUÉS de las rutas literales) ────

@router.get("/{currency_id}", response_model=MonedaResponse)
def get_currency_detail(
    currency_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("currencies:view")),
) -> MonedaResponse:
    return get_currency(db, currency_id)


@router.patch("/{currency_id}", response_model=MonedaResponse)
def update_currency_record(
    currency_id: int,
    payload: MonedaUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("currencies:update")),
) -> MonedaResponse:
    return update_currency(
        db,
        currency_id=currency_id,
        payload=payload,
        updated_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/{currency_id}/status", response_model=MonedaResponse)
def update_currency_record_status(
    currency_id: int,
    payload: MonedaStatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("currencies:update_status")),
) -> MonedaResponse:
    return set_currency_status(
        db,
        currency_id=currency_id,
        enabled=payload.habilitado,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
