from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.audit import register_audit_event
from app.models.account import Cuenta
from app.models.boutique_item import ItemBoutique
from app.models.provider import Proveedor
from app.schemas.boutique import ProveedorCreateRequest, ProveedorDetailResponse, ProveedorListItem, ProveedorUpdateRequest


def _to_list_item(provider: Proveedor) -> ProveedorListItem:
    return ProveedorListItem(
        id=provider.id,
        full_name=provider.nombre_completo,
        nombre_comercial=provider.nombre_comercial,
        celular=provider.celular,
        correo=provider.correo,
        ciudad=provider.ciudad,
        is_active=provider.habilitado,
        created_at=provider.fecha_registro,
    )


def _to_detail(provider: Proveedor) -> ProveedorDetailResponse:
    return ProveedorDetailResponse(
        id=provider.id,
        nombres=provider.nombres,
        apellido_paterno=provider.apellido_paterno,
        apellido_materno=provider.apellido_materno,
        full_name=provider.nombre_completo,
        nombre_comercial=provider.nombre_comercial,
        celular=provider.celular,
        celular_secundario=provider.celular_secundario,
        correo=provider.correo,
        pais=provider.pais,
        ciudad=provider.ciudad,
        direccion=provider.direccion,
        observaciones=provider.observaciones,
        is_active=provider.habilitado,
        created_at=provider.fecha_registro,
    )


def _get_provider_entity(db: Session, provider_id: int) -> Proveedor:
    provider = db.execute(select(Proveedor).where(Proveedor.id == provider_id)).scalar_one_or_none()
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado.")
    return provider


def _ensure_unique_phone(db: Session, celular: str | None, *, exclude_id: int | None = None) -> None:
    if not celular:
        return
    stmt = select(Proveedor).where(Proveedor.celular == celular.strip())
    if exclude_id is not None:
        stmt = stmt.where(Proveedor.id != exclude_id)
    if db.execute(stmt).scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El Celular principal ya está en uso.")


def _ensure_unique_email(db: Session, correo: str | None, *, exclude_id: int | None = None) -> None:
    if not correo:
        return
    stmt = select(Proveedor).where(func.lower(Proveedor.correo) == correo.strip().lower())
    if exclude_id is not None:
        stmt = stmt.where(Proveedor.id != exclude_id)
    if db.execute(stmt).scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El Correo Electrónico ya está en uso.")


def list_providers(db: Session, *, search: str | None = None, is_active: bool | None = None) -> list[ProveedorListItem]:
    stmt = select(Proveedor).order_by(Proveedor.id.desc())
    if is_active is not None:
        stmt = stmt.where(Proveedor.habilitado.is_(is_active))
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.where(
            or_(
                func.upper(Proveedor.nombres).like(term),
                func.upper(func.coalesce(Proveedor.apellido_paterno, "")).like(term),
                func.upper(func.coalesce(Proveedor.nombre_comercial, "")).like(term),
                func.upper(func.coalesce(Proveedor.ciudad, "")).like(term),
                func.upper(func.coalesce(Proveedor.celular, "")).like(term),
            )
        )
    return [_to_list_item(provider) for provider in db.execute(stmt).scalars().all()]


def get_provider(db: Session, provider_id: int) -> ProveedorDetailResponse:
    return _to_detail(_get_provider_entity(db, provider_id))


def create_provider(
    db: Session,
    *,
    payload: ProveedorCreateRequest,
    created_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> ProveedorDetailResponse:
    _ensure_unique_phone(db, payload.celular)
    _ensure_unique_email(db, payload.correo)
    provider = Proveedor(
        nombres=payload.nombres,
        apellido_paterno=payload.apellido_paterno,
        apellido_materno=payload.apellido_materno,
        nombre_comercial=payload.nombre_comercial,
        celular=payload.celular,
        celular_secundario=payload.celular_secundario,
        correo=payload.correo,
        pais=payload.pais,
        ciudad=payload.ciudad,
        direccion=payload.direccion,
        observaciones=payload.observaciones,
        habilitado=True,
    )
    db.add(provider)
    db.flush()
    register_audit_event(
        db,
        action="BOUTIQUE_PROVIDER_CREATED",
        description=f"Se creó el proveedor '{provider.nombre_completo}'.",
        account=created_by,
        user=created_by.usuario,
        reference=str(provider.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_provider(db, provider.id)


def update_provider(
    db: Session,
    *,
    provider_id: int,
    payload: ProveedorUpdateRequest,
    updated_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> ProveedorDetailResponse:
    provider = _get_provider_entity(db, provider_id)
    _ensure_unique_phone(db, payload.celular, exclude_id=provider.id)
    _ensure_unique_email(db, payload.correo, exclude_id=provider.id)
    provider.nombres = payload.nombres
    provider.apellido_paterno = payload.apellido_paterno
    provider.apellido_materno = payload.apellido_materno
    provider.nombre_comercial = payload.nombre_comercial
    provider.celular = payload.celular
    provider.celular_secundario = payload.celular_secundario
    provider.correo = payload.correo
    provider.pais = payload.pais
    provider.ciudad = payload.ciudad
    provider.direccion = payload.direccion
    provider.observaciones = payload.observaciones
    register_audit_event(
        db,
        action="BOUTIQUE_PROVIDER_UPDATED",
        description=f"Se actualizó el proveedor '{provider.nombre_completo}'.",
        account=updated_by,
        user=updated_by.usuario,
        reference=str(provider.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_provider(db, provider.id)


def set_provider_status(
    db: Session,
    *,
    provider_id: int,
    enabled: bool,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> ProveedorDetailResponse:
    provider = _get_provider_entity(db, provider_id)
    if not enabled:
        active_items = db.execute(
            select(ItemBoutique.id).where(ItemBoutique.proveedor_id == provider.id, ItemBoutique.estado.is_(True))
        ).first()
        if active_items is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No puedes deshabilitar un proveedor con items activos asociados.",
            )
    provider.habilitado = enabled
    register_audit_event(
        db,
        action="BOUTIQUE_PROVIDER_STATUS_CHANGED",
        description=f"Se actualizó el estado del proveedor '{provider.nombre_completo}' a {'ACTIVO' if enabled else 'INACTIVO'}.",
        account=changed_by,
        user=changed_by.usuario,
        reference=str(provider.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_provider(db, provider.id)
