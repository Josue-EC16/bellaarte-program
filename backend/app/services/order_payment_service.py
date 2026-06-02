from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.audit import register_audit_event
from app.models.account import Cuenta
from app.models.boutique_enums import EstadoPagoPedidoEnum, EstadoPedidoGeneralEnum
from app.models.client import Cliente
from app.models.currency import Moneda
from app.models.order import PagoPedido, Pedido
from app.models.user import Usuario
from app.schemas.order import OrderCurrencySummary, OrderPaymentAnnulRequest, OrderPaymentCreateRequest, OrderPaymentDetailResponse, OrderPaymentListItem
from app.services.currency_service import get_active_exchange_rate_for_currency
from app.services.notification_service import sync_order_delivery_notifications_for_order
from app.services.order_service import recalculate_order_balance
from app.services.receipt_service import _to_receipt_summary, annul_receipt, create_order_payment_receipt


def _to_float(value) -> float:
    return float(value or 0)


def _money(value) -> Decimal:
    return Decimal(str(value or 0))


def _currency_summary(currency: Moneda) -> OrderCurrencySummary:
    return OrderCurrencySummary(id=currency.id, codigo=currency.codigo, nombre=currency.nombre, simbolo=currency.simbolo, es_base=currency.es_base)


def _get_payment_entity(db: Session, payment_id: int) -> PagoPedido:
    payment = db.execute(
        select(PagoPedido)
        .options(
            joinedload(PagoPedido.pedido).joinedload(Pedido.cliente),
            joinedload(PagoPedido.usuario),
            joinedload(PagoPedido.moneda),
            joinedload(PagoPedido.comprobante),
        )
        .where(PagoPedido.id == payment_id)
    ).scalar_one_or_none()
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pago de pedido no encontrado.")
    return payment


def _to_list_item(payment: PagoPedido) -> OrderPaymentListItem:
    return OrderPaymentListItem(
        id=payment.id,
        pedido_id=payment.pedido_id,
        pedido_codigo=payment.pedido.codigo,
        client_name=payment.pedido.cliente.nombre_completo,
        currency=_currency_summary(payment.moneda),
        fecha=payment.fecha,
        monto=_to_float(payment.monto),
        tipo_cambio_usado=_to_float(payment.tipo_cambio_usado),
        monto_bob=_to_float(payment.monto_bob),
        metodo_pago=payment.metodo_pago,
        estado=payment.estado,
        registered_by=payment.usuario.nombre_completo,
    )


def _to_detail_response(payment: PagoPedido) -> OrderPaymentDetailResponse:
    base = _to_list_item(payment).model_dump()
    return OrderPaymentDetailResponse(
        **base,
        observaciones=payment.observaciones,
        fecha_cambio_estado=payment.fecha_cambio_estado,
        motivo_cambio_estado=payment.motivo_cambio_estado,
        receipt=_to_receipt_summary(payment.comprobante),
    )


def list_order_payments(
    db: Session,
    *,
    search: str | None = None,
    order_id: int | None = None,
    client_id: int | None = None,
    state: EstadoPagoPedidoEnum | None = None,
    currency_id: int | None = None,
    payment_method=None,
    user_id: int | None = None,
    date_from=None,
    date_to=None,
) -> list[OrderPaymentListItem]:
    stmt = (
        select(PagoPedido)
        .options(joinedload(PagoPedido.pedido).joinedload(Pedido.cliente), joinedload(PagoPedido.usuario), joinedload(PagoPedido.moneda))
        .order_by(PagoPedido.fecha.desc(), PagoPedido.id.desc())
    )
    if order_id is not None:
        stmt = stmt.where(PagoPedido.pedido_id == order_id)
    if client_id is not None:
        stmt = stmt.join(PagoPedido.pedido).where(Pedido.cliente_id == client_id)
    if state is not None:
        stmt = stmt.where(PagoPedido.estado == state)
    if currency_id is not None:
        stmt = stmt.where(PagoPedido.moneda_id == currency_id)
    if payment_method is not None:
        stmt = stmt.where(PagoPedido.metodo_pago == payment_method)
    if user_id is not None:
        stmt = stmt.where(PagoPedido.usuario_id == user_id)
    if date_from is not None:
        stmt = stmt.where(func.date(PagoPedido.fecha) >= date_from)
    if date_to is not None:
        stmt = stmt.where(func.date(PagoPedido.fecha) <= date_to)
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.join(PagoPedido.pedido).join(Pedido.cliente).where(
            or_(
                func.upper(Pedido.codigo).like(term),
                func.upper(Cliente.codigo).like(term),
                func.upper(Cliente.nombres).like(term),
                func.upper(Cliente.apellido_paterno).like(term),
            )
        )
    return [_to_list_item(payment) for payment in db.execute(stmt).unique().scalars().all()]


