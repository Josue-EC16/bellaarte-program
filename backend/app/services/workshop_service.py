from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.audit import register_audit_event
from app.models.account import Cuenta
from app.models.provider import Proveedor
from app.models.user import Usuario
from app.models.workshop import EntradaInventarioTaller, InventarioTaller, SalidaMaterialTaller, TipoInventarioTaller
from app.schemas.boutique import ProveedorNested
from app.schemas.workshop import (
    TallerEntryCreateRequest,
    TallerEntryDetailResponse,
    TallerEntryListItem,
    TallerInventoryCreateRequest,
    TallerInventoryDetailResponse,
    TallerInventoryListItem,
    TallerItemSummary,
    TallerOutputCreateRequest,
    TallerOutputDetailResponse,
    TallerOutputListItem,
    TallerTypeNested,
    TallerTypeResponse,
    TallerUserSummary,
)
from app.services.notification_service import sync_workshop_stock_notification


def _to_float(value):
    if value is None:
        return None
    return float(value)


def _provider_nested(provider: Proveedor | None) -> ProveedorNested | None:
    if provider is None:
        return None
    return ProveedorNested(id=provider.id, full_name=provider.nombre_completo, nombre_comercial=provider.nombre_comercial)


def _item_summary(item: InventarioTaller) -> TallerItemSummary:
    return TallerItemSummary(
        id=item.id, 
        code=item.codigo, 
        name=item.nombre, 
        unit_measure=item.unidad_medida,
        type_name=item.tipo.nombre if getattr(item, "tipo", None) else None
    )


def _type_response(item_type: TipoInventarioTaller) -> TallerTypeResponse:
    return TallerTypeResponse(
        id=item_type.id,
        nombre=item_type.nombre,
        descripcion=item_type.descripcion,
        habilitado=item_type.habilitado,
        fecha_registro=item_type.fecha_registro,
    )


def _get_type(db: Session, type_id: int) -> TipoInventarioTaller:
    entity = db.execute(select(TipoInventarioTaller).where(TipoInventarioTaller.id == type_id)).scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de inventario de taller no encontrado.")
    return entity


def _get_provider(db: Session, provider_id: int | None) -> Proveedor | None:
    if provider_id is None:
        return None
    provider = db.execute(select(Proveedor).where(Proveedor.id == provider_id)).scalar_one_or_none()
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado.")
    if not provider.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El proveedor está deshabilitado.")
    return provider


def _get_inventory(db: Session, item_id: int) -> InventarioTaller:
    entity = db.execute(
        select(InventarioTaller)
        .options(joinedload(InventarioTaller.tipo), joinedload(InventarioTaller.proveedor))
        .where(InventarioTaller.id == item_id)
    ).scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material de taller no encontrado.")
    return entity


def _get_workshop_entry(db: Session, entry_id: int) -> EntradaInventarioTaller:
    entry = db.execute(
        select(EntradaInventarioTaller)
        .options(
            joinedload(EntradaInventarioTaller.item).joinedload(InventarioTaller.tipo),
            joinedload(EntradaInventarioTaller.proveedor),
            joinedload(EntradaInventarioTaller.usuario).joinedload(Usuario.cuenta),
        )
        .where(EntradaInventarioTaller.id == entry_id)
    ).scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrada de taller no encontrada.")
    return entry


def _get_workshop_output(db: Session, output_id: int) -> SalidaMaterialTaller:
    output = db.execute(
        select(SalidaMaterialTaller)
        .options(
            joinedload(SalidaMaterialTaller.item).joinedload(InventarioTaller.tipo),
            joinedload(SalidaMaterialTaller.usuario).joinedload(Usuario.cuenta),
        )
        .where(SalidaMaterialTaller.id == output_id)
    ).scalar_one_or_none()
    if output is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salida de taller no encontrada.")
    return output


