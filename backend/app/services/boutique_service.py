from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.audit import register_audit_event
from app.models.account import Cuenta
from app.models.boutique_details import DetalleBouquetBoutique, DetalleBrassierBoutique, DetalleVeloBoutique, DetalleVestidoBoutique
from app.models.boutique_item import ItemBoutique
from app.models.boutique_sale import VentaBoutique
from app.models.boutique_type import TipoItemBoutique
from app.models.provider import Proveedor
from app.schemas.boutique import (
    BoutiqueItemCreateRequest,
    BoutiqueItemDetailResponse,
    BoutiqueItemListItem,
    BoutiqueItemUpdateRequest,
    ProveedorNested,
    TipoItemBoutiqueNested,
)


SEED_BOUTIQUE_TYPES = ("VESTIDO", "VELO", "BOUQUET", "BRASIER", "OTRO")


def _detail_kind_from_type_name(type_name: str) -> str:
    normalized = (type_name or "").strip().upper()
    if normalized == "VESTIDO":
        return "VESTIDO"
    if normalized == "VELO":
        return "VELO"
    if normalized == "BOUQUET":
        return "BOUQUET"
    if normalized == "BRASIER":
        return "BRASIER"
    return "OTRO"


def _to_float(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _to_provider_nested(provider: Proveedor | None) -> ProveedorNested | None:
    if provider is None:
        return None
    return ProveedorNested(
        id=provider.id,
        full_name=provider.nombre_completo,
        nombre_comercial=provider.nombre_comercial,
    )


def _serialize_detail(item: ItemBoutique, detail_kind: str) -> dict | None:
    if detail_kind == "VESTIDO" and item.detalle_vestido:
        detail = item.detalle_vestido
        return {
            "dress_type": detail.tipo_vestido.value,
            "skirt_cut": detail.corte_falda,
            "neckline_type": detail.tipo_escote,
            "has_train": detail.tiene_cola,
            "has_sleeves": detail.tiene_manga,
            "has_stoning": detail.tiene_pedreria,
            "cup_size": detail.copa_talla.value if detail.copa_talla else None,
            "dress_size": detail.talla.value,
            "skirt_length": _to_float(detail.largo_falda),
            "notes": detail.observaciones,
        }
    if detail_kind == "VELO" and item.detalle_velo:
        detail = item.detalle_velo
        return {
            "veil_type": detail.tipo_velo,
            "layers": detail.capas,
            "edge": detail.borde,
            "decoration": detail.decoracion,
            "notes": detail.observaciones,
        }
    if detail_kind == "BOUQUET" and item.detalle_bouquet:
        detail = item.detalle_bouquet
        return {
            "bouquet_type": detail.tipo_bouquet,
            "shape": detail.forma,
            "flower_type": detail.tipo_flor,
            "decoration": detail.decoracion,
            "notes": detail.observaciones,
        }
    if detail_kind == "BRASIER" and item.detalle_brassier:
        detail = item.detalle_brassier
        return {
            "cup_size": detail.copa_talla.value,
            "has_lace": detail.tiene_encaje,
            "brand": detail.marca,
            "notes": detail.observaciones,
        }
    return None


def _to_item_detail_response(item: ItemBoutique) -> BoutiqueItemDetailResponse:
    detail_kind = _detail_kind_from_type_name(item.tipo_item.nombre)
    return BoutiqueItemDetailResponse(
        id=item.id,
        type=TipoItemBoutiqueNested(id=item.tipo_item.id, nombre=item.tipo_item.nombre),
        provider=_to_provider_nested(item.proveedor_rel),
        code=item.codigo,
        name=item.nombre,
        color_primary=item.color_primario,
        color_secondary=item.color_secundario,
        material=item.material,
        length=_to_float(item.largo),
        width=_to_float(item.ancho),
        detail_text=item.detalle,
        purchase_price=float(item.precio_compra),
        sale_price=float(item.precio_venta),
        stock=item.stock,
        stock_min=item.stock_minimo,
        is_low_stock=item.stock <= item.stock_minimo,
        is_active=item.estado,
        created_at=item.fecha_registro,
        detail_kind=detail_kind,
        detail=_serialize_detail(item, detail_kind),
    )


def _ensure_unique_type_name(db: Session, nombre: str, *, exclude_id: int | None = None) -> None:
    stmt = select(TipoItemBoutique).where(func.upper(TipoItemBoutique.nombre) == nombre.strip().upper())
    if exclude_id is not None:
        stmt = stmt.where(TipoItemBoutique.id != exclude_id)
    if db.execute(stmt).scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un tipo boutique con ese nombre.")


def _ensure_unique_item_code(db: Session, codigo: str, *, exclude_id: int | None = None) -> None:
    stmt = select(ItemBoutique).where(func.upper(ItemBoutique.codigo) == codigo.strip().upper())
    if exclude_id is not None:
        stmt = stmt.where(ItemBoutique.id != exclude_id)
    if db.execute(stmt).scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un item boutique con ese código.")


def _get_type_entity(db: Session, type_id: int) -> TipoItemBoutique:
    boutique_type = db.execute(select(TipoItemBoutique).where(TipoItemBoutique.id == type_id)).scalar_one_or_none()
    if boutique_type is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo boutique no encontrado.")
    return boutique_type


def _get_provider_entity(db: Session, provider_id: int) -> Proveedor:
    provider = db.execute(select(Proveedor).where(Proveedor.id == provider_id)).scalar_one_or_none()
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado.")
    return provider


def _get_item_entity(db: Session, item_id: int) -> ItemBoutique:
    item = db.execute(
        select(ItemBoutique)
        .options(
            joinedload(ItemBoutique.tipo_item),
            joinedload(ItemBoutique.proveedor_rel),
            joinedload(ItemBoutique.detalle_vestido),
            joinedload(ItemBoutique.detalle_velo),
            joinedload(ItemBoutique.detalle_bouquet),
            joinedload(ItemBoutique.detalle_brassier),
        )
        .where(ItemBoutique.id == item_id)
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto boutique no encontrado.")
    return item


def _ensure_provider_available(db: Session, provider_id: int | None) -> Proveedor | None:
    if provider_id is None:
        return None
    provider = _get_provider_entity(db, provider_id)
    if not provider.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El proveedor está deshabilitado.")
    return provider


def _ensure_type_enabled(boutique_type: TipoItemBoutique) -> None:
    if not boutique_type.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El tipo boutique está deshabilitado.")


def seed_boutique_types(db: Session) -> None:
    existing = {row.nombre for row in db.execute(select(TipoItemBoutique)).scalars().all()}
    for type_name in SEED_BOUTIQUE_TYPES:
        if type_name in existing:
            continue
        db.add(TipoItemBoutique(nombre=type_name, descripcion=f"TIPO BASE {type_name}", habilitado=True))
    db.commit()


def list_boutique_types(db: Session) -> list[TipoItemBoutique]:
    return db.execute(select(TipoItemBoutique).order_by(TipoItemBoutique.nombre.asc())).scalars().all()


def get_boutique_type(db: Session, type_id: int) -> TipoItemBoutique:
    return _get_type_entity(db, type_id)


def create_boutique_type(
    db: Session,
    *,
    payload,
    created_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> TipoItemBoutique:
    _ensure_unique_type_name(db, payload.nombre)
    boutique_type = TipoItemBoutique(nombre=payload.nombre, descripcion=payload.descripcion, habilitado=True)
    db.add(boutique_type)
    db.flush()
    register_audit_event(
        db,
        action="BOUTIQUE_TYPE_CREATED",
        description=f"Se creó el tipo boutique '{boutique_type.nombre}'.",
        account=created_by,
        user=created_by.usuario,
        reference=str(boutique_type.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(boutique_type)
    return boutique_type


def update_boutique_type(
    db: Session,
    *,
    type_id: int,
    payload,
    updated_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> TipoItemBoutique:
    boutique_type = _get_type_entity(db, type_id)
    _ensure_unique_type_name(db, payload.nombre, exclude_id=boutique_type.id)
    boutique_type.nombre = payload.nombre
    boutique_type.descripcion = payload.descripcion
    register_audit_event(
        db,
        action="BOUTIQUE_TYPE_UPDATED",
        description=f"Se actualizó el tipo boutique '{boutique_type.nombre}'.",
        account=updated_by,
        user=updated_by.usuario,
        reference=str(boutique_type.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(boutique_type)
    return boutique_type


def set_boutique_type_status(
    db: Session,
    *,
    type_id: int,
    enabled: bool,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> TipoItemBoutique:
    boutique_type = _get_type_entity(db, type_id)
    if not enabled:
        active_items = db.execute(
            select(ItemBoutique.id).where(
                ItemBoutique.tipo_item_id == boutique_type.id,
                ItemBoutique.estado.is_(True),
            )
        ).first()
        if active_items is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No puedes deshabilitar un tipo con items activos asociados.",
            )
    boutique_type.habilitado = enabled
    register_audit_event(
        db,
        action="BOUTIQUE_TYPE_STATUS_CHANGED",
        description=f"Se actualizó el estado del tipo boutique '{boutique_type.nombre}' a {'ACTIVO' if enabled else 'INACTIVO'}.",
        account=changed_by,
        user=changed_by.usuario,
        reference=str(boutique_type.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(boutique_type)
    return boutique_type


def _validate_item_detail(detail_kind: str, detail_payload: dict | None) -> None:
    if detail_kind == "VESTIDO" and detail_payload:
        if not detail_payload.get("dress_type") or not detail_payload.get("dress_size"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El detalle del vestido requiere tipo de vestido y talla.")
    if detail_kind == "VELO" and detail_payload:
        if not detail_payload.get("veil_type"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El detalle del velo requiere tipo de velo.")
    if detail_kind == "BOUQUET" and detail_payload is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El detalle del bouquet es obligatorio.")
    if detail_kind == "BRASIER" and detail_payload:
        if not detail_payload.get("cup_size"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El detalle del brassier requiere la copa/talla.")


def _sync_detail(item: ItemBoutique, detail_kind: str, detail_payload: dict | None) -> None:
    item.detalle_vestido = None
    item.detalle_velo = None
    item.detalle_bouquet = None
    item.detalle_brassier = None
    if detail_kind == "OTRO":
        return
    if detail_payload is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Debe enviar el detalle especializado.")
    if detail_kind == "VESTIDO":
        item.detalle_vestido = DetalleVestidoBoutique(
            tipo_vestido=detail_payload["dress_type"],
            corte_falda=detail_payload.get("skirt_cut"),
            tipo_escote=detail_payload.get("neckline_type"),
            tiene_cola=detail_payload.get("has_train", False),
            tiene_manga=detail_payload.get("has_sleeves", False),
            tiene_pedreria=detail_payload.get("has_stoning", False),
            copa_talla=detail_payload.get("cup_size"),
            talla=detail_payload["dress_size"],
            largo_falda=detail_payload.get("skirt_length"),
            observaciones=detail_payload.get("notes"),
        )
    elif detail_kind == "VELO":
        item.detalle_velo = DetalleVeloBoutique(
            tipo_velo=detail_payload["veil_type"],
            capas=detail_payload.get("layers"),
            borde=detail_payload.get("edge"),
            decoracion=detail_payload.get("decoration"),
            observaciones=detail_payload.get("notes"),
        )
    elif detail_kind == "BOUQUET":
        item.detalle_bouquet = DetalleBouquetBoutique(
            tipo_bouquet=detail_payload.get("bouquet_type"),
            forma=detail_payload.get("shape"),
            tipo_flor=detail_payload.get("flower_type"),
            decoracion=detail_payload.get("decoration"),
            observaciones=detail_payload.get("notes"),
        )
    elif detail_kind == "BRASIER":
        item.detalle_brassier = DetalleBrassierBoutique(
            copa_talla=detail_payload["cup_size"],
            tiene_encaje=detail_payload.get("has_lace", True),
            marca=detail_payload.get("brand"),
            observaciones=detail_payload.get("notes"),
        )


def list_boutique_items(
    db: Session,
    *,
    type_id: int | None = None,
    search: str | None = None,
    is_active: bool | None = None,
    low_stock: bool | None = None,
) -> list[BoutiqueItemListItem]:
    stmt = (
        select(ItemBoutique)
        .options(joinedload(ItemBoutique.tipo_item), joinedload(ItemBoutique.proveedor_rel))
        .order_by(ItemBoutique.id.desc())
    )
    if type_id is not None:
        stmt = stmt.where(ItemBoutique.tipo_item_id == type_id)
    if is_active is not None:
        stmt = stmt.where(ItemBoutique.estado.is_(is_active))
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.where(
            or_(
                func.upper(ItemBoutique.codigo).like(term),
                func.upper(ItemBoutique.nombre).like(term),
                func.upper(ItemBoutique.color_primario).like(term),
                func.upper(func.coalesce(ItemBoutique.color_secundario, "")).like(term),
            )
        )
    if low_stock:
        stmt = stmt.where(ItemBoutique.stock <= ItemBoutique.stock_minimo)

    items = db.execute(stmt).scalars().all()
    return [
        BoutiqueItemListItem(
            id=item.id,
            type_id=item.tipo_item.id,
            type_name=item.tipo_item.nombre,
            code=item.codigo,
            name=item.nombre,
            color_primary=item.color_primario,
            color_secondary=item.color_secundario,
            material=item.material,
            provider_name=item.proveedor_rel.nombre_completo if item.proveedor_rel else None,
            sale_price=float(item.precio_venta),
            stock=item.stock,
            stock_min=item.stock_minimo,
            is_low_stock=item.stock <= item.stock_minimo,
            is_active=item.estado,
            detail_kind=_detail_kind_from_type_name(item.tipo_item.nombre),
            created_at=item.fecha_registro,
        )
        for item in items
    ]


def get_boutique_item_detail(db: Session, item_id: int) -> BoutiqueItemDetailResponse:
    return _to_item_detail_response(_get_item_entity(db, item_id))


def create_boutique_item(
    db: Session,
    *,
    payload: BoutiqueItemCreateRequest,
    created_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> BoutiqueItemDetailResponse:
    boutique_type = _get_type_entity(db, payload.type_id)
    _ensure_type_enabled(boutique_type)
    detail_kind = _detail_kind_from_type_name(boutique_type.nombre)
    if payload.detail_kind != detail_kind:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El detalle no corresponde con el tipo seleccionado.")
    _ensure_provider_available(db, payload.item.provider_id)
    _ensure_unique_item_code(db, payload.item.code)
    _validate_item_detail(detail_kind, payload.detail)

    item = ItemBoutique(
        tipo_item_id=boutique_type.id,
        proveedor_id=payload.item.provider_id,
        codigo=payload.item.code,
        nombre=payload.item.name,
        color_primario=payload.item.color_primary,
        color_secundario=payload.item.color_secondary,
        material=payload.item.material,
        largo=payload.item.length,
        ancho=payload.item.width,
        precio_compra=payload.item.purchase_price,
        precio_venta=payload.item.sale_price,
        stock=payload.item.stock,
        stock_minimo=payload.item.stock_min,
        detalle=payload.item.detail,
        estado=True,
    )
    _sync_detail(item, detail_kind, payload.detail)
    db.add(item)
    db.flush()
    register_audit_event(
        db,
        action="BOUTIQUE_ITEM_CREATED",
        description=f"Se creó el item boutique '{item.codigo}'.",
        account=created_by,
        user=created_by.usuario,
        reference=item.codigo,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_boutique_item_detail(db, item.id)


def update_boutique_item(
    db: Session,
    *,
    item_id: int,
    payload: BoutiqueItemUpdateRequest,
    updated_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> BoutiqueItemDetailResponse:
    item = _get_item_entity(db, item_id)
    _ensure_provider_available(db, payload.item.provider_id)
    _ensure_unique_item_code(db, payload.item.code, exclude_id=item.id)
    detail_kind = _detail_kind_from_type_name(item.tipo_item.nombre)
    _validate_item_detail(detail_kind, payload.detail)

    has_sales = db.execute(select(exists().where(VentaBoutique.item_id == item.id))).scalar()
    if has_sales and item.stock != payload.item.stock:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El stock no puede editarse manualmente porque el producto ya tiene ventas registradas.",
        )

    item.proveedor_id = payload.item.provider_id
    item.codigo = payload.item.code
    item.nombre = payload.item.name
    item.color_primario = payload.item.color_primary
    item.color_secundario = payload.item.color_secondary
    item.material = payload.item.material
    item.largo = payload.item.length
    item.ancho = payload.item.width
    item.precio_compra = payload.item.purchase_price
    item.precio_venta = payload.item.sale_price
    item.stock = payload.item.stock
    item.stock_minimo = payload.item.stock_min
    item.detalle = payload.item.detail
    _sync_detail(item, detail_kind, payload.detail)
    register_audit_event(
        db,
        action="BOUTIQUE_ITEM_UPDATED",
        description=f"Se actualizó el item boutique '{item.codigo}'.",
        account=updated_by,
        user=updated_by.usuario,
        reference=item.codigo,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_boutique_item_detail(db, item.id)


def set_boutique_item_status(
    db: Session,
    *,
    item_id: int,
    is_active: bool,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> BoutiqueItemDetailResponse:
    item = _get_item_entity(db, item_id)
    if is_active and not item.tipo_item.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes activar un item cuyo tipo está deshabilitado.")
    if is_active and item.proveedor_rel and not item.proveedor_rel.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes activar un item con proveedor deshabilitado.")
    item.estado = is_active
    register_audit_event(
        db,
        action="BOUTIQUE_ITEM_STATUS_CHANGED",
        description=f"Se actualizó el estado del item boutique '{item.codigo}' a {'ACTIVO' if is_active else 'INACTIVO'}.",
        account=changed_by,
        user=changed_by.usuario,
        reference=item.codigo,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_boutique_item_detail(db, item.id)
