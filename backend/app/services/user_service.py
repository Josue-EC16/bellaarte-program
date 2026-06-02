from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.audit import register_audit_event
from app.core.permissions import build_permissions_for_role
from app.core.security import hash_password
from app.models.account import Cuenta
from app.models.role import Rol
from app.models.user import Usuario
from app.schemas.auth import CreateUserRequest, ResetPasswordRequest, UpdateUserRequest, UserSummary
from app.schemas.role import RoleCreateRequest, RoleUpdateRequest
from app.services.notification_service import send_welcome_email_with_tracking


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


def _account_base_query():
    return select(Cuenta).options(joinedload(Cuenta.usuario), joinedload(Cuenta.rol))


def list_roles(db: Session) -> list[Rol]:
    stmt = select(Rol).order_by(Rol.nombre.asc())
    return list(db.execute(stmt).scalars().all())


def get_role(db: Session, role_id: int) -> Rol:
    role = db.execute(select(Rol).where(Rol.id == role_id)).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado.")
    return role


def get_role_by_code(db: Session, role_code: str) -> Rol:
    stmt = select(Rol).where(Rol.codigo == role_code.strip().upper())
    role = db.execute(stmt).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado.")
    return role


def _ensure_role_uniqueness(db: Session, *, codigo: str | None, nombre: str, exclude_id: int | None = None) -> None:
    conditions = [func.upper(Rol.nombre) == nombre.strip().upper()]
    if codigo is not None:
        conditions.append(func.upper(Rol.codigo) == codigo.strip().upper())
    stmt = select(Rol).where(or_(*conditions))
    if exclude_id is not None:
        stmt = stmt.where(Rol.id != exclude_id)
    duplicate = db.execute(stmt).scalar_one_or_none()
    if duplicate is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un rol con el mismo codigo o nombre.")


