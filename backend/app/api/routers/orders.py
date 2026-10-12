from datetime import date

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps.auth import require_permission
from app.models.account import Cuenta
from app.models.boutique_enums import EstadoPagoPedidoEnum, EstadoPedidoGeneralEnum, MetodoPagoEnum, PruebaEstadoPedidoEnum, TipoPedidoEnum
from app.schemas.order import (
    ClientOrderSummaryReport,
    OrderBalanceReportItem,
    OrderCreateRequest,
    OrderDeliverRequest,
    OrderDetailResponse,
    OrderListItem,
    OrderPaymentAnnulRequest,
    OrderPaymentCreateRequest,
    OrderPaymentDetailResponse,
    OrderPaymentListItem,
    OrderStatusUpdateRequest,
    OrderTestCreateRequest,
    OrderTestListItem,
    OrderTestUpdateRequest,
    OrderUpdateRequest,
)
from app.services.order_payment_service import annul_order_payment, create_order_payment, get_payment_detail, list_order_payments
from app.services.order_report_service import (
    build_client_printable_html,
    get_client_order_summary,
    list_order_balance_report,
    list_order_delivery_report,
    list_order_payment_report,
    list_order_test_report,
)
from app.services.order_service import change_order_status, create_order, deliver_order, get_order_detail, list_orders, update_order
from app.services.order_test_service import create_order_test, get_order_test_detail, list_order_tests, update_order_test


router = APIRouter()


@router.get("/pagos", response_model=list[OrderPaymentListItem])
def get_payments(
    search: str | None = Query(default=None, min_length=1),
    order_id: int | None = Query(default=None, gt=0),
    client_id: int | None = Query(default=None, gt=0),
    state: EstadoPagoPedidoEnum | None = Query(default=None),
    currency_id: int | None = Query(default=None, gt=0),
    payment_method: MetodoPagoEnum | None = Query(default=None),
    user_id: int | None = Query(default=None, gt=0),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("order_payments:list")),
) -> list[OrderPaymentListItem]:
    return list_order_payments(
        db,
        search=search,
        order_id=order_id,
        client_id=client_id,
        state=state,
        currency_id=currency_id,
        payment_method=payment_method,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/pagos/{pago_id}", response_model=OrderPaymentDetailResponse)
def get_payment(
    pago_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("order_payments:view")),
) -> OrderPaymentDetailResponse:
    return get_payment_detail(db, pago_id)


@router.patch("/pagos/{pago_id}/annul", response_model=OrderPaymentDetailResponse)
def annul_payment(
    pago_id: int,
    payload: OrderPaymentAnnulRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("order_payments:annul")),
) -> OrderPaymentDetailResponse:
    return annul_order_payment(
        db,
        payment_id=pago_id,
        payload=payload,
        annulled_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/pruebas", response_model=list[OrderTestListItem])
def get_tests(
    search: str | None = Query(default=None, min_length=1),
    order_id: int | None = Query(default=None, gt=0),
    client_id: int | None = Query(default=None, gt=0),
    state: PruebaEstadoPedidoEnum | None = Query(default=None),
    type_: TipoPedidoEnum | None = Query(default=None, alias="type"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("order_tests:list")),
) -> list[OrderTestListItem]:
    return list_order_tests(db, search=search, order_id=order_id, client_id=client_id, state=state, type_=type_, date_from=date_from, date_to=date_to)


@router.get("/pruebas/{prueba_id}", response_model=OrderTestListItem)
def get_test(
    prueba_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("order_tests:view")),
) -> OrderTestListItem:
    return get_order_test_detail(db, prueba_id)


@router.patch("/pruebas/{prueba_id}", response_model=OrderTestListItem)
def update_test(
    prueba_id: int,
    payload: OrderTestUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("order_tests:update")),
) -> OrderTestListItem:
    return update_order_test(
        db,
        test_id=prueba_id,
        payload=payload,
        updated_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/reportes/clientes/{cliente_id}/resumen", response_model=ClientOrderSummaryReport)
def get_client_summary(
    cliente_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("order_reports:view")),
) -> ClientOrderSummaryReport:
    return get_client_order_summary(db, cliente_id)


