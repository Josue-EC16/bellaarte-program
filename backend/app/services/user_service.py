from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.audit import register_audit_event
from app.core.permissions import build_permissions_for_role
from app.core.security import hash_password
from app.models.account import Cuenta
from app.models.role import Rol
from app.models.user import Usuario
from app.schemas.auth import CreateUserRequest, UserSummary


def build_user_summary(account: Cuenta) -> UserSummary:
    return UserSummary(
        id=account.id,
        full_name=account.usuario.nombre_completo,
        role_code=account.rol.codigo,
        role_name=account.rol.nombre,
        username=account.username,
        must_change_password=account.must_change_password,
        permissions=build_permissions_for_role(account.rol.codigo),
    )


def list_roles(db: Session) -> list[Rol]:
    stmt = select(Rol).where(Rol.activo.is_(True)).order_by(Rol.nombre.asc())
    return list(db.execute(stmt).scalars().all())


def list_accounts(db: Session) -> list[Cuenta]:
    stmt = select(Cuenta).options(joinedload(Cuenta.usuario), joinedload(Cuenta.rol)).order_by(Cuenta.id.desc())
    return list(db.execute(stmt).scalars().all())


def get_role_by_code(db: Session, role_code: str) -> Rol:
    stmt = select(Rol).where(Rol.codigo == role_code)
    role = db.execute(stmt).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado.")
    return role


def ensure_user_uniqueness(db: Session, payload: CreateUserRequest) -> None:
    duplicate_user = db.execute(
        select(Usuario).where(or_(Usuario.ci == payload.ci.strip(), Usuario.correo == payload.correo.lower().strip()))
    ).scalar_one_or_none()
    if duplicate_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con el mismo CI o correo.",
        )

    duplicate_account = db.execute(select(Cuenta).where(Cuenta.username == payload.username.strip())).scalar_one_or_none()
    if duplicate_account:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El nombre de usuario ya existe.")


def create_user(
    db: Session,
    *,
    payload: CreateUserRequest,
    created_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> Cuenta:
    ensure_user_uniqueness(db, payload)
    role = get_role_by_code(db, payload.role_code)

    usuario = Usuario(
        nombres=payload.nombres,
        apellido_paterno=payload.apellido_paterno,
        apellido_materno=payload.apellido_materno,
        ci=payload.ci,
        celular=payload.celular,
        correo=payload.correo,
        zona=payload.zona,
        direccion=payload.direccion,
        activo=True,
    )
    db.add(usuario)
    db.flush()

    cuenta = Cuenta(
        usuario_id=usuario.id,
        rol_id=role.id,
        username=payload.username.strip(),
        password_hash=hash_password(payload.password_temporal),
        must_change_password=True,
        is_active=True,
    )
    db.add(cuenta)
    db.flush()

    register_audit_event(
        db,
        action="USER_CREATED",
        description=f"Se creo la cuenta interna '{cuenta.username}'.",
        account=created_by,
        user=created_by.usuario,
        reference=cuenta.username,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_account(db, cuenta.id)


def get_account(db: Session, account_id: int) -> Cuenta:
    stmt = (
        select(Cuenta)
        .where(Cuenta.id == account_id)
        .options(joinedload(Cuenta.usuario), joinedload(Cuenta.rol))
    )
    account = db.execute(stmt).scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada.")
    return account


def set_account_status(
    db: Session,
    *,
    account_id: int,
    is_active: bool,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> Cuenta:
    account = get_account(db, account_id)
    account.is_active = is_active
    register_audit_event(
        db,
        action="ACCOUNT_STATUS_CHANGED",
        description=f"Se actualizo el estado de la cuenta '{account.username}' a {'ACTIVA' if is_active else 'INACTIVA'}.",
        account=changed_by,
        user=changed_by.usuario,
        reference=account.username,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_account(db, account.id)