def create_role(
    db: Session,
    *,
    payload: RoleCreateRequest,
    created_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> Rol:
    _ensure_role_uniqueness(db, codigo=payload.codigo, nombre=payload.nombre)
    role = Rol(
        codigo=payload.codigo.strip().upper(),
        nombre=payload.nombre.strip().upper(),
        descripcion=payload.descripcion.strip() if payload.descripcion else None,
        activo=True,
    )
    db.add(role)
    db.flush()
    register_audit_event(
        db,
        action="ROLE_CREATED",
        description=f"Se creo el rol '{role.codigo}'.",
        account=created_by,
        user=created_by.usuario,
        reference=role.codigo,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_role(db, role.id)


def update_role(
    db: Session,
    *,
    role_id: int,
    payload: RoleUpdateRequest,
    updated_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> Rol:
    role = get_role(db, role_id)
    _ensure_role_uniqueness(db, codigo=None, nombre=payload.nombre, exclude_id=role.id)
    role.nombre = payload.nombre.strip().upper()
    role.descripcion = payload.descripcion.strip() if payload.descripcion else None
    register_audit_event(
        db,
        action="ROLE_UPDATED",
        description=f"Se actualizo el rol '{role.codigo}'.",
        account=updated_by,
        user=updated_by.usuario,
        reference=role.codigo,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_role(db, role.id)


def set_role_status(
    db: Session,
    *,
    role_id: int,
    activo: bool,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> Rol:
    role = get_role(db, role_id)
    if not activo:
        active_accounts = db.execute(
            select(Cuenta.id).where(Cuenta.rol_id == role.id, Cuenta.is_active.is_(True)).limit(1)
        ).scalar_one_or_none()
        if active_accounts is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No puedes desactivar un rol con cuentas activas asociadas.",
            )
    role.activo = activo
    register_audit_event(
        db,
        action="ROLE_STATUS_CHANGED",
        description=f"Se actualizo el estado del rol '{role.codigo}' a {'ACTIVO' if activo else 'INACTIVO'}.",
        account=changed_by,
        user=changed_by.usuario,
        reference=role.codigo,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_role(db, role.id)


def list_accounts(db: Session) -> list[Cuenta]:
    stmt = _account_base_query().order_by(Cuenta.id.desc())
    return list(db.execute(stmt).scalars().all())


def get_account(db: Session, account_id: int) -> Cuenta:
    account = db.execute(_account_base_query().where(Cuenta.id == account_id)).scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada.")
    return account


def get_account_by_user_id(db: Session, user_id: int) -> Cuenta:
    account = db.execute(_account_base_query().where(Cuenta.usuario_id == user_id)).scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada.")
    return account


def ensure_user_uniqueness(
    db: Session,
    *,
    ci: str,
    correo: str,
    username: str,
    exclude_account_id: int | None = None,
    exclude_user_id: int | None = None,
) -> None:
    stmt_user = select(Usuario).where(or_(Usuario.ci == ci.strip(), Usuario.correo == correo.lower().strip()))
    if exclude_user_id is not None:
        stmt_user = stmt_user.where(Usuario.id != exclude_user_id)
    duplicate_user = db.execute(stmt_user).scalar_one_or_none()
    if duplicate_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con el mismo CI o correo.",
        )

    stmt_account = select(Cuenta).where(Cuenta.username == username.strip().lower())
    if exclude_account_id is not None:
        stmt_account = stmt_account.where(Cuenta.id != exclude_account_id)
    duplicate_account = db.execute(stmt_account).scalar_one_or_none()
    if duplicate_account:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El nombre de usuario ya existe.")


def create_user(
    db: Session,
    *,
    payload: CreateUserRequest,
    created_by: Cuenta,
    background_tasks: BackgroundTasks,
    ip_address: str | None,
    user_agent: str | None,
) -> Cuenta:
    username = f"{payload.nombres[0]}{payload.apellido_paterno[0]}{payload.ci}".upper()
    password_temporal = payload.ci.upper()

    ensure_user_uniqueness(db, ci=payload.ci, correo=payload.correo, username=username)
    role = get_role_by_code(db, payload.role_code)
    if not role.activo:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El rol asignado esta deshabilitado.")

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
        username=username,
        password_hash=hash_password(password_temporal),
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

    background_tasks.add_task(
        send_welcome_email_with_tracking,
        user_id=usuario.id,
        recipient_email=payload.correo,
        full_name=f"{payload.nombres} {payload.apellido_paterno} {payload.apellido_materno or ''}".strip(),
        username=username,
        initial_password=password_temporal,
    )

    return get_account(db, cuenta.id)


def update_user(
    db: Session,
    *,
    account_id: int,
    payload: UpdateUserRequest,
    updated_by: Cuenta,
    background_tasks: BackgroundTasks,
    ip_address: str | None,
    user_agent: str | None,
) -> Cuenta:
    account = get_account(db, account_id)
    role = get_role_by_code(db, payload.role_code)
    if not role.activo:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El rol asignado esta deshabilitado.")
    ensure_user_uniqueness(
        db,
        ci=payload.ci,
        correo=payload.correo,
        username=account.username,
        exclude_account_id=account.id,
        exclude_user_id=account.usuario.id,
    )

    email_changed = account.usuario.correo.lower().strip() != payload.correo.lower().strip()
    should_resend_welcome = email_changed and account.last_login_at is None

    account.usuario.nombres = payload.nombres
    account.usuario.apellido_paterno = payload.apellido_paterno
    account.usuario.apellido_materno = payload.apellido_materno
    account.usuario.ci = payload.ci
    account.usuario.celular = payload.celular
    account.usuario.correo = payload.correo
    account.usuario.zona = payload.zona
    account.usuario.direccion = payload.direccion
    account.usuario.activo = payload.user_is_active
    account.rol_id = role.id
    account.is_active = payload.account_is_active

    register_audit_event(
        db,
        action="USER_UPDATED",
        description=f"Se actualizo la cuenta interna '{account.username}'.",
        account=updated_by,
        user=updated_by.usuario,
        reference=account.username,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()

    if should_resend_welcome:
        background_tasks.add_task(
            send_welcome_email_with_tracking,
            user_id=account.usuario.id,
            recipient_email=payload.correo,
            full_name=f"{payload.nombres} {payload.apellido_paterno} {payload.apellido_materno or ''}".strip(),
            username=account.username,
            initial_password=payload.ci.upper(),
        )

    return get_account(db, account.id)


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
    account.usuario.activo = is_active
    register_audit_event(
        db,
        action="ACCOUNT_STATUS_CHANGED",
        description=f"Se actualizo el estado operativo de la cuenta '{account.username}' a {'ACTIVA' if is_active else 'INACTIVA'}.",
        account=changed_by,
        user=changed_by.usuario,
        reference=account.username,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_account(db, account.id)


def reset_account_password(
    db: Session,
    *,
    account_id: int,
    payload: ResetPasswordRequest,
    changed_by: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> Cuenta:
    account = get_account(db, account_id)
    new_temporary_password = account.usuario.ci.upper()
    account.password_hash = hash_password(new_temporary_password)
    account.must_change_password = True
    register_audit_event(
        db,
        action="PASSWORD_RESET",
        description=f"Se reseteo la contrasena de la cuenta '{account.username}'.",
        account=changed_by,
        user=changed_by.usuario,
        reference=account.username,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return get_account(db, account.id)
