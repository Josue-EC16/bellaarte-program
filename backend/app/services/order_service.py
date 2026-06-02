from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.audit import register_audit_event
from app.models.account import Cuenta
from app.models.boutique_enums import EstadoPagoPedidoEnum, EstadoPedidoGeneralEnum, TipoPedidoEnum
from app.models.client import Cliente
from app.models.order import Pedido, PedidoBouquet, PedidoCola, PedidoManga, PedidoOtro, PedidoVelo, PedidoVestido, PagoPedido, PruebaPedido
from app.models.user import Usuario
from app.schemas.order import (
    OrderClientSummary,
    OrderCreateRequest,
    OrderDeliverRequest,
    OrderDetailResponse,
    OrderListItem,
    OrderPaymentSummary,
    OrderStatusUpdateRequest,
    OrderTestSummary,
    OrderUpdateRequest,
    OrderUserSummary,
    PedidoBouquetPayload,
    PedidoColaPayload,
    PedidoMangaPayload,
    PedidoOtroPayload,
    PedidoVeloPayload,
    PedidoVestidoPayload,
)
from app.services.notification_service import sync_order_delivery_notifications_for_order


DETAIL_MODEL_BY_TYPE = {
    TipoPedidoEnum.VESTIDO: PedidoVestido,
    TipoPedidoEnum.VELO: PedidoVelo,
    TipoPedidoEnum.COLA: PedidoCola,
    TipoPedidoEnum.MANGA: PedidoManga,
    TipoPedidoEnum.BOUQUET: PedidoBouquet,
    TipoPedidoEnum.OTRO: PedidoOtro,
}
DETAIL_SCHEMA_BY_TYPE = {
    TipoPedidoEnum.VESTIDO: PedidoVestidoPayload,
    TipoPedidoEnum.VELO: PedidoVeloPayload,
    TipoPedidoEnum.COLA: PedidoColaPayload,
    TipoPedidoEnum.MANGA: PedidoMangaPayload,
    TipoPedidoEnum.BOUQUET: PedidoBouquetPayload,
    TipoPedidoEnum.OTRO: PedidoOtroPayload,
}
DETAIL_RELATION_BY_TYPE = {
    TipoPedidoEnum.VESTIDO: "vestido",
    TipoPedidoEnum.VELO: "velo",
    TipoPedidoEnum.COLA: "cola",
    TipoPedidoEnum.MANGA: "manga",
    TipoPedidoEnum.BOUQUET: "bouquet",
    TipoPedidoEnum.OTRO: "otro",
}


def _to_float(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _money(value: Decimal | float | int | None) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _ensure_operating_account(account: Cuenta) -> None:
    if not account.is_active or not account.usuario.activo or not account.rol.activo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="La cuenta usada para operar pedidos no está habilitada.")


def _get_client(db: Session, client_id: int) -> Cliente:
    client = db.execute(select(Cliente).where(Cliente.id == client_id)).scalar_one_or_none()
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado.")
    if not client.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes operar pedidos con un cliente inactivo.")
    return client


def _get_user(db: Session, user_id: int) -> Usuario:
    user = db.execute(select(Usuario).where(Usuario.id == user_id)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario encargado no encontrado.")
    if not user.activo:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El usuario encargado está inactivo.")
    return user


def _base_order_options():
    return (
        joinedload(Pedido.cliente),
        joinedload(Pedido.usuario_encargado).joinedload(Usuario.cuenta),
        joinedload(Pedido.vestido),
        joinedload(Pedido.velo),
        joinedload(Pedido.cola),
        joinedload(Pedido.manga),
        joinedload(Pedido.bouquet),
        joinedload(Pedido.otro),
        selectinload(Pedido.pagos),
        selectinload(Pedido.pruebas),
    )


def _get_order_entity(db: Session, order_id: int) -> Pedido:
    order = db.execute(select(Pedido).options(*_base_order_options()).where(Pedido.id == order_id)).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado.")
    return order


def _generate_order_code(db: Session) -> str:
    counter = db.execute(select(func.count(Pedido.id))).scalar_one() + 1
    while True:
        code = f"PED-{counter:05d}"
        if db.execute(select(Pedido.id).where(func.upper(Pedido.codigo) == code)).scalar_one_or_none() is None:
            return code
        counter += 1


def _ensure_unique_order_code(db: Session, code: str, *, exclude_id: int | None = None) -> str:
    normalized = code.strip().upper()
    stmt = select(Pedido.id).where(func.upper(Pedido.codigo) == normalized)
    if exclude_id is not None:
        stmt = stmt.where(Pedido.id != exclude_id)
    if db.execute(stmt).scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un pedido con ese código.")
    return normalized


def _parse_detail(tipo: TipoPedidoEnum, raw_detail: dict[str, Any] | None) -> dict[str, Any]:
    if not raw_detail:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"El pedido de tipo {tipo.value} requiere detalle especializado.")
    schema_cls = DETAIL_SCHEMA_BY_TYPE[tipo]
    try:
        return schema_cls.model_validate(raw_detail).model_dump()
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc


def _detail_dict(order: Pedido) -> dict[str, Any] | None:
    relation = DETAIL_RELATION_BY_TYPE[order.tipo]
    detail = getattr(order, relation)
    if detail is None:
        return None
    schema_cls = DETAIL_SCHEMA_BY_TYPE[order.tipo]
    return {
        field_name: _to_float(value) if isinstance(value, Decimal) else value
        for field_name in schema_cls.model_fields.keys()
        for value in [getattr(detail, field_name)]
    }


def _to_client_summary(client: Cliente) -> OrderClientSummary:
    return OrderClientSummary(id=client.id, codigo=client.codigo, full_name=client.nombre_completo, celular=client.celular)


def _to_user_summary(user: Usuario) -> OrderUserSummary:
    username = user.cuenta.username if user.cuenta else None
    return OrderUserSummary(id=user.id, full_name=user.nombre_completo, username=username)


def _to_payment_summary(payment: PagoPedido) -> OrderPaymentSummary:
    return OrderPaymentSummary(
        id=payment.id,
        fecha=payment.fecha,
        monto=_to_float(payment.monto) or 0,
        monto_bob=_to_float(payment.monto_bob) or 0,
        metodo_pago=payment.metodo_pago,
        estado=payment.estado,
    )


def _to_test_summary(test: PruebaPedido) -> OrderTestSummary:
    return OrderTestSummary(id=test.id, numero=test.numero, fecha=test.fecha, hora=test.hora, estado=test.estado)


def _to_list_item(order: Pedido) -> OrderListItem:
    return OrderListItem(
        id=order.id,
        codigo=order.codigo,
        tipo=order.tipo,
        client_id=order.cliente_id,
        client_name=order.cliente.nombre_completo,
        fecha_entrega=order.fecha_entrega,
        precio_total=_to_float(order.precio_total) or 0,
        total_pagado=_to_float(order.total_pagado) or 0,
        saldo=_to_float(order.saldo) or 0,
        estado_general=order.estado_general,
        habilitado=order.habilitado,
        viaje=order.viaje,
    )


def _to_detail_response(order: Pedido) -> OrderDetailResponse:
    return OrderDetailResponse(
        id=order.id,
        codigo=order.codigo,
        tipo=order.tipo,
        client=_to_client_summary(order.cliente),
        usuario_encargado=_to_user_summary(order.usuario_encargado),
        fecha_contrato=order.fecha_contrato,
        fecha_entrega=order.fecha_entrega,
        fecha_entrega_final=order.fecha_entrega_final,
        viaje=order.viaje,
        pais_destino=order.pais_destino,
        ciudad_destino=order.ciudad_destino,
        precio=_to_float(order.precio) or 0,
        descuento=_to_float(order.descuento),
        motivo_descuento=order.motivo_descuento,
        precio_total=_to_float(order.precio_total) or 0,
        total_pagado=_to_float(order.total_pagado) or 0,
        saldo=_to_float(order.saldo) or 0,
        observaciones=order.observaciones,
        estado_general=order.estado_general,
        fecha_cambio_estado=order.fecha_cambio_estado,
        motivo_cambio_estado=order.motivo_cambio_estado,
        habilitado=order.habilitado,
        detail=_detail_dict(order),
        pagos=sorted([_to_payment_summary(payment) for payment in order.pagos], key=lambda item: item.fecha, reverse=True),
        pruebas=sorted([_to_test_summary(test) for test in order.pruebas], key=lambda item: (item.fecha, item.numero)),
    )


def recalculate_order_balance(db: Session, order: Pedido) -> None:
    db.flush()
    db.refresh(order)
    paid = db.execute(
        select(func.coalesce(func.sum(PagoPedido.monto_bob), 0)).where(
            PagoPedido.pedido_id == order.id,
            PagoPedido.estado == EstadoPagoPedidoEnum.REGISTRADO,
        )
    ).scalar_one()
    order.total_pagado = paid
    order.saldo = max(Decimal("0"), _money(order.precio_total) - _money(paid))
    db.flush()