def _ensure_type_unique(db: Session, nombre: str, exclude_id: int | None = None) -> None:
    stmt = select(TipoInventarioTaller).where(func.upper(TipoInventarioTaller.nombre) == nombre.strip().upper())
    if exclude_id is not None:
        stmt = stmt.where(TipoInventarioTaller.id != exclude_id)
    if db.execute(stmt).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un tipo de inventario de taller con ese nombre.")


def _ensure_inventory_unique(db: Session, code: str, exclude_id: int | None = None) -> None:
    stmt = select(InventarioTaller).where(func.upper(InventarioTaller.codigo) == code.strip().upper())
    if exclude_id is not None:
        stmt = stmt.where(InventarioTaller.id != exclude_id)
    if db.execute(stmt).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un material de taller con ese código.")


def list_workshop_types(db: Session) -> list[TallerTypeResponse]:
    return [_type_response(item) for item in db.execute(select(TipoInventarioTaller).order_by(TipoInventarioTaller.nombre.asc())).scalars().all()]


def get_workshop_type(db: Session, type_id: int) -> TallerTypeResponse:
    return _type_response(_get_type(db, type_id))


def create_workshop_type(db: Session, *, payload, created_by: Cuenta, ip_address: str | None, user_agent: str | None) -> TallerTypeResponse:
    _ensure_type_unique(db, payload.nombre)
    entity = TipoInventarioTaller(nombre=payload.nombre, descripcion=payload.descripcion, habilitado=True)
    db.add(entity)
    db.flush()
    register_audit_event(db, action="WORKSHOP_TYPE_CREATED", description=f"Se creó el tipo de taller '{entity.nombre}'.", account=created_by, user=created_by.usuario, reference=str(entity.id), ip_address=ip_address, user_agent=user_agent)
    db.commit()
    return _type_response(entity)


def update_workshop_type(db: Session, *, type_id: int, payload, updated_by: Cuenta, ip_address: str | None, user_agent: str | None) -> TallerTypeResponse:
    entity = _get_type(db, type_id)
    _ensure_type_unique(db, payload.nombre, exclude_id=entity.id)
    entity.nombre = payload.nombre
    entity.descripcion = payload.descripcion
    register_audit_event(db, action="WORKSHOP_TYPE_UPDATED", description=f"Se actualizó el tipo de taller '{entity.nombre}'.", account=updated_by, user=updated_by.usuario, reference=str(entity.id), ip_address=ip_address, user_agent=user_agent)
    db.commit()
    return _type_response(entity)


def set_workshop_type_status(db: Session, *, type_id: int, enabled: bool, changed_by: Cuenta, ip_address: str | None, user_agent: str | None) -> TallerTypeResponse:
    entity = _get_type(db, type_id)
    if not enabled:
        active_items = db.execute(select(InventarioTaller.id).where(InventarioTaller.tipo_id == entity.id, InventarioTaller.estado.is_(True))).first()
        if active_items is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes deshabilitar un tipo con materiales activos asociados.")
    entity.habilitado = enabled
    register_audit_event(db, action="WORKSHOP_TYPE_STATUS_CHANGED", description=f"Se actualizó el estado del tipo de taller '{entity.nombre}' a {'ACTIVO' if enabled else 'INACTIVO'}.", account=changed_by, user=changed_by.usuario, reference=str(entity.id), ip_address=ip_address, user_agent=user_agent)
    db.commit()
    return _type_response(entity)


