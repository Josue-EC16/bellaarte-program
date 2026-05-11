from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.audit import register_audit_event
from app.models.account import Cuenta
from app.models.boutique_entry import EntradaItemBoutique
from app.models.boutique_item import ItemBoutique
from app.models.provider import Proveedor
from app.models.user import Usuario
from app.schemas.boutique import (
    BoutiqueEntryCreateRequest,
    BoutiqueEntryDetailResponse,
    BoutiqueEntryItemSummary,
    BoutiqueEntryListItem,
    BoutiqueEntryUserSummary,
    ProveedorNested,
)


def _to_float(value):
    if value is None:
        return None
    return float(value)


def _get_item(db: Session, item_id: int) -> ItemBoutique:
    item = db.execute(
        select(ItemBoutique)
        .options(joinedload(ItemBoutique.tipo_item), joinedload(ItemBoutique.proveedor_rel))
        .where(ItemBoutique.id == item_id)
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto boutique no encontrado.")
    if not item.estado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes registrar entradas sobre productos inactivos.")
    if not item.tipo_item.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes registrar entradas sobre productos con tipo inactivo.")
    if item.proveedor_rel and not item.proveedor_rel.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes registrar entradas sobre productos con proveedor inactivo.")
    return item


def _get_provider(db: Session, provider_id: int | None) -> Proveedor | None:
    if provider_id is None:
        return None
    provider = db.execute(select(Proveedor).where(Proveedor.id == provider_id)).scalar_one_or_none()
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado.")
    if not provider.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El proveedor está deshabilitado.")
    return provider


def _get_entry(db: Session, entry_id: int) -> EntradaItemBoutique:
    entry = db.execute(
        select(EntradaItemBoutique)
        .options(
            joinedload(EntradaItemBoutique.item).joinedload(ItemBoutique.tipo_item),
            joinedload(EntradaItemBoutique.proveedor),
            joinedload(EntradaItemBoutique.usuario).joinedload(Usuario.cuenta),
        )
        .where(EntradaItemBoutique.id == entry_id)
    ).scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrada boutique no encontrada.")
    return entry


def _to_provider_nested(provider: Proveedor | None) -> ProveedorNested | None:
    if provider is None:
        return None
    return ProveedorNested(id=provider.id, full_name=provider.nombre_completo, nombre_comercial=provider.nombre_comercial)


def _to_detail_response(entry: EntradaItemBoutique) -> BoutiqueEntryDetailResponse:
    return BoutiqueEntryDetailResponse(
        id=entry.id,
        fecha=entry.fecha,
        item=BoutiqueEntryItemSummary(
            id=entry.item.id,
            code=entry.item.codigo,
            name=entry.item.nombre,
            type_name=entry.item.tipo_item.nombre,
        ),
        provider=_to_provider_nested(entry.proveedor),
        quantity=entry.cantidad,
        unit_cost=float(entry.costo_unitario),
        reason=entry.motivo,
        document_reference=entry.documento_referencia,
        observations=entry.observaciones,
        is_active=entry.estado,
        registered_by=BoutiqueEntryUserSummary(
            id=entry.usuario.id,
            full_name=entry.usuario.nombre_completo,
            username=entry.usuario.cuenta.username if entry.usuario.cuenta else "",
        ),
    )


def list_boutique_entries(
    db: Session,
    *,
    search: str | None = None,
    item_id: int | None = None,
    is_active: bool | None = None,
) -> list[BoutiqueEntryListItem]:
    stmt = (
        select(EntradaItemBoutique)
        .options(
            joinedload(EntradaItemBoutique.item).joinedload(ItemBoutique.tipo_item),
            joinedload(EntradaItemBoutique.proveedor),
            joinedload(EntradaItemBoutique.usuario),
        )
        .order_by(EntradaItemBoutique.fecha.desc(), EntradaItemBoutique.id.desc())
    )
    if item_id is not None:
        stmt = stmt.where(EntradaItemBoutique.item_id == item_id)
    if is_active is not None:
        stmt = stmt.where(EntradaItemBoutique.estado.is_(is_active))
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.join(EntradaItemBoutique.item).outerjoin(EntradaItemBoutique.proveedor).where(
            or_(
                func.upper(ItemBoutique.codigo).like(term),
                func.upper(ItemBoutique.nombre).like(term),
                func.upper(func.coalesce(Proveedor.nombre_comercial, "")).like(term),
            )
        )
    entries = db.execute(stmt).unique().scalars().all()
    return [
        BoutiqueEntryListItem(
            id=entry.id,
            fecha=entry.fecha,
            item=BoutiqueEntryItemSummary(
                id=entry.item.id,
                code=entry.item.codigo,
                name=entry.item.nombre,
                type_name=entry.item.tipo_item.nombre,
            ),
            provider_name=entry.proveedor.nombre_comercial if entry.proveedor and entry.proveedor.nombre_comercial else entry.proveedor.nombre_completo if entry.proveedor else None,
            quantity=entry.cantidad,
            unit_cost=float(entry.costo_unitario),
            reason=entry.motivo,
            document_reference=entry.documento_referencia,
            is_active=entry.estado,
            registered_by=entry.usuario.nombre_completo,
        )
        for entry in entries
    ]


def get_boutique_entry_detail(db: Session, entry_id: int) -> BoutiqueEntryDetailResponse:
    return _to_detail_response(_get_entry(db, entry_id))


def create_boutique_entry(
    db: Session,
    *,
    payload: BoutiqueEntryCreateRequest,
    created_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> BoutiqueEntryDetailResponse:
    item = _get_item(db, payload.item_id)
    provider = _get_provider(db, payload.provider_id)

    entry = EntradaItemBoutique(
        item_id=item.id,
        usuario_id=created_by.usuario_id,
        proveedor_id=provider.id if provider else None,
        cantidad=payload.quantity,
        costo_unitario=payload.unit_cost,
        motivo=payload.reason,
        documento_referencia=payload.document_reference,
        observaciones=payload.observations,
        estado=True,
    )
    item.stock += payload.quantity
    item.precio_compra = Decimal(str(payload.unit_cost))
    db.add(entry)
    db.flush()
    register_audit_event(
        db,
        action="BOUTIQUE_ENTRY_CREATED",
        description=f"Se registró la entrada boutique '{entry.id}' para el producto '{item.codigo}'.",
        account=created_by,
        user=created_by.usuario,
        reference=str(entry.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_boutique_entry_detail(db, entry.id)


def set_boutique_entry_status(
    db: Session,
    *,
    entry_id: int,
    is_active: bool,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> BoutiqueEntryDetailResponse:
    entry = _get_entry(db, entry_id)
    if entry.estado == is_active:
        return _to_detail_response(entry)

    if is_active:
        item = _get_item(db, entry.item_id)
        entry.estado = True
        item.stock += entry.cantidad
        item.precio_compra = entry.costo_unitario
    else:
        if entry.item.stock < entry.cantidad:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No puedes desactivar la entrada porque el stock actual es menor a la cantidad registrada en ese movimiento.",
            )
        entry.estado = False
        entry.item.stock -= entry.cantidad

    register_audit_event(
        db,
        action="BOUTIQUE_ENTRY_STATUS_CHANGED",
        description=f"Se actualizó el estado de la entrada boutique '{entry.id}' a {'ACTIVA' if is_active else 'INACTIVA'}.",
        account=changed_by,
        user=changed_by.usuario,
        reference=str(entry.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_boutique_entry_detail(db, entry.id)
