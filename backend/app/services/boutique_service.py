from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.audit import register_audit_event
from app.models.account import Cuenta
from app.models.boutique_details import DetalleBouquetBoutique, DetalleVeloBoutique, DetalleVestidoBoutique
from app.models.boutique_item import ItemBoutique
from app.models.boutique_type import TipoItemBoutique
from app.schemas.boutique import (
    BoutiqueItemCreateRequest,
    BoutiqueItemDetailResponse,
    BoutiqueItemListItem,
    BoutiqueItemUpdateRequest,
    DetalleBouquetBoutiquePayload,
    DetalleVeloBoutiquePayload,
    DetalleVestidoBoutiquePayload,
    TipoItemBoutiqueCreate,
    TipoItemBoutiqueNested,
    TipoItemBoutiqueUpdate,
)


SPECIALIZED_KIND_NAMES = {"VESTIDO", "VELO", "BOUQUET"}


def build_boutique_permissions(role_code: str) -> list[str]:
    if role_code in {"ADMIN", "INV_BOUTIQUE"}:
        return [
            "boutique_types:list",
            "boutique_types:create",
            "boutique_types:update",
            "boutique_types:update_status",
            "boutique_items:list",
            "boutique_items:view",
            "boutique_items:create",
            "boutique_items:update",
            "boutique_items:update_status",
        ]
    if role_code == "CAJA":
        return [
            "boutique_types:list",
            "boutique_items:list",
            "boutique_items:view",
        ]
    return []


def _normalize_name(value: str) -> str:
    return value.strip().upper()


