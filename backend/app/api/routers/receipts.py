from datetime import date

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps.auth import require_permission
from app.models.account import Cuenta
from app.models.boutique_enums import EstadoComprobanteEnum, MetodoPagoEnum
from app.schemas.receipt import (
    ReceiptDetailResponse,
    ReceiptListItem,
    ReceiptTypeCreateRequest,
    ReceiptTypeResponse,
    ReceiptTypeStatusUpdateRequest,
    ReceiptTypeUpdateRequest,
)
from app.services.receipt_service import (
    build_receipt_printable_html,
    create_receipt_type,
    get_receipt_detail,
    get_receipt_type,
    list_receipt_types,
    list_receipts,
    set_receipt_type_status,
    update_receipt_type,
)


router = APIRouter()


@router.get("/tipos", response_model=list[ReceiptTypeResponse])
def get_receipt_types(
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("receipt_types:list")),
) -> list[ReceiptTypeResponse]:
    return list_receipt_types(db)


@router.get("/tipos/{type_id}", response_model=ReceiptTypeResponse)
def get_receipt_type_detail(
    type_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("receipt_types:view")),
) -> ReceiptTypeResponse:
    return get_receipt_type(db, type_id)


@router.post("/tipos", response_model=ReceiptTypeResponse, status_code=status.HTTP_201_CREATED)
def create_receipt_type_record(
    payload: ReceiptTypeCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("receipt_types:create")),
) -> ReceiptTypeResponse:
    return create_receipt_type(
        db,
        payload=payload,
        created_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/tipos/{type_id}", response_model=ReceiptTypeResponse)
def update_receipt_type_record(
    type_id: int,
    payload: ReceiptTypeUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("receipt_types:update")),
) -> ReceiptTypeResponse:
    return update_receipt_type(
        db,
        type_id=type_id,
        payload=payload,
        updated_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.patch("/tipos/{type_id}/status", response_model=ReceiptTypeResponse)
def update_receipt_type_record_status(
    type_id: int,
    payload: ReceiptTypeStatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("receipt_types:update_status")),
) -> ReceiptTypeResponse:
    return set_receipt_type_status(
        db,
        type_id=type_id,
        enabled=payload.habilitado,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("", response_model=list[ReceiptListItem])
def get_receipts(
    search: str | None = Query(default=None, min_length=1),
    origin_type: str | None = Query(default=None, pattern="^(VENTA_BOUTIQUE|PAGO_PEDIDO|SALIDA_FLETE)$"),
    state: EstadoComprobanteEnum | None = Query(default=None),
    currency_id: int | None = Query(default=None, gt=0),
    payment_method: MetodoPagoEnum | None = Query(default=None),
    client_id: int | None = Query(default=None, gt=0),
    user_id: int | None = Query(default=None, gt=0),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("receipts:list")),
) -> list[ReceiptListItem]:
    return list_receipts(
        db,
        search=search,
        origin_type=origin_type,
        state=state,
        currency_id=currency_id,
        payment_method=payment_method,
        client_id=client_id,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/{receipt_id}", response_model=ReceiptDetailResponse)
def get_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("receipts:view")),
) -> ReceiptDetailResponse:
    return get_receipt_detail(db, receipt_id)


@router.get("/{receipt_id}/printable")
def get_receipt_printable(
    receipt_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("receipts:print")),
) -> Response:
    return Response(content=build_receipt_printable_html(db, receipt_id), media_type="text/html")