def list_workshop_inventory(
    db: Session,
    *,
    type_id: int | None = None,
    search: str | None = None,
    is_active: bool | None = None,
    low_stock: bool | None = None,
) -> list[TallerInventoryListItem]:
    stmt = select(InventarioTaller).options(joinedload(InventarioTaller.tipo), joinedload(InventarioTaller.proveedor)).order_by(InventarioTaller.id.desc())
    if type_id is not None:
        stmt = stmt.where(InventarioTaller.tipo_id == type_id)
    if is_active is not None:
        stmt = stmt.where(InventarioTaller.estado.is_(is_active))
    if low_stock:
        stmt = stmt.where(InventarioTaller.stock <= InventarioTaller.stock_minimo)
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.where(
            or_(
                func.upper(InventarioTaller.codigo).like(term),
                func.upper(InventarioTaller.nombre).like(term),
                func.upper(InventarioTaller.color).like(term),
                func.upper(func.coalesce(InventarioTaller.material, "")).like(term),
            )
        )
    items = db.execute(stmt).scalars().all()
    return [
        TallerInventoryListItem(
            id=item.id,
            type_id=item.tipo.id,
            type_name=item.tipo.nombre,
            code=item.codigo,
            name=item.nombre,
            color=item.color,
            material=item.material,
            provider_name=item.proveedor.nombre_comercial if item.proveedor and item.proveedor.nombre_comercial else item.proveedor.nombre_completo if item.proveedor else None,
            stock=float(item.stock),
            unit_measure=item.unidad_medida,
            stock_min=float(item.stock_minimo),
            is_low_stock=float(item.stock) <= float(item.stock_minimo),
            is_active=item.estado,
            created_at=item.fecha_registro,
        )
        for item in items
    ]


def get_workshop_inventory_detail(db: Session, item_id: int) -> TallerInventoryDetailResponse:
    item = _get_inventory(db, item_id)
    return TallerInventoryDetailResponse(
        id=item.id,
        type=TallerTypeNested(id=item.tipo.id, nombre=item.tipo.nombre),
        provider=_provider_nested(item.proveedor),
        code=item.codigo,
        name=item.nombre,
        color=item.color,
        length=_to_float(item.largo),
        width=_to_float(item.ancho),
        material=item.material,
        description=item.descripcion,
        reference_cost=float(item.costo_referencia),
        stock=float(item.stock),
        unit_measure=item.unidad_medida,
        stock_min=float(item.stock_minimo),
        is_low_stock=float(item.stock) <= float(item.stock_minimo),
        is_active=item.estado,
        observations=item.observaciones,
        created_at=item.fecha_registro,
    )


