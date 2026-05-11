from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.audit import register_audit_event
from app.models.account import Cuenta
from app.models.boutique_enums import EstadoVentaBoutiqueEnum
from app.models.boutique_item import ItemBoutique
from app.models.boutique_sale import VentaBoutique
from app.models.client import Cliente
from app.models.currency import Moneda
from app.models.user import Usuario
from app.schemas.boutique import (
    BoutiqueSaleCreateRequest,
    BoutiqueSaleCurrencySummary,
    BoutiqueSaleDetailResponse,
    BoutiqueSaleItemSummary,
    BoutiqueSaleListItem,
    BoutiqueSaleClientSummary,
    BoutiqueSaleUserSummary,
)
from app.services.currency_service import get_active_exchange_rate_for_currency


def _to_float(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _get_sale_entity(db: Session, sale_id: int) -> VentaBoutique:
    sale = db.execute(
        select(VentaBoutique)
        .options(
            joinedload(VentaBoutique.item).joinedload(ItemBoutique.tipo_item),
            joinedload(VentaBoutique.cliente),
            joinedload(VentaBoutique.usuario).joinedload(Usuario.cuenta),
            joinedload(VentaBoutique.moneda),
        )
        .where(VentaBoutique.id == sale_id)
    ).scalar_one_or_none()
    if sale is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venta boutique no encontrada.")
    return sale


def _get_item_for_sale(db: Session, item_id: int) -> ItemBoutique:
    item = db.execute(
        select(ItemBoutique)
        .options(joinedload(ItemBoutique.tipo_item))
        .where(ItemBoutique.id == item_id)
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto boutique no encontrado.")
    if not item.estado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El producto boutique está inactivo.")
    if not item.tipo_item.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El tipo boutique del producto está deshabilitado.")
    return item


def _get_client_for_sale(db: Session, client_id: int | None) -> Cliente | None:
    if client_id is None:
        return None
    client = db.execute(select(Cliente).where(Cliente.id == client_id)).scalar_one_or_none()
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado.")
    if not client.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El cliente está inactivo.")
    return client


def _get_currency_for_sale(db: Session, currency_id: int) -> Moneda:
    currency = db.execute(select(Moneda).where(Moneda.id == currency_id)).scalar_one_or_none()
    if currency is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Moneda no encontrada.")
    if not currency.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes operar con monedas deshabilitadas.")
    return currency


def _to_sale_list_item(sale: VentaBoutique) -> BoutiqueSaleListItem:
    return BoutiqueSaleListItem(
        id=sale.id,
        fecha=sale.fecha,
        estado=sale.estado,
        payment_method=sale.metodo_pago,
        item_id=sale.item.id,
        item_code=sale.item.codigo,
        item_name=sale.item.nombre,
        client_id=sale.cliente.id if sale.cliente else None,
        client_code=sale.cliente.codigo if sale.cliente else None,
        client_name=sale.cliente.nombre_completo if sale.cliente else None,
        currency_code=sale.moneda.codigo,
        registered_by=sale.usuario.nombre_completo,
        quantity=sale.cantidad,
        unit_price=float(sale.precio_unitario),
        discount=_to_float(sale.descuento),
        total=float(sale.total),
        total_currency_origin=float(sale.total_moneda_original),
    )


def get_boutique_sale_detail(db: Session, sale_id: int) -> BoutiqueSaleDetailResponse:
    sale = _get_sale_entity(db, sale_id)
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
        client=BoutiqueSaleClientSummary(
            id=sale.cliente.id,
            codigo=sale.cliente.codigo,
            full_name=sale.cliente.nombre_completo,
        )
        if sale.cliente
        else None,
        currency=BoutiqueSaleCurrencySummary(
            id=sale.moneda.id,
            codigo=sale.moneda.codigo,
            nombre=sale.moneda.nombre,
            simbolo=sale.moneda.simbolo,
            es_base=sale.moneda.es_base,
        ),
        registered_by=BoutiqueSaleUserSummary(
            id=sale.usuario.id,
            full_name=sale.usuario.nombre_completo,
            username=sale.usuario.cuenta.username if sale.usuario.cuenta else "",
        ),
        quantity=sale.cantidad,
        unit_price=float(sale.precio_unitario),
        discount=_to_float(sale.descuento),
        discount_reason=sale.motivo_descuento,
        total=float(sale.total),
        exchange_rate_used=float(sale.tipo_cambio_usado),
        total_currency_origin=float(sale.total_moneda_original),
        observations=sale.observaciones,
        changed_at=sale.fecha_cambio_estado,
        state_change_reason=sale.motivo_cambio_estado,
    )


def list_boutique_sales(
    db: Session,
    *,
    search: str | None = None,
    item_id: int | None = None,
    client_id: int | None = None,
    payment_method=None,
    state=None,
    currency_id: int | None = None,
    date_from=None,
    date_to=None,
) -> list[BoutiqueSaleListItem]:
    stmt = (
        select(VentaBoutique)
        .options(
            joinedload(VentaBoutique.item).joinedload(ItemBoutique.tipo_item),
            joinedload(VentaBoutique.cliente),
            joinedload(VentaBoutique.usuario),
            joinedload(VentaBoutique.moneda),
        )
        .order_by(VentaBoutique.fecha.desc())
    )
    if item_id is not None:
        stmt = stmt.where(VentaBoutique.item_id == item_id)
    if client_id is not None:
        stmt = stmt.where(VentaBoutique.cliente_id == client_id)
    if payment_method is not None:
        stmt = stmt.where(VentaBoutique.metodo_pago == payment_method)
    if state is not None:
        stmt = stmt.where(VentaBoutique.estado == state)
    if currency_id is not None:
        stmt = stmt.where(VentaBoutique.moneda_id == currency_id)
    if date_from is not None:
        stmt = stmt.where(func.date(VentaBoutique.fecha) >= date_from)
    if date_to is not None:
        stmt = stmt.where(func.date(VentaBoutique.fecha) <= date_to)
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.join(VentaBoutique.item).outerjoin(VentaBoutique.cliente).where(
            or_(
                func.upper(ItemBoutique.codigo).like(term),
                func.upper(ItemBoutique.nombre).like(term),
                func.upper(func.coalesce(Cliente.codigo, "")).like(term),
                func.upper(func.concat(func.coalesce(Cliente.nombres, ""), " ", func.coalesce(Cliente.apellido_paterno, ""))).like(term),
            )
        )
    return [_to_sale_list_item(sale) for sale in db.execute(stmt).unique().scalars().all()]


def create_boutique_sale(
    db: Session,
    *,
    payload: BoutiqueSaleCreateRequest,
    created_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> BoutiqueSaleDetailResponse:
    if not created_by.is_active or not created_by.usuario.activo or not created_by.rol.activo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="La cuenta usada para registrar la venta no está habilitada.")

    item = _get_item_for_sale(db, payload.item_id)
    client = _get_client_for_sale(db, payload.client_id)
    currency = _get_currency_for_sale(db, payload.currency_id)

    if payload.quantity > item.stock:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La cantidad vendida no puede ser mayor al stock disponible.")

    unit_price = Decimal(item.precio_venta)
    subtotal = Decimal(payload.quantity) * unit_price
    discount = Decimal(payload.discount or 0)
    if discount > subtotal:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El descuento no puede ser mayor al subtotal de la venta.")
    total_bob = subtotal - discount
    if total_bob <= 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El total final de la venta debe ser mayor a cero.")

    if currency.es_base:
        exchange_rate_used = Decimal("1")
        total_currency_origin = total_bob
    else:
        exchange_rate = get_active_exchange_rate_for_currency(db, currency.id)
        if exchange_rate is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La moneda seleccionada no tiene un tipo de cambio activo.")
        exchange_rate_used = Decimal(exchange_rate.valor_bob)
        total_currency_origin = (total_bob / exchange_rate_used).quantize(Decimal("0.01"))

    sale = VentaBoutique(
        item_id=item.id,
        usuario_id=created_by.usuario_id,
        cliente_id=client.id if client else None,
        moneda_id=currency.id,
        cantidad=payload.quantity,
        precio_unitario=unit_price,
        descuento=discount if discount > 0 else None,
        motivo_descuento=payload.discount_reason if discount > 0 else None,
        tipo_cambio_usado=exchange_rate_used,
        total_moneda_original=total_currency_origin,
        metodo_pago=payload.payment_method,
        observaciones=payload.observations,
        estado=EstadoVentaBoutiqueEnum.ACTIVA,
    )
    item.stock -= payload.quantity
    db.add(sale)
    db.flush()
    register_audit_event(
        db,
        action="BOUTIQUE_SALE_CREATED",
        description=f"Se registró la venta boutique '{sale.id}' del producto '{item.codigo}'.",
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
    sale = _get_sale_entity(db, sale_id)
    if sale.estado != EstadoVentaBoutiqueEnum.ACTIVA:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo puedes cambiar el estado de ventas activas.")
    if target_state not in {EstadoVentaBoutiqueEnum.CANCELADA, EstadoVentaBoutiqueEnum.ANULADA}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El estado destino no es válido para una reversión.")

    sale.estado = target_state
    sale.fecha_cambio_estado = datetime.now(timezone.utc)
    sale.motivo_cambio_estado = reason
    sale.item.stock += sale.cantidad
    register_audit_event(
        db,
        action="BOUTIQUE_SALE_CANCELLED" if target_state == EstadoVentaBoutiqueEnum.CANCELADA else "BOUTIQUE_SALE_ANNULLED",
        description=f"Se cambió la venta boutique '{sale.id}' a estado '{target_state.value}'.",
        account=changed_by,
        user=changed_by.usuario,
        reference=str(sale.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_boutique_sale_detail(db, sale.id)
