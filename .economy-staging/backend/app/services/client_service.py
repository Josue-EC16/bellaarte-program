import re

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.audit import register_audit_event
from app.models.account import Cuenta
from app.models.client import Cliente
from app.schemas.client import ClienteCreateRequest, ClienteDetailResponse, ClienteListItem, ClienteUpdateRequest


CLIENT_CODE_PATTERN = re.compile(r"^CLI-\d{5}$")


def _to_list_item(cliente: Cliente) -> ClienteListItem:
    return ClienteListItem(
        id=cliente.id,
        codigo=cliente.codigo,
        full_name=cliente.nombre_completo,
        celular=cliente.celular,
        correo=cliente.correo,
        ci=cliente.ci,
        ciudad=cliente.ciudad,
        zona=cliente.zona,
        is_active=cliente.habilitado,
        created_at=cliente.fecha_registro,
    )


def _to_detail(cliente: Cliente) -> ClienteDetailResponse:
    return ClienteDetailResponse(
        id=cliente.id,
        codigo=cliente.codigo,
        nombres=cliente.nombres,
        apellido_paterno=cliente.apellido_paterno,
        apellido_materno=cliente.apellido_materno,
        full_name=cliente.nombre_completo,
        celular=cliente.celular,
        celular_referencia=cliente.celular_referencia,
        nombre_referencia=cliente.nombre_referencia,
        correo=cliente.correo,
        ci=cliente.ci,
        fecha_nacimiento=cliente.fecha_nacimiento,
        pais=cliente.pais,
        ciudad=cliente.ciudad,
        zona=cliente.zona,
        calle=cliente.calle,
        observaciones=cliente.observaciones,
        is_active=cliente.habilitado,
        created_at=cliente.fecha_registro,
    )


def _ensure_unique_client_code(db: Session, codigo: str, *, exclude_id: int | None = None) -> None:
    stmt = select(Cliente).where(func.upper(Cliente.codigo) == codigo.strip().upper())
    if exclude_id is not None:
        stmt = stmt.where(Cliente.id != exclude_id)
    if db.execute(stmt).scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un cliente con ese código.")


def _ensure_unique_client_ci(db: Session, ci: str | None, *, exclude_id: int | None = None) -> None:
    if not ci:
        return
    stmt = select(Cliente).where(Cliente.ci == ci.strip())
    if exclude_id is not None:
        stmt = stmt.where(Cliente.id != exclude_id)
    if db.execute(stmt).scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La Cédula de Identidad ya está en uso.")


def _ensure_unique_client_email(db: Session, correo: str | None, *, exclude_id: int | None = None) -> None:
    if not correo:
        return
    stmt = select(Cliente).where(func.lower(Cliente.correo) == correo.strip().lower())
    if exclude_id is not None:
        stmt = stmt.where(Cliente.id != exclude_id)
    if db.execute(stmt).scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El Correo Electrónico ya está en uso.")


def _generate_client_code(db: Session) -> str:
    codes = db.execute(select(Cliente.codigo)).scalars().all()
    max_number = 0
    for code in codes:
        if not code:
            continue
        match = CLIENT_CODE_PATTERN.match(code.strip().upper())
        if match:
            max_number = max(max_number, int(code.strip().upper().split("-")[1]))
    return f"CLI-{max_number + 1:05d}"


def _resolve_client_code(db: Session, codigo: str | None, *, exclude_id: int | None = None) -> str:
    if codigo:
        normalized = codigo.strip().upper()
        _ensure_unique_client_code(db, normalized, exclude_id=exclude_id)
        return normalized
    generated = _generate_client_code(db)
    _ensure_unique_client_code(db, generated, exclude_id=exclude_id)
    return generated