@router.get("/reportes/saldos", response_model=list[OrderBalanceReportItem])
def get_balance_report(
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("order_reports:view")),
) -> list[OrderBalanceReportItem]:
    return list_order_balance_report(db)


@router.get("/reportes/pagos")
def get_payment_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("order_reports:view")),
):
    return list_order_payment_report(db, date_from=date_from, date_to=date_to)


@router.get("/reportes/pruebas")
def get_test_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("order_reports:view")),
):
    return list_order_test_report(db, date_from=date_from, date_to=date_to)


@router.get("/reportes/entregas", response_model=list[OrderListItem])
def get_delivery_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("order_reports:view")),
) -> list[OrderListItem]:
    return list_order_delivery_report(db, date_from=date_from, date_to=date_to)


@router.get("/reportes/clientes/{cliente_id}/imprimible")
def get_printable_client_report(
    cliente_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("order_reports:print")),
) -> Response:
    return Response(content=build_client_printable_html(db, cliente_id), media_type="text/html")


@router.get("", response_model=list[OrderListItem])
def get_orders(
    search: str | None = Query(default=None, min_length=1),
    state: EstadoPedidoGeneralEnum | None = Query(default=None),
    type_: TipoPedidoEnum | None = Query(default=None, alias="type"),
    client_id: int | None = Query(default=None, gt=0),
    only_travel: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("orders:list")),
) -> list[OrderListItem]:
    return list_orders(db, search=search, state=state, type_=type_, client_id=client_id, only_travel=only_travel)


@router.post("", response_model=OrderDetailResponse, status_code=status.HTTP_201_CREATED)
def post_order(
    payload: OrderCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("orders:create")),
) -> OrderDetailResponse:
    return create_order(db, payload=payload, created_by=account, ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))


@router.get("/{pedido_id}", response_model=OrderDetailResponse)
def get_order(
    pedido_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("orders:view")),
) -> OrderDetailResponse:
    return get_order_detail(db, pedido_id)


@router.patch("/{pedido_id}", response_model=OrderDetailResponse)
def patch_order(
    pedido_id: int,
    payload: OrderUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("orders:update")),
) -> OrderDetailResponse:
    return update_order(db, order_id=pedido_id, payload=payload, updated_by=account, ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))


@router.patch("/{pedido_id}/status", response_model=OrderDetailResponse)
def patch_order_status(
    pedido_id: int,
    payload: OrderStatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("orders:update_status")),
) -> OrderDetailResponse:
    return change_order_status(db, order_id=pedido_id, payload=payload, changed_by=account, ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))


@router.patch("/{pedido_id}/deliver", response_model=OrderDetailResponse)
def patch_order_deliver(
    pedido_id: int,
    payload: OrderDeliverRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("orders:deliver")),
) -> OrderDetailResponse:
    return deliver_order(db, order_id=pedido_id, payload=payload, delivered_by=account, ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))


@router.post("/{pedido_id}/pagos", response_model=OrderPaymentDetailResponse, status_code=status.HTTP_201_CREATED)
def post_order_payment(
    pedido_id: int,
    payload: OrderPaymentCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("order_payments:create")),
) -> OrderPaymentDetailResponse:
    return create_order_payment(db, order_id=pedido_id, payload=payload, created_by=account, ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))


@router.post("/{pedido_id}/pruebas", response_model=OrderTestListItem, status_code=status.HTTP_201_CREATED)
def post_order_test(
    pedido_id: int,
    payload: OrderTestCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("order_tests:create")),
) -> OrderTestListItem:
    return create_order_test(db, order_id=pedido_id, payload=payload, created_by=account, ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