def _to_float(value: Decimal | float | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _specialized_kind_for_type(tipo: TipoItemBoutique) -> str:
    normalized_name = _normalize_name(tipo.nombre)
    if normalized_name in SPECIALIZED_KIND_NAMES:
        return normalized_name
    return "OTRO"


def _detail_kind_for_item(item: ItemBoutique) -> str:
    if item.detalle_vestido is not None:
        return "VESTIDO"
    if item.detalle_velo is not None:
        return "VELO"
    if item.detalle_bouquet is not None:
        return "BOUQUET"
    return "OTRO"


def _serialize_detail(item: ItemBoutique) -> dict[str, Any] | None:
    if item.detalle_vestido is not None:
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
    if item.detalle_velo is not None:
        detail = item.detalle_velo
        return {
            "veil_type": detail.tipo_velo,
            "length": _to_float(detail.largo),
            "size": detail.tamano.value,
            "layers": detail.capas,
            "edge": detail.borde,
            "decoration": detail.decoracion,
            "notes": detail.observaciones,
        }
    if item.detalle_bouquet is not None:
        detail = item.detalle_bouquet
        return {
            "bouquet_type": detail.tipo_bouquet,
            "size": detail.tamano.value,
            "flower_type": detail.tipo_flor,
            "decoration": detail.decoracion,
            "notes": detail.observaciones,
        }
    return None


def _item_to_detail_response(item: ItemBoutique) -> BoutiqueItemDetailResponse:
    return BoutiqueItemDetailResponse(
        id=item.id,
        type=TipoItemBoutiqueNested(id=item.tipo_item.id, nombre=item.tipo_item.nombre),
        code=item.codigo,
        name=item.nombre,
        color=item.color,
        shape=item.forma,
        material=item.material,
        measurements=item.medidas,
        supplier=item.proveedor,
        description=item.descripcion,
        notes=item.observaciones,
        purchase_price=_to_float(item.precio_compra) or 0,
        sale_price=_to_float(item.precio_venta) or 0,
        stock=_to_float(item.stock) or 0,
        stock_min=_to_float(item.stock_minimo) or 0,
        is_low_stock=Decimal(item.stock) <= Decimal(item.stock_minimo),
        is_active=item.estado,
        created_at=item.fecha_registro,
        detail_kind=_detail_kind_for_item(item),
        detail=_serialize_detail(item),
    )


def _item_to_list_item(item: ItemBoutique) -> BoutiqueItemListItem:
    stock = _to_float(item.stock) or 0
    stock_min = _to_float(item.stock_minimo) or 0
    return BoutiqueItemListItem(
        id=item.id,
        type_id=item.tipo_item.id,
        type_name=item.tipo_item.nombre,
        code=item.codigo,
        name=item.nombre,
        color=item.color,
        material=item.material,
        sale_price=_to_float(item.precio_venta) or 0,
        stock=stock,
        stock_min=stock_min,
        is_low_stock=stock <= stock_min,
        is_active=item.estado,
        detail_kind=_detail_kind_for_item(item),
        created_at=item.fecha_registro,
    )


def seed_boutique_types(db: Session) -> None:
    initial_types = (
        ("VESTIDO", "ARTICULOS DE VESTIDO PARA BOUTIQUE"),
        ("VELO", "ARTICULOS DE VELO PARA BOUTIQUE"),
        ("BOUQUET", "ARTICULOS DE BOUQUET PARA BOUTIQUE"),
        ("OTRO", "OTROS ARTICULOS DE BOUTIQUE"),
    )
    existing = {_normalize_name(tipo.nombre) for tipo in db.execute(select(TipoItemBoutique)).scalars().all()}
    for nombre, descripcion in initial_types:
        if nombre in existing:
            continue
        db.add(TipoItemBoutique(nombre=nombre, descripcion=descripcion, habilitado=True))
    db.commit()


def list_boutique_types(db: Session) -> list[TipoItemBoutique]:
    stmt = select(TipoItemBoutique).order_by(TipoItemBoutique.nombre.asc())
    return list(db.execute(stmt).scalars().all())


def get_boutique_type(db: Session, type_id: int) -> TipoItemBoutique:
    tipo = db.execute(select(TipoItemBoutique).where(TipoItemBoutique.id == type_id)).scalar_one_or_none()
    if tipo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo boutique no encontrado.")
    return tipo


def _ensure_unique_type_name(db: Session, nombre: str, *, exclude_id: int | None = None) -> None:
    normalized_name = _normalize_name(nombre)
    stmt = select(TipoItemBoutique).where(func.upper(TipoItemBoutique.nombre) == normalized_name)
    if exclude_id is not None:
        stmt = stmt.where(TipoItemBoutique.id != exclude_id)
    duplicate = db.execute(stmt).scalar_one_or_none()
    if duplicate is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un tipo boutique con ese nombre.")


def create_boutique_type(
    db: Session,
    *,
    payload: TipoItemBoutiqueCreate,
    created_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> TipoItemBoutique:
    _ensure_unique_type_name(db, payload.nombre)
    tipo = TipoItemBoutique(nombre=payload.nombre, descripcion=payload.descripcion, habilitado=True)
    db.add(tipo)
    db.flush()
    register_audit_event(
        db,
        action="BOUTIQUE_TYPE_CREATED",
        description=f"Se creo el tipo boutique '{tipo.nombre}'.",
        account=created_by,
        user=created_by.usuario,
        reference=str(tipo.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_boutique_type(db, tipo.id)


def update_boutique_type(
    db: Session,
    *,
    type_id: int,
    payload: TipoItemBoutiqueUpdate,
    updated_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> TipoItemBoutique:
    tipo = get_boutique_type(db, type_id)
    _ensure_unique_type_name(db, payload.nombre, exclude_id=tipo.id)

    previous_name = tipo.nombre
    tipo.nombre = payload.nombre
    tipo.descripcion = payload.descripcion
    register_audit_event(
        db,
        action="BOUTIQUE_TYPE_UPDATED",
        description=f"Se actualizo el tipo boutique '{previous_name}' a '{tipo.nombre}'.",
        account=updated_by,
        user=updated_by.usuario,
        reference=str(tipo.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_boutique_type(db, tipo.id)


def set_boutique_type_status(
    db: Session,
    *,
    type_id: int,
    enabled: bool,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> TipoItemBoutique:
    tipo = get_boutique_type(db, type_id)
    if not enabled:
        active_items = db.execute(
            select(ItemBoutique.id).where(ItemBoutique.tipo_item_id == tipo.id, ItemBoutique.estado.is_(True)).limit(1)
        ).scalar_one_or_none()
        if active_items is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No puedes desactivar un tipo con items activos asociados.",
            )

    tipo.habilitado = enabled
    register_audit_event(
        db,
        action="BOUTIQUE_TYPE_STATUS_CHANGED",
        description=f"Se actualizo el estado del tipo boutique '{tipo.nombre}' a {'ACTIVO' if enabled else 'INACTIVO'}.",
        account=changed_by,
        user=changed_by.usuario,
        reference=str(tipo.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_boutique_type(db, tipo.id)


def _base_item_query():
    return select(ItemBoutique).options(
        joinedload(ItemBoutique.tipo_item),
        joinedload(ItemBoutique.detalle_vestido),
        joinedload(ItemBoutique.detalle_velo),
        joinedload(ItemBoutique.detalle_bouquet),
    )


def get_boutique_item(db: Session, item_id: int) -> ItemBoutique:
    item = db.execute(_base_item_query().where(ItemBoutique.id == item_id)).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item boutique no encontrado.")
    return item


def get_boutique_item_detail(db: Session, item_id: int) -> BoutiqueItemDetailResponse:
    return _item_to_detail_response(get_boutique_item(db, item_id))


def list_boutique_items(
    db: Session,
    *,
    type_id: int | None = None,
    search: str | None = None,
    is_active: bool | None = None,
    low_stock: bool | None = None,
) -> list[BoutiqueItemListItem]:
    stmt = _base_item_query().order_by(ItemBoutique.id.desc())
    if type_id is not None:
        stmt = stmt.where(ItemBoutique.tipo_item_id == type_id)
    if is_active is not None:
        stmt = stmt.where(ItemBoutique.estado.is_(is_active))
    if search:
        normalized = f"%{search.strip().upper()}%"
        stmt = stmt.where(
            or_(
                func.upper(ItemBoutique.codigo).like(normalized),
                func.upper(ItemBoutique.nombre).like(normalized),
                func.upper(ItemBoutique.color).like(normalized),
            )
        )

    items = list(db.execute(stmt).scalars().unique().all())
    if low_stock:
        items = [item for item in items if Decimal(item.stock) <= Decimal(item.stock_minimo)]
    return [_item_to_list_item(item) for item in items]


def _validate_type_for_item(db: Session, type_id: int) -> TipoItemBoutique:
    tipo = get_boutique_type(db, type_id)
    if not tipo.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El tipo boutique esta deshabilitado.")
    return tipo


def _ensure_unique_item_code(db: Session, code: str, *, exclude_id: int | None = None) -> None:
    normalized_code = code.strip().upper()
    stmt = select(ItemBoutique).where(func.upper(ItemBoutique.codigo) == normalized_code)
    if exclude_id is not None:
        stmt = stmt.where(ItemBoutique.id != exclude_id)
    duplicate = db.execute(stmt).scalar_one_or_none()
    if duplicate is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un item boutique con ese codigo.")


def _build_vestido_detail(item_id: int, payload: dict[str, Any]) -> DetalleVestidoBoutique:
    detail = DetalleVestidoBoutiquePayload.model_validate(payload)
    return DetalleVestidoBoutique(
        item_id=item_id,
        tipo_vestido=detail.dress_type,
        corte_falda=detail.skirt_cut,
        tipo_escote=detail.neckline_type,
        tiene_cola=detail.has_train,
        tiene_manga=detail.has_sleeves,
        tiene_pedreria=detail.has_stoning,
        copa_talla=detail.cup_size,
        talla=detail.dress_size,
        largo_falda=detail.skirt_length,
        observaciones=detail.notes,
    )


def _build_velo_detail(item_id: int, payload: dict[str, Any]) -> DetalleVeloBoutique:
    detail = DetalleVeloBoutiquePayload.model_validate(payload)
    return DetalleVeloBoutique(
        item_id=item_id,
        tipo_velo=detail.veil_type,
        largo=detail.length,
        tamano=detail.size,
        capas=detail.layers,
        borde=detail.edge,
        decoracion=detail.decoration,
        observaciones=detail.notes,
    )


def _build_bouquet_detail(item_id: int, payload: dict[str, Any]) -> DetalleBouquetBoutique:
    detail = DetalleBouquetBoutiquePayload.model_validate(payload)
    return DetalleBouquetBoutique(
        item_id=item_id,
        tipo_bouquet=detail.bouquet_type,
        tamano=detail.size,
        tipo_flor=detail.flower_type,
        decoracion=detail.decoration,
        observaciones=detail.notes,
    )


def _apply_item_payload(item: ItemBoutique, payload) -> None:
    item.codigo = payload.code
    item.nombre = payload.name
    item.color = payload.color
    item.forma = payload.shape
    item.material = payload.material
    item.medidas = payload.measurements
    item.proveedor = payload.supplier
    item.descripcion = payload.description
    item.precio_compra = payload.purchase_price
    item.precio_venta = payload.sale_price
    item.stock = payload.stock
    item.stock_minimo = payload.stock_min
    item.observaciones = payload.notes


def _attach_specialized_detail(db: Session, item: ItemBoutique, detail_kind: str, payload: dict[str, Any] | None) -> None:
    if detail_kind == "OTRO":
        if payload is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El item tipo OTRO no admite detalle especializado.")
        return
    if payload is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Debes enviar el detalle especializado.")

    if detail_kind == "VESTIDO":
        db.add(_build_vestido_detail(item.id, payload))
        return
    if detail_kind == "VELO":
        db.add(_build_velo_detail(item.id, payload))
        return
    if detail_kind == "BOUQUET":
        db.add(_build_bouquet_detail(item.id, payload))
        return
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de detalle boutique no soportado.")


def _ensure_detail_matches_type(tipo: TipoItemBoutique, detail_kind: str) -> str:
    expected_kind = _specialized_kind_for_type(tipo)
    if expected_kind != detail_kind:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El tipo boutique '{tipo.nombre}' requiere detalle '{expected_kind}'.",
        )
    return expected_kind


def create_boutique_item(
    db: Session,
    *,
    payload: BoutiqueItemCreateRequest,
    created_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> BoutiqueItemDetailResponse:
    tipo = _validate_type_for_item(db, payload.type_id)
    detail_kind = _ensure_detail_matches_type(tipo, payload.detail_kind)
    _ensure_unique_item_code(db, payload.item.code)

    item = ItemBoutique(tipo_item_id=tipo.id, estado=True)
    _apply_item_payload(item, payload.item)
    db.add(item)
    db.flush()

    _attach_specialized_detail(db, item, detail_kind, payload.detail)
    db.flush()

    register_audit_event(
        db,
        action="BOUTIQUE_ITEM_CREATED",
        description=f"Se creo el item boutique '{item.codigo}'.",
        account=created_by,
        user=created_by.usuario,
        reference=str(item.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return _item_to_detail_response(get_boutique_item(db, item.id))


def update_boutique_item(
    db: Session,
    *,
    item_id: int,
    payload: BoutiqueItemUpdateRequest,
    updated_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> BoutiqueItemDetailResponse:
    item = get_boutique_item(db, item_id)
    if not item.tipo_item.habilitado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El tipo boutique del item esta deshabilitado.")

    _ensure_unique_item_code(db, payload.item.code, exclude_id=item.id)
    _apply_item_payload(item, payload.item)

    detail_kind = _specialized_kind_for_type(item.tipo_item)
    if detail_kind == "VESTIDO":
        if payload.detail is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El item requiere detalle de vestido.")
        if item.detalle_vestido is None:
            db.add(_build_vestido_detail(item.id, payload.detail))
        else:
            detail = DetalleVestidoBoutiquePayload.model_validate(payload.detail)
            item.detalle_vestido.tipo_vestido = detail.dress_type
            item.detalle_vestido.corte_falda = detail.skirt_cut
            item.detalle_vestido.tipo_escote = detail.neckline_type
            item.detalle_vestido.tiene_cola = detail.has_train
            item.detalle_vestido.tiene_manga = detail.has_sleeves
            item.detalle_vestido.tiene_pedreria = detail.has_stoning
            item.detalle_vestido.copa_talla = detail.cup_size
            item.detalle_vestido.talla = detail.dress_size
            item.detalle_vestido.largo_falda = detail.skirt_length
            item.detalle_vestido.observaciones = detail.notes
    elif detail_kind == "VELO":
        if payload.detail is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El item requiere detalle de velo.")
        if item.detalle_velo is None:
            db.add(_build_velo_detail(item.id, payload.detail))
        else:
            detail = DetalleVeloBoutiquePayload.model_validate(payload.detail)
            item.detalle_velo.tipo_velo = detail.veil_type
            item.detalle_velo.largo = detail.length
            item.detalle_velo.tamano = detail.size
            item.detalle_velo.capas = detail.layers
            item.detalle_velo.borde = detail.edge
            item.detalle_velo.decoracion = detail.decoration
            item.detalle_velo.observaciones = detail.notes
    elif detail_kind == "BOUQUET":
        if payload.detail is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El item requiere detalle de bouquet.")
        if item.detalle_bouquet is None:
            db.add(_build_bouquet_detail(item.id, payload.detail))
        else:
            detail = DetalleBouquetBoutiquePayload.model_validate(payload.detail)
            item.detalle_bouquet.tipo_bouquet = detail.bouquet_type
            item.detalle_bouquet.tamano = detail.size
            item.detalle_bouquet.tipo_flor = detail.flower_type
            item.detalle_bouquet.decoracion = detail.decoration
            item.detalle_bouquet.observaciones = detail.notes
    elif payload.detail is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El item tipo OTRO no admite detalle especializado.")

    register_audit_event(
        db,
        action="BOUTIQUE_ITEM_UPDATED",
        description=f"Se actualizo el item boutique '{item.codigo}'.",
        account=updated_by,
        user=updated_by.usuario,
        reference=str(item.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return _item_to_detail_response(get_boutique_item(db, item.id))


def set_boutique_item_status(
    db: Session,
    *,
    item_id: int,
    is_active: bool,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> BoutiqueItemDetailResponse:
    item = get_boutique_item(db, item_id)
    if is_active and not item.tipo_item.habilitado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No puedes activar un item cuyo tipo boutique esta deshabilitado.",
        )
    item.estado = is_active
    register_audit_event(
        db,
        action="BOUTIQUE_ITEM_STATUS_CHANGED",
        description=f"Se actualizo el estado del item boutique '{item.codigo}' a {'ACTIVO' if is_active else 'INACTIVO'}.",
        account=changed_by,
        user=changed_by.usuario,
        reference=str(item.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return _item_to_detail_response(get_boutique_item(db, item.id))
