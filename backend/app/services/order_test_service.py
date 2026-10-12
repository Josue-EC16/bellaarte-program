from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.audit import register_audit_event
from app.models.account import Cuenta
from app.models.boutique_enums import EstadoPedidoGeneralEnum, PruebaEstadoPedidoEnum, TipoPedidoEnum
from app.models.client import Cliente
from app.models.order import Pedido, PruebaPedido
from app.schemas.order import OrderTestCreateRequest, OrderTestListItem, OrderTestUpdateRequest
from app.services.notification_service import sync_material_preparation_notification_for_test, sync_test_schedule_notifications_for_test


def _get_test_entity(db: Session, test_id: int) -> PruebaPedido:
    test = db.execute(
        select(PruebaPedido).options(joinedload(PruebaPedido.pedido).joinedload(Pedido.cliente)).where(PruebaPedido.id == test_id)
    ).scalar_one_or_none()
    if test is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prueba de pedido no encontrada.")
    return test


def _get_active_order(db: Session, order_id: int) -> Pedido:
    order = db.execute(select(Pedido).options(joinedload(Pedido.cliente)).where(Pedido.id == order_id)).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado.")
    if order.estado_general != EstadoPedidoGeneralEnum.ACTIVO or not order.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo puedes registrar pruebas sobre pedidos activos y habilitados.")
    return order


def _validate_test_date(order: Pedido, test_date: date) -> None:
    if test_date < date.today():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La fecha de prueba no puede ser anterior a la fecha actual.")
    if test_date > order.fecha_entrega:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La fecha de prueba no puede quedar después de la fecha de entrega comprometida.")
    if order.fecha_entrega_final and test_date > order.fecha_entrega_final:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La prueba no puede quedar después de la entrega final.")


def _to_list_item(test: PruebaPedido) -> OrderTestListItem:
    return OrderTestListItem(
        id=test.id,
        pedido_id=test.pedido_id,
        pedido_codigo=test.pedido.codigo,
        tipo=test.pedido.tipo,
        client_name=test.pedido.cliente.nombre_completo,
        numero=test.numero,
        fecha=test.fecha,
        hora=test.hora,
        estado=test.estado,
        observaciones=test.observaciones,
        fecha_entrega=test.pedido.fecha_entrega,
    )


def list_order_tests(
    db: Session,
    *,
    search: str | None = None,
    order_id: int | None = None,
    client_id: int | None = None,
    state: PruebaEstadoPedidoEnum | None = None,
    type_: TipoPedidoEnum | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[OrderTestListItem]:
    stmt = (
        select(PruebaPedido)
        .options(joinedload(PruebaPedido.pedido).joinedload(Pedido.cliente))
        .order_by(PruebaPedido.fecha.asc(), PruebaPedido.hora.asc().nulls_last(), PruebaPedido.numero.asc())
    )
    if order_id is not None:
        stmt = stmt.where(PruebaPedido.pedido_id == order_id)
    if state is not None:
        stmt = stmt.where(PruebaPedido.estado == state)
    if date_from is not None:
        stmt = stmt.where(PruebaPedido.fecha >= date_from)
    if date_to is not None:
        stmt = stmt.where(PruebaPedido.fecha <= date_to)
    if client_id is not None or type_ is not None or search:
        stmt = stmt.join(PruebaPedido.pedido).join(Pedido.cliente)
    if client_id is not None:
        stmt = stmt.where(Pedido.cliente_id == client_id)
    if type_ is not None:
        stmt = stmt.where(Pedido.tipo == type_)
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.where(
            or_(
                func.upper(Pedido.codigo).like(term),
                func.upper(Cliente.codigo).like(term),
                func.upper(Cliente.nombres).like(term),
                func.upper(Cliente.apellido_paterno).like(term),
            )
        )
    return [_to_list_item(test) for test in db.execute(stmt).unique().scalars().all()]


def get_order_test_detail(db: Session, test_id: int) -> OrderTestListItem:
    return _to_list_item(_get_test_entity(db, test_id))


def create_order_test(
    db: Session,
    *,
    order_id: int,
    payload: OrderTestCreateRequest,
    created_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> OrderTestListItem:
    order = _get_active_order(db, order_id)
    _validate_test_date(order, payload.fecha)
    duplicate = db.execute(select(PruebaPedido.id).where(PruebaPedido.pedido_id == order.id, PruebaPedido.numero == payload.numero)).scalar_one_or_none()
    if duplicate is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe una prueba con ese número para el pedido.")
    if payload.numero > 1:
        previous = db.execute(select(PruebaPedido.id).where(PruebaPedido.pedido_id == order.id, PruebaPedido.numero == payload.numero - 1)).scalar_one_or_none()
        if previous is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Debes registrar la prueba anterior antes de continuar la secuencia.")
    test = PruebaPedido(
        pedido_id=order.id,
        numero=payload.numero,
        fecha=payload.fecha,
        hora=payload.hora,
        estado=payload.estado,
        observaciones=payload.observaciones,
    )
    db.add(test)
    db.flush()
    register_audit_event(
        db,
        action="ORDER_TEST_CREATED",
        description=f"Se registró la prueba {test.numero} para el pedido {order.codigo}.",
        account=created_by,
        user=created_by.usuario,
        reference=str(test.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    sync_test_schedule_notifications_for_test(db, test_id=test.id)
    sync_material_preparation_notification_for_test(db, test_id=test.id)
    db.commit()
    return get_order_test_detail(db, test.id)


def update_order_test(
    db: Session,
    *,
    test_id: int,
    payload: OrderTestUpdateRequest,
    updated_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> OrderTestListItem:
    test = _get_test_entity(db, test_id)
    if test.pedido.estado_general != EstadoPedidoGeneralEnum.ACTIVO or not test.pedido.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo puedes editar pruebas de pedidos activos y habilitados.")
    _validate_test_date(test.pedido, payload.fecha)
    test.fecha = payload.fecha
    test.hora = payload.hora
    test.estado = payload.estado
    test.observaciones = payload.observaciones
    register_audit_event(
        db,
        action="ORDER_TEST_UPDATED",
        description=f"Se actualizó la prueba {test.numero} del pedido {test.pedido.codigo}.",
        account=updated_by,
        user=updated_by.usuario,
        reference=str(test.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    sync_test_schedule_notifications_for_test(db, test_id=test.id)
    sync_material_preparation_notification_for_test(db, test_id=test.id)
    db.commit()
    return get_order_test_detail(db, test.id)