def list_orders(
    db: Session,
    *,
    search: str | None = None,
    state: EstadoPedidoGeneralEnum | None = None,
    type_: TipoPedidoEnum | None = None,
    client_id: int | None = None,
    only_travel: bool | None = None,
) -> list[OrderListItem]:
    stmt = select(Pedido).options(joinedload(Pedido.cliente)).order_by(Pedido.fecha_entrega.asc(), Pedido.id.desc())
    if state is not None:
        stmt = stmt.where(Pedido.estado_general == state)
    if type_ is not None:
        stmt = stmt.where(Pedido.tipo == type_)
    if client_id is not None:
        stmt = stmt.where(Pedido.cliente_id == client_id)
    if only_travel is not None:
        stmt = stmt.where(Pedido.viaje.is_(only_travel))
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.join(Pedido.cliente).where(
            or_(
                func.upper(Pedido.codigo).like(term),
                func.upper(Cliente.codigo).like(term),
                func.upper(Cliente.nombres).like(term),
                func.upper(Cliente.apellido_paterno).like(term),
                func.upper(func.coalesce(Cliente.ci, "")).like(term),
            )
        )
    return [_to_list_item(order) for order in db.execute(stmt).unique().scalars().all()]


def get_order_detail(db: Session, order_id: int) -> OrderDetailResponse:
    return _to_detail_response(_get_order_entity(db, order_id))