def list_clients(db: Session, *, search: str | None = None, is_active: bool | None = None) -> list[ClienteListItem]:
    stmt = select(Cliente).order_by(Cliente.id.desc())
    if is_active is not None:
        stmt = stmt.where(Cliente.habilitado.is_(is_active))
    if search:
        term = f"%{search.strip().upper()}%"
        stmt = stmt.where(
            or_(
                func.upper(Cliente.codigo).like(term),
                func.upper(Cliente.nombres).like(term),
                func.upper(Cliente.apellido_paterno).like(term),
                func.upper(func.coalesce(Cliente.apellido_materno, "")).like(term),
                func.upper(func.coalesce(Cliente.ci, "")).like(term),
                func.upper(Cliente.celular).like(term),
                func.upper(func.coalesce(Cliente.ciudad, "")).like(term),
            )
        )
    return [_to_list_item(cliente) for cliente in db.execute(stmt).scalars().all()]


def get_client_entity(db: Session, client_id: int) -> Cliente:
    cliente = db.execute(select(Cliente).where(Cliente.id == client_id)).scalar_one_or_none()
    if cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado.")
    return cliente


def get_client(db: Session, client_id: int) -> ClienteDetailResponse:
    return _to_detail(get_client_entity(db, client_id))


def create_client(
    db: Session,
    *,
    payload: ClienteCreateRequest,
    created_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> ClienteDetailResponse:
    codigo = _resolve_client_code(db, payload.codigo)
    _ensure_unique_client_ci(db, payload.ci)
    _ensure_unique_client_email(db, payload.correo)
    cliente = Cliente(
        codigo=codigo,
        nombres=payload.nombres,
        apellido_paterno=payload.apellido_paterno,
        apellido_materno=payload.apellido_materno,
        celular=payload.celular,
        celular_referencia=payload.celular_referencia,
        nombre_referencia=payload.nombre_referencia,
        correo=payload.correo,
        ci=payload.ci,
        fecha_nacimiento=payload.fecha_nacimiento,
        pais=payload.pais,
        ciudad=payload.ciudad,
        zona=payload.zona,
        calle=payload.calle,
        observaciones=payload.observaciones,
        habilitado=True,
    )
    db.add(cliente)
    db.flush()
    register_audit_event(
        db,
        action="CLIENT_CREATED",
        description=f"Se creó el cliente '{cliente.codigo}'.",
        account=created_by,
        user=created_by.usuario,
        reference=cliente.codigo,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_client(db, cliente.id)


def update_client(
    db: Session,
    *,
    client_id: int,
    payload: ClienteUpdateRequest,
    updated_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> ClienteDetailResponse:
    cliente = get_client_entity(db, client_id)
    cliente.codigo = _resolve_client_code(db, payload.codigo, exclude_id=cliente.id)
    _ensure_unique_client_ci(db, payload.ci, exclude_id=cliente.id)
    _ensure_unique_client_email(db, payload.correo, exclude_id=cliente.id)
    cliente.nombres = payload.nombres
    cliente.apellido_paterno = payload.apellido_paterno
    cliente.apellido_materno = payload.apellido_materno
    cliente.celular = payload.celular
    cliente.celular_referencia = payload.celular_referencia
    cliente.nombre_referencia = payload.nombre_referencia
    cliente.correo = payload.correo
    cliente.ci = payload.ci
    cliente.fecha_nacimiento = payload.fecha_nacimiento
    cliente.pais = payload.pais
    cliente.ciudad = payload.ciudad
    cliente.zona = payload.zona
    cliente.calle = payload.calle
    cliente.observaciones = payload.observaciones
    register_audit_event(
        db,
        action="CLIENT_UPDATED",
        description=f"Se actualizó el cliente '{cliente.codigo}'.",
        account=updated_by,
        user=updated_by.usuario,
        reference=cliente.codigo,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_client(db, cliente.id)


def set_client_status(
    db: Session,
    *,
    client_id: int,
    habilitado: bool,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> ClienteDetailResponse:
    cliente = get_client_entity(db, client_id)
    cliente.habilitado = habilitado
    register_audit_event(
        db,
        action="CLIENT_STATUS_CHANGED",
        description=f"Se actualizó el estado del cliente '{cliente.codigo}' a {'ACTIVO' if habilitado else 'INACTIVO'}.",
        account=changed_by,
        user=changed_by.usuario,
        reference=cliente.codigo,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_client(db, cliente.id)
