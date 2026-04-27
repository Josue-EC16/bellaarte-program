from datetime import date, datetime, time
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.audit import register_audit_event
from app.models.account import Cuenta
from app.models.boutique_enums import EstadoVentaBoutiqueEnum, MetodoPagoEnum
from app.models.boutique_item import ItemBoutique
from app.models.boutique_sale import VentaBoutique
from app.models.client import Cliente
from app.models.user import Usuario
from app.schemas.boutique import (
    BoutiqueSaleClientSummary,
    BoutiqueSaleCreateRequest,
    BoutiqueSaleDetailResponse,
    BoutiqueSaleItemSummary,
    BoutiqueSaleListItem,
    BoutiqueSaleUserSummary,
)


def _to_float(value: Decimal | float | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _base_sale_query():
    return select(VentaBoutique).options(
        joinedload(VentaBoutique.item).joinedload(ItemBoutique.tipo_item),
        joinedload(VentaBoutique.cliente),
        joinedload(VentaBoutique.usuario).joinedload(Usuario.cuenta),
    )


def _sale_to_list_item(sale: VentaBoutique) -> BoutiqueSaleListItem:
    client = sale.cliente
    return BoutiqueSaleListItem(
        id=sale.id,
        fecha=sale.fecha,
        estado=sale.estado,
        payment_method=sale.metodo_pago,
        item_id=sale.item.id,
        item_code=sale.item.codigo,
        item_name=sale.item.nombre,
        client_id=client.id if client else None,
        client_code=client.codigo if client else None,
        client_name=client.nombre_completo if client else None,
        registered_by=sale.usuario.nombre_completo,
        quantity=_to_float(sale.cantidad) or 0,
        unit_price=_to_float(sale.precio_unitario) or 0,
        discount=_to_float(sale.descuento),
        total=_to_float(sale.total) or 0,
    )


def _sale_to_detail(sale: VentaBoutique) -> BoutiqueSaleDetailResponse:
    client = None
    if sale.cliente is not None:
        client = BoutiqueSaleClientSummary(
            id=sale.cliente.id,
            codigo=sale.cliente.codigo,
            full_name=sale.cliente.nombre_completo,
        )
    return BoutiqueSaleDetailResponse(
        id=sale.id,
        fecha=sale.fecha,
        estado=sale.estado,
        payment_method=sale.metodo_pago,
        item=BoutiqueSaleItemSummary(
            id=sale.item.id,
            code=sale.item.codigo,
            name=sale.item.nombre,
            type_name=sale.item.tipo_item.nombre,
        ),
        client=client,
        registered_by=BoutiqueSaleUserSummary(
            id=sale.usuario.id,
            full_name=sale.usuario.nombre_completo,
            username=sale.usuario.cuenta.username,
        ),
        quantity=_to_float(sale.cantidad) or 0,
        unit_price=_to_float(sale.precio_unitario) or 0,
        discount=_to_float(sale.descuento),
        discount_reason=sale.motivo_descuento,
        total=_to_float(sale.total) or 0,
        observations=sale.observaciones,
    )


def get_boutique_sale_entity(db: Session, sale_id: int) -> VentaBoutique:
    sale = db.execute(_base_sale_query().where(VentaBoutique.id == sale_id)).scalar_one_or_none()
    if sale is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venta boutique no encontrada.")
    return sale


def get_boutique_sale_detail(db: Session, sale_id: int) -> BoutiqueSaleDetailResponse:
    return _sale_to_detail(get_boutique_sale_entity(db, sale_id))


def list_boutique_sales(
    db: Session,
    *,
    search: str | None = None,
    item_id: int | None = None,
    client_id: int | None = None,
    payment_method: MetodoPagoEnum | None = None,
    state: EstadoVentaBoutiqueEnum | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[BoutiqueSaleListItem]:
    stmt = _base_sale_query().order_by(VentaBoutique.fecha.desc(), VentaBoutique.id.desc())
    if item_id is not None:
        stmt = stmt.where(VentaBoutique.item_id == item_id)
    if client_id is not None:
        stmt = stmt.where(VentaBoutique.cliente_id == client_id)
    if payment_method is not None:
        stmt = stmt.where(VentaBoutique.metodo_pago == payment_method)
    if state is not None:
        stmt = stmt.where(VentaBoutique.estado == state)
    if date_from is not None:
        stmt = stmt.where(VentaBoutique.fecha >= datetime.combine(date_from, time.min))
    if date_to is not None:
        stmt = stmt.where(VentaBoutique.fecha <= datetime.combine(date_to, time.max))
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.join(VentaBoutique.item).join(ItemBoutique.tipo_item).join(VentaBoutique.usuario).outerjoin(VentaBoutique.cliente)
        stmt = stmt.where(
            or_(
                func.upper(ItemBoutique.codigo).like(term),
                func.upper(ItemBoutique.nombre).like(term),
                func.upper(func.coalesce(Cliente.codigo, "")).like(term),
                func.upper(func.coalesce(Cliente.nombres, "")).like(term),
                func.upper(func.coalesce(Cliente.apellido_paterno, "")).like(term),
                func.upper(func.coalesce(Cliente.apellido_materno, "")).like(term),
            )
        )
    sales = db.execute(stmt).scalars().unique().all()
    return [_sale_to_list_item(sale) for sale in sales]


def _get_item_for_sale(db: Session, item_id: int) -> ItemBoutique:
    item = db.execute(
        select(ItemBoutique).options(joinedload(ItemBoutique.tipo_item)).where(ItemBoutique.id == item_id)
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto boutique no encontrado.")
    if not item.estado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes vender un producto boutique inactivo.")
    if not item.tipo_item.habilitado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No puedes vender un producto cuyo tipo boutique está deshabilitado.",
        )
    return item


def _get_active_client(db: Session, client_id: int | None) -> Cliente | None:
    if client_id is None:
        return None
    client = db.execute(select(Cliente).where(Cliente.id == client_id)).scalar_one_or_none()
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado.")
    if not client.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes asociar un cliente inactivo a la venta.")
    return client


def create_boutique_sale(
    db: Session,
    *,
    payload: BoutiqueSaleCreateRequest,
    created_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> BoutiqueSaleDetailResponse:
    if payload.payment_method == MetodoPagoEnum.MIXTO:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El método de pago MIXTO no está disponible en esta versión.")

    item = _get_item_for_sale(db, payload.item_id)
    _get_active_client(db, payload.client_id)

    quantity = Decimal(str(payload.quantity)).quantize(Decimal("0.01"))
    unit_price = Decimal(str(item.precio_venta)).quantize(Decimal("0.01"))
    discount = Decimal(str(payload.discount)).quantize(Decimal("0.01")) if payload.discount is not None else None
    subtotal = (quantity * unit_price).quantize(Decimal("0.01"))

    if quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La cantidad vendida debe ser mayor a cero.")
    if Decimal(str(item.stock)) < quantity:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No hay stock suficiente para completar la venta.")
    if discount is not None and discount > subtotal:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El descuento no puede ser mayor al subtotal de la venta.")
    if discount is None and payload.discount_reason is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No debes enviar motivo de descuento si no existe descuento.")
    if discount is not None and payload.discount_reason is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Debes registrar el motivo del descuento.")

    sale = VentaBoutique(
        item_id=item.id,
        usuario_id=created_by.usuario.id,
        cliente_id=payload.client_id,
        cantidad=quantity,
        precio_unitario=unit_price,
        descuento=discount,
        motivo_descuento=payload.discount_reason,
        metodo_pago=payload.payment_method,
        observaciones=payload.observations,
        estado=EstadoVentaBoutiqueEnum.ACTIVA,
    )
    item.stock = Decimal(str(item.stock)) - quantity
    db.add(sale)
    db.flush()
    db.refresh(sale)

    register_audit_event(
        db,
        action="BOUTIQUE_SALE_CREATED",
        description=f"Se registró la venta boutique #{sale.id} del producto '{item.codigo}'.",
        account=created_by,
        user=created_by.usuario,
        reference=str(sale.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_boutique_sale_detail(db, sale.id)


def change_boutique_sale_state(
    db: Session,
    *,
    sale_id: int,
    target_state: EstadoVentaBoutiqueEnum,
    reason: str,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> BoutiqueSaleDetailResponse:
    sale = get_boutique_sale_entity(db, sale_id)
    if sale.estado != EstadoVentaBoutiqueEnum.ACTIVA:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo puedes revertir ventas que estén en estado ACTIVA.",
        )
    if target_state not in {EstadoVentaBoutiqueEnum.CANCELADA, EstadoVentaBoutiqueEnum.ANULADA}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El estado destino no es válido para una reversión.")

    sale.estado = target_state
    sale.item.stock = Decimal(str(sale.item.stock)) + Decimal(str(sale.cantidad))
    action = "BOUTIQUE_SALE_CANCELLED" if target_state == EstadoVentaBoutiqueEnum.CANCELADA else "BOUTIQUE_SALE_ANNULLED"
    label = "canceló" if target_state == EstadoVentaBoutiqueEnum.CANCELADA else "anuló"
    register_audit_event(
        db,
        action=action,
        description=f"Se {label} la venta boutique #{sale.id}. Motivo: {reason.strip().upper()}",
        account=changed_by,
        user=changed_by.usuario,
        reference=str(sale.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_boutique_sale_detail(db, sale.id)