def create_order(
    db: Session,
    *,
    payload: OrderCreateRequest,
    created_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> OrderDetailResponse:
    _ensure_operating_account(created_by)
    _get_client(db, payload.order.client_id)
    _get_user(db, created_by.usuario_id)
    code = _ensure_unique_order_code(db, payload.order.codigo) if payload.order.codigo else _generate_order_code(db)
    detail_data = _parse_detail(payload.order.tipo, payload.detail)
    order = Pedido(
        cliente_id=payload.order.client_id,
        codigo=code,
        tipo=payload.order.tipo,
        usuario_encargado_id=created_by.usuario_id,
        fecha_entrega=payload.order.fecha_entrega,
        viaje=payload.order.viaje,
        pais_destino=payload.order.pais_destino,
        ciudad_destino=payload.order.ciudad_destino,
        precio=payload.order.precio,
        descuento=payload.order.descuento,
        motivo_descuento=payload.order.motivo_descuento,
        observaciones=payload.order.observaciones,
        estado_general=EstadoPedidoGeneralEnum.ACTIVO,
        habilitado=True,
    )
    db.add(order)
    db.flush()
    detail_model = DETAIL_MODEL_BY_TYPE[payload.order.tipo]
    db.add(detail_model(pedido_id=order.id, **detail_data))
    recalculate_order_balance(db, order)
    register_audit_event(
        db,
        action="ORDER_CREATED",
        description=f"Se creó el pedido {order.codigo}.",
        account=created_by,
        user=created_by.usuario,
        reference=str(order.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    sync_order_delivery_notifications_for_order(db, order_id=order.id)
    db.commit()
    return get_order_detail(db, order.id)


def update_order(
    db: Session,
    *,
    order_id: int,
    payload: OrderUpdateRequest,
    updated_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> OrderDetailResponse:
    _ensure_operating_account(updated_by)
    order = _get_order_entity(db, order_id)
    if order.estado_general != EstadoPedidoGeneralEnum.ACTIVO or not order.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo puedes editar pedidos activos y habilitados.")
    if payload.order.tipo != order.tipo:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No se puede cambiar el tipo de pedido después de creado.")
    code = _ensure_unique_order_code(db, payload.order.codigo, exclude_id=order.id) if payload.order.codigo else order.codigo
    order.cliente_id = payload.order.client_id
    _get_client(db, order.cliente_id)
    order.codigo = code
    order.fecha_entrega = payload.order.fecha_entrega
    order.viaje = payload.order.viaje
    order.pais_destino = payload.order.pais_destino
    order.ciudad_destino = payload.order.ciudad_destino
    order.precio = payload.order.precio
    order.descuento = payload.order.descuento
    order.motivo_descuento = payload.order.motivo_descuento
    order.observaciones = payload.order.observaciones
    if payload.detail is not None:
        detail_data = _parse_detail(order.tipo, payload.detail)
        relation = DETAIL_RELATION_BY_TYPE[order.tipo]
        detail = getattr(order, relation)
        if detail is None:
            detail = DETAIL_MODEL_BY_TYPE[order.tipo](pedido_id=order.id)
            db.add(detail)
            setattr(order, relation, detail)
        for key, value in detail_data.items():
            setattr(detail, key, value)
    recalculate_order_balance(db, order)
    if _money(order.precio_total) < _money(order.total_pagado):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El nuevo total no puede quedar por debajo de los pagos registrados.")
    register_audit_event(
        db,
        action="ORDER_UPDATED",
        description=f"Se actualizó el pedido {order.codigo}.",
        account=updated_by,
        user=updated_by.usuario,
        reference=str(order.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    sync_order_delivery_notifications_for_order(db, order_id=order.id)
    db.commit()
    return get_order_detail(db, order.id)


def change_order_status(
    db: Session,
    *,
    order_id: int,
    payload: OrderStatusUpdateRequest,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> OrderDetailResponse:
    order = _get_order_entity(db, order_id)
    if payload.target_state == EstadoPedidoGeneralEnum.ENTREGADO:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usa el flujo de entrega para marcar pedidos como entregados.")
    if payload.target_state == EstadoPedidoGeneralEnum.INACTIVO:
        if order.estado_general != EstadoPedidoGeneralEnum.ACTIVO:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo puedes inactivar pedidos activos.")
        has_payment = db.execute(select(PagoPedido.id).where(PagoPedido.pedido_id == order.id).limit(1)).scalar_one_or_none()
        if has_payment is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes inactivar pedidos con pagos registrados.")
        order.estado_general = EstadoPedidoGeneralEnum.INACTIVO
        order.habilitado = False
    elif payload.target_state == EstadoPedidoGeneralEnum.CANCELADO:
        if order.estado_general != EstadoPedidoGeneralEnum.ACTIVO:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo puedes cancelar pedidos activos.")
        order.estado_general = EstadoPedidoGeneralEnum.CANCELADO
        order.habilitado = True
    elif payload.target_state == EstadoPedidoGeneralEnum.ACTIVO:
        if order.estado_general != EstadoPedidoGeneralEnum.INACTIVO:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo puedes reactivar pedidos inactivos.")
        order.estado_general = EstadoPedidoGeneralEnum.ACTIVO
        order.habilitado = True
        order.fecha_cambio_estado = None
        order.motivo_cambio_estado = None
    if payload.target_state != EstadoPedidoGeneralEnum.ACTIVO:
        order.fecha_cambio_estado = datetime.now(timezone.utc)
        order.motivo_cambio_estado = payload.reason
    register_audit_event(
        db,
        action="ORDER_CANCELLED" if order.estado_general == EstadoPedidoGeneralEnum.CANCELADO else "ORDER_STATUS_CHANGED",
        description=f"Se cambió el estado del pedido {order.codigo} a {order.estado_general.value}.",
        account=changed_by,
        user=changed_by.usuario,
        reference=str(order.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    sync_order_delivery_notifications_for_order(db, order_id=order.id)
    db.commit()
    return get_order_detail(db, order.id)


def deliver_order(
    db: Session,
    *,
    order_id: int,
    payload: OrderDeliverRequest,
    delivered_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> OrderDetailResponse:
    order = _get_order_entity(db, order_id)
    if order.estado_general != EstadoPedidoGeneralEnum.ACTIVO or not order.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo puedes entregar pedidos activos y habilitados.")
    if payload.fecha_entrega_final < order.fecha_contrato.date():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La fecha final de entrega no puede ser anterior a la fecha de contrato.")
    if payload.fecha_entrega_final < order.fecha_entrega:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La fecha final de entrega no puede ser anterior a la fecha de entrega comprometida.")
    if _money(order.saldo) > Decimal("0"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes entregar un pedido con saldo pendiente.")
    order.fecha_entrega_final = payload.fecha_entrega_final
    order.estado_general = EstadoPedidoGeneralEnum.ENTREGADO
    order.observaciones = payload.observaciones or order.observaciones
    register_audit_event(
        db,
        action="ORDER_DELIVERED",
        description=f"Se entregó el pedido {order.codigo}.",
        account=delivered_by,
        user=delivered_by.usuario,
        reference=str(order.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    sync_order_delivery_notifications_for_order(db, order_id=order.id)
    db.commit()
    return get_order_detail(db, order.id)