def create_workshop_inventory(db: Session, *, payload: TallerInventoryCreateRequest, created_by: Cuenta, ip_address: str | None, user_agent: str | None) -> TallerInventoryDetailResponse:
    item_type = _get_type(db, payload.type_id)
    if not item_type.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El tipo de inventario de taller está deshabilitado.")
    provider = _get_provider(db, payload.provider_id)
    _ensure_inventory_unique(db, payload.code)
    item = InventarioTaller(
        tipo_id=item_type.id,
        proveedor_id=provider.id if provider else None,
        codigo=payload.code,
        nombre=payload.name,
        color=payload.color,
        largo=payload.length,
        ancho=payload.width,
        material=payload.material,
        descripcion=payload.description,
        costo_referencia=payload.reference_cost,
        stock=payload.stock,
        unidad_medida=payload.unit_measure,
        stock_minimo=payload.stock_min,
        estado=True,
        observaciones=payload.observations,
    )
    db.add(item)
    db.flush()
    register_audit_event(db, action="WORKSHOP_ITEM_CREATED", description=f"Se creó el material de taller '{item.codigo}'.", account=created_by, user=created_by.usuario, reference=item.codigo, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    return get_workshop_inventory_detail(db, item.id)


def update_workshop_inventory(db: Session, *, item_id: int, payload: TallerInventoryCreateRequest, updated_by: Cuenta, ip_address: str | None, user_agent: str | None) -> TallerInventoryDetailResponse:
    item = _get_inventory(db, item_id)
    item_type = _get_type(db, payload.type_id)
    if not item_type.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El tipo de inventario de taller está deshabilitado.")
    provider = _get_provider(db, payload.provider_id)
    _ensure_inventory_unique(db, payload.code, exclude_id=item.id)
    has_active_entries = db.execute(
        select(exists().where(EntradaInventarioTaller.item_id == item.id).where(EntradaInventarioTaller.estado.is_(True)))
    ).scalar()
    has_active_outputs = db.execute(
        select(exists().where(SalidaMaterialTaller.item_id == item.id).where(SalidaMaterialTaller.estado.is_(True)))
    ).scalar()
    has_movements = bool(has_active_entries or has_active_outputs)
    if has_movements and Decimal(str(payload.stock)) != item.stock:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El stock no puede editarse manualmente porque el material ya tiene movimientos registrados.")

    item.tipo_id = item_type.id
    item.proveedor_id = provider.id if provider else None
    item.codigo = payload.code
    item.nombre = payload.name
    item.color = payload.color
    item.largo = payload.length
    item.ancho = payload.width
    item.material = payload.material
    item.descripcion = payload.description
    item.costo_referencia = payload.reference_cost
    item.stock = payload.stock
    item.unidad_medida = payload.unit_measure
    item.stock_minimo = payload.stock_min
    item.observaciones = payload.observations
    register_audit_event(db, action="WORKSHOP_ITEM_UPDATED", description=f"Se actualizó el material de taller '{item.codigo}'.", account=updated_by, user=updated_by.usuario, reference=item.codigo, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    return get_workshop_inventory_detail(db, item.id)


def set_workshop_inventory_status(db: Session, *, item_id: int, is_active: bool, changed_by: Cuenta, ip_address: str | None, user_agent: str | None) -> TallerInventoryDetailResponse:
    item = _get_inventory(db, item_id)
    if is_active and not item.tipo.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes activar un material cuyo tipo está deshabilitado.")
    if is_active and item.proveedor and not item.proveedor.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes activar un material con proveedor deshabilitado.")
    item.estado = is_active
    register_audit_event(db, action="WORKSHOP_ITEM_STATUS_CHANGED", description=f"Se actualizó el estado del material de taller '{item.codigo}' a {'ACTIVO' if is_active else 'INACTIVO'}.", account=changed_by, user=changed_by.usuario, reference=item.codigo, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    return get_workshop_inventory_detail(db, item.id)


def list_workshop_entries(db: Session, *, search: str | None = None, item_id: int | None = None, is_active: bool | None = None) -> list[TallerEntryListItem]:
    stmt = (
        select(EntradaInventarioTaller)
        .options(joinedload(EntradaInventarioTaller.item).joinedload(InventarioTaller.tipo), joinedload(EntradaInventarioTaller.proveedor), joinedload(EntradaInventarioTaller.usuario))
        .order_by(EntradaInventarioTaller.fecha.desc(), EntradaInventarioTaller.id.desc())
    )
    if item_id is not None:
        stmt = stmt.where(EntradaInventarioTaller.item_id == item_id)
    if is_active is not None:
        stmt = stmt.where(EntradaInventarioTaller.estado.is_(is_active))
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.join(EntradaInventarioTaller.item).where(
            or_(func.upper(InventarioTaller.codigo).like(term), func.upper(InventarioTaller.nombre).like(term))
        )
    entries = db.execute(stmt).unique().scalars().all()
    return [
        TallerEntryListItem(
            id=entry.id,
            fecha=entry.fecha,
            item=_item_summary(entry.item),
            provider_name=entry.proveedor.nombre_comercial if entry.proveedor and entry.proveedor.nombre_comercial else entry.proveedor.nombre_completo if entry.proveedor else None,
            quantity=float(entry.cantidad),
            unit_measure=entry.unidad_medida,
            unit_cost=float(entry.costo_unitario),
            reason=entry.motivo,
            document_reference=entry.documento_referencia,
            is_active=entry.estado,
            registered_by=entry.usuario.nombre_completo,
        )
        for entry in entries
    ]


def get_workshop_entry_detail(db: Session, entry_id: int) -> TallerEntryDetailResponse:
    entry = _get_workshop_entry(db, entry_id)
    return TallerEntryDetailResponse(
        id=entry.id,
        fecha=entry.fecha,
        item=_item_summary(entry.item),
        provider=_provider_nested(entry.proveedor),
        quantity=float(entry.cantidad),
        unit_measure=entry.unidad_medida,
        unit_cost=float(entry.costo_unitario),
        reason=entry.motivo,
        document_reference=entry.documento_referencia,
        observations=entry.observaciones,
        is_active=entry.estado,
        registered_by=TallerUserSummary(id=entry.usuario.id, full_name=entry.usuario.nombre_completo, username=entry.usuario.cuenta.username if entry.usuario.cuenta else ""),
    )


def create_workshop_entry(db: Session, *, payload: TallerEntryCreateRequest, created_by: Cuenta, ip_address: str | None, user_agent: str | None) -> TallerEntryDetailResponse:
    item = _get_inventory(db, payload.item_id)
    if not item.estado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes registrar entradas sobre materiales inactivos.")
    if not item.tipo.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes registrar entradas sobre materiales con tipo inactivo.")
    if item.proveedor and not item.proveedor.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes registrar entradas sobre materiales con proveedor inactivo.")
    provider = _get_provider(db, payload.provider_id)
    if payload.unit_measure != item.unidad_medida:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La unidad de medida de la entrada debe coincidir con la del material base.")

    entry = EntradaInventarioTaller(
        item_id=item.id,
        usuario_id=created_by.usuario_id,
        proveedor_id=provider.id if provider else None,
        cantidad=payload.quantity,
        unidad_medida=payload.unit_measure,
        costo_unitario=payload.unit_cost,
        motivo=payload.reason,
        documento_referencia=payload.document_reference,
        observaciones=payload.observations,
        estado=True,
    )
    item.stock += Decimal(str(payload.quantity))
    item.costo_referencia = Decimal(str(payload.unit_cost))
    db.add(entry)
    db.flush()
    register_audit_event(db, action="WORKSHOP_ENTRY_CREATED", description=f"Se registró la entrada de taller '{entry.id}' para el material '{item.codigo}'.", account=created_by, user=created_by.usuario, reference=str(entry.id), ip_address=ip_address, user_agent=user_agent)
    sync_workshop_stock_notification(db, item_id=item.id)
    db.commit()
    return get_workshop_entry_detail(db, entry.id)


def set_workshop_entry_status(db: Session, *, entry_id: int, is_active: bool, changed_by: Cuenta, ip_address: str | None, user_agent: str | None) -> TallerEntryDetailResponse:
    entry = _get_workshop_entry(db, entry_id)
    if entry.estado == is_active:
        return get_workshop_entry_detail(db, entry.id)
    if is_active:
        item = _get_inventory(db, entry.item_id)
        if entry.unidad_medida != item.unidad_medida:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La unidad de medida de la entrada no coincide con la del material base.")
        entry.estado = True
        item.stock += entry.cantidad
        item.costo_referencia = entry.costo_unitario
    else:
        if entry.item.stock < entry.cantidad:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes desactivar la entrada porque el stock actual es menor al movimiento registrado.")
        entry.estado = False
        entry.item.stock -= entry.cantidad
    register_audit_event(db, action="WORKSHOP_ENTRY_STATUS_CHANGED", description=f"Se actualizó el estado de la entrada de taller '{entry.id}' a {'ACTIVA' if is_active else 'INACTIVA'}.", account=changed_by, user=changed_by.usuario, reference=str(entry.id), ip_address=ip_address, user_agent=user_agent)
    sync_workshop_stock_notification(db, item_id=entry.item_id)
    db.commit()
    return get_workshop_entry_detail(db, entry.id)


def list_workshop_outputs(db: Session, *, search: str | None = None, item_id: int | None = None, is_active: bool | None = None) -> list[TallerOutputListItem]:
    stmt = (
        select(SalidaMaterialTaller)
        .options(joinedload(SalidaMaterialTaller.item).joinedload(InventarioTaller.tipo), joinedload(SalidaMaterialTaller.usuario))
        .order_by(SalidaMaterialTaller.fecha.desc(), SalidaMaterialTaller.id.desc())
    )
    if item_id is not None:
        stmt = stmt.where(SalidaMaterialTaller.item_id == item_id)
    if is_active is not None:
        stmt = stmt.where(SalidaMaterialTaller.estado.is_(is_active))
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.join(SalidaMaterialTaller.item).where(
            or_(
                func.upper(InventarioTaller.codigo).like(term),
                func.upper(InventarioTaller.nombre).like(term),
                func.upper(SalidaMaterialTaller.destino).like(term),
            )
        )
    outputs = db.execute(stmt).unique().scalars().all()
    return [
        TallerOutputListItem(
            id=output.id,
            fecha=output.fecha,
            item=_item_summary(output.item),
            quantity=float(output.cantidad),
            unit_measure=output.unidad_medida,
            destination=output.destino,
            is_active=output.estado,
            registered_by=output.usuario.nombre_completo if output.usuario else None,
        )
        for output in outputs
    ]


def get_workshop_output_detail(db: Session, output_id: int) -> TallerOutputDetailResponse:
    output = _get_workshop_output(db, output_id)
    return TallerOutputDetailResponse(
        id=output.id,
        fecha=output.fecha,
        item=_item_summary(output.item),
        quantity=float(output.cantidad),
        unit_measure=output.unidad_medida,
        destination=output.destino,
        observations_1=output.observaciones_1,
        observations_2=output.observaciones_2,
        is_active=output.estado,
        registered_by=TallerUserSummary(id=output.usuario.id, full_name=output.usuario.nombre_completo, username=output.usuario.cuenta.username if output.usuario and output.usuario.cuenta else "") if output.usuario else None,
    )


def create_workshop_output(db: Session, *, payload: TallerOutputCreateRequest, created_by: Cuenta, ip_address: str | None, user_agent: str | None) -> TallerOutputDetailResponse:
    item = _get_inventory(db, payload.item_id)
    if not item.estado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes registrar salidas sobre materiales inactivos.")
    if not item.tipo.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes registrar salidas sobre materiales con tipo inactivo.")
    if payload.unit_measure != item.unidad_medida:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La unidad de medida de la salida debe coincidir con la del material base.")
    quantity = Decimal(str(payload.quantity))
    if item.stock < quantity:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La cantidad de salida no puede ser mayor al stock disponible.")

    output = SalidaMaterialTaller(
        item_id=item.id,
        usuario_id=created_by.usuario_id,
        cantidad=payload.quantity,
        unidad_medida=payload.unit_measure,
        destino=payload.destination,
        observaciones_1=payload.observations_1,
        observaciones_2=payload.observations_2,
        estado=True,
    )
    item.stock -= quantity
    db.add(output)
    db.flush()
    register_audit_event(db, action="WORKSHOP_OUTPUT_CREATED", description=f"Se registró la salida de taller '{output.id}' para el material '{item.codigo}'.", account=created_by, user=created_by.usuario, reference=str(output.id), ip_address=ip_address, user_agent=user_agent)
    sync_workshop_stock_notification(db, item_id=item.id)
    db.commit()
    return get_workshop_output_detail(db, output.id)


def set_workshop_output_status(db: Session, *, output_id: int, is_active: bool, changed_by: Cuenta, ip_address: str | None, user_agent: str | None) -> TallerOutputDetailResponse:
    output = _get_workshop_output(db, output_id)
    if output.estado == is_active:
        return get_workshop_output_detail(db, output.id)
    if is_active:
        item = _get_inventory(db, output.item_id)
        if output.unidad_medida != item.unidad_medida:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La unidad de medida de la salida no coincide con la del material base.")
        if item.stock < output.cantidad:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes reactivar la salida porque el stock actual es insuficiente.")
        output.estado = True
        item.stock -= output.cantidad
    else:
        output.estado = False
        output.item.stock += output.cantidad
    register_audit_event(db, action="WORKSHOP_OUTPUT_STATUS_CHANGED", description=f"Se actualizó el estado de la salida de taller '{output.id}' a {'ACTIVA' if is_active else 'INACTIVA'}.", account=changed_by, user=changed_by.usuario, reference=str(output.id), ip_address=ip_address, user_agent=user_agent)
    sync_workshop_stock_notification(db, item_id=output.item_id)
    db.commit()
    return get_workshop_output_detail(db, output.id)