def get_payment_detail(db: Session, payment_id: int) -> OrderPaymentDetailResponse:
    return _to_detail_response(_get_payment_entity(db, payment_id))


def create_order_payment(
    db: Session,
    *,
    order_id: int,
    payload: OrderPaymentCreateRequest,
    created_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> OrderPaymentDetailResponse:
    order = db.execute(select(Pedido).options(joinedload(Pedido.cliente)).where(Pedido.id == order_id)).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado.")
    if order.estado_general != EstadoPedidoGeneralEnum.ACTIVO or not order.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo puedes registrar pagos sobre pedidos activos y habilitados.")
    currency = db.execute(select(Moneda).where(Moneda.id == payload.currency_id)).scalar_one_or_none()
    if currency is None or not currency.habilitado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Moneda no encontrada o inactiva.")
    exchange_rate = Decimal("1")
    if not currency.es_base:
        active_rate = get_active_exchange_rate_for_currency(db, currency.id)
        if active_rate is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La moneda seleccionada no tiene tipo de cambio activo.")
        exchange_rate = _money(active_rate.valor_bob)
    amount_bob = (_money(payload.monto) * exchange_rate).quantize(Decimal("0.01"))
    if amount_bob > _money(order.saldo):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El pago no puede ser mayor al saldo pendiente del pedido.")
    payment = PagoPedido(
        pedido_id=order.id,
        usuario_id=created_by.usuario_id,
        moneda_id=currency.id,
        monto=payload.monto,
        tipo_cambio_usado=exchange_rate,
        metodo_pago=payload.metodo_pago,
        observaciones=payload.observaciones,
        estado=EstadoPagoPedidoEnum.REGISTRADO,
    )
    db.add(payment)
    db.flush()
    db.refresh(payment)
    recalculate_order_balance(db, order)
    create_order_payment_receipt(
        db,
        payment=payment,
        order=order,
        snapshot_payload=payload.receipt_customer_snapshot,
    )
    register_audit_event(
        db,
        action="ORDER_PAYMENT_CREATED",
        description=f"Se registró un pago de pedido por {payment.monto_bob} Bs para {order.codigo}.",
        account=created_by,
        user=created_by.usuario,
        reference=str(payment.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    sync_order_delivery_notifications_for_order(db, order_id=order.id)
    db.commit()
    return get_payment_detail(db, payment.id)


def annul_order_payment(
    db: Session,
    *,
    payment_id: int,
    payload: OrderPaymentAnnulRequest,
    annulled_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> OrderPaymentDetailResponse:
    payment = _get_payment_entity(db, payment_id)
    if payment.estado != EstadoPagoPedidoEnum.REGISTRADO:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo puedes anular pagos registrados.")
    payment.estado = EstadoPagoPedidoEnum.ANULADO
    payment.fecha_cambio_estado = datetime.now(timezone.utc)
    payment.motivo_cambio_estado = payload.reason
    annul_receipt(payment.comprobante, reason=payload.reason)
    recalculate_order_balance(db, payment.pedido)
    register_audit_event(
        db,
        action="ORDER_PAYMENT_ANNULLED",
        description=f"Se anuló el pago {payment.id} del pedido {payment.pedido.codigo}.",
        account=annulled_by,
        user=annulled_by.usuario,
        reference=str(payment.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    sync_order_delivery_notifications_for_order(db, order_id=payment.pedido_id)
    db.commit()
    return get_payment_detail(db, payment.id)
