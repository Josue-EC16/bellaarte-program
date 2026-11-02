from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps.auth import require_permission
from app.models.account import Cuenta
from app.schemas.auth import CreateUserRequest, ResetPasswordRequest, StatusUpdateRequest, UpdateUserRequest
from app.schemas.user import UserCreateResponse, UserDetailResponse, UserListItem
from app.services.user_service import (
    create_user,
    get_account,
    get_account_by_user_id,
    list_accounts,
    reset_account_password,
    set_account_status,
    update_user,
)


router = APIRouter()


@router.get("", response_model=list[UserListItem])
def get_users(
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("users:list")),
) -> list[UserListItem]:
    users = []
    for account in list_accounts(db):
        users.append(
            UserListItem(
                id=account.id,
                user_id=account.usuario.id,
                full_name=account.usuario.nombre_completo,
                username=account.username,
                correo=account.usuario.correo,
                ci=account.usuario.ci,
                celular=account.usuario.celular,
                zona=account.usuario.zona,
                role_code=account.rol.codigo,
                role_name=account.rol.nombre,
                user_is_active=account.usuario.activo,
                account_is_active=account.is_active,
                must_change_password=account.must_change_password,
                last_login_at=account.last_login_at,
            )
        )
    return users


@router.get("/{user_id}", response_model=UserDetailResponse)
def get_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("users:view")),
) -> UserDetailResponse:
    account = get_account_by_user_id(db, user_id)
    return UserDetailResponse(
        id=account.id,
        user_id=account.usuario.id,
        full_name=account.usuario.nombre_completo,
        nombres=account.usuario.nombres,
        apellido_paterno=account.usuario.apellido_paterno,
        apellido_materno=account.usuario.apellido_materno,
        username=account.username,
        correo=account.usuario.correo,
        ci=account.usuario.ci,
        celular=account.usuario.celular,
        zona=account.usuario.zona,
        direccion=account.usuario.direccion,
        role_code=account.rol.codigo,
        role_name=account.rol.nombre,
        user_is_active=account.usuario.activo,
        account_is_active=account.is_active,
        must_change_password=account.must_change_password,
        last_login_at=account.last_login_at,
    )


@router.post("", response_model=UserCreateResponse, status_code=201)
def create_internal_user(
    payload: CreateUserRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("users:create")),
) -> UserCreateResponse:
    created = create_user(
        db,
        payload=payload,
        created_by=account,
        background_tasks=background_tasks,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return UserCreateResponse(
        id=created.id,
        user_id=created.usuario.id,
        full_name=created.usuario.nombre_completo,
        username=created.username,
        correo=created.usuario.correo,
        ci=created.usuario.ci,
        celular=created.usuario.celular,
        zona=created.usuario.zona,
        role_code=created.rol.codigo,
        role_name=created.rol.nombre,
        user_is_active=created.usuario.activo,
        account_is_active=created.is_active,
        must_change_password=created.must_change_password,
        last_login_at=created.last_login_at,
    )


@router.patch("/{account_id}", response_model=UserCreateResponse)
def update_internal_user(
    account_id: int,
    payload: UpdateUserRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("users:update")),
) -> UserCreateResponse:
    updated = update_user(
        db,
        account_id=account_id,
        payload=payload,
        updated_by=account,
        background_tasks=background_tasks,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return UserCreateResponse(
        id=updated.id,
        user_id=updated.usuario.id,
        full_name=updated.usuario.nombre_completo,
        username=updated.username,
        correo=updated.usuario.correo,
        ci=updated.usuario.ci,
        celular=updated.usuario.celular,
        zona=updated.usuario.zona,
        role_code=updated.rol.codigo,
        role_name=updated.rol.nombre,
        user_is_active=updated.usuario.activo,
        account_is_active=updated.is_active,
        must_change_password=updated.must_change_password,
        last_login_at=updated.last_login_at,
    )


@router.patch("/{account_id}/status", response_model=UserCreateResponse)
def update_user_status(
    account_id: int,
    payload: StatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("users:update_status")),
) -> UserCreateResponse:
    updated = set_account_status(
        db,
        account_id=account_id,
        is_active=payload.is_active,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return UserCreateResponse(
        id=updated.id,
        user_id=updated.usuario.id,
        full_name=updated.usuario.nombre_completo,
        username=updated.username,
        correo=updated.usuario.correo,
        ci=updated.usuario.ci,
        celular=updated.usuario.celular,
        zona=updated.usuario.zona,
        role_code=updated.rol.codigo,
        role_name=updated.rol.nombre,
        user_is_active=updated.usuario.activo,
        account_is_active=updated.is_active,
        must_change_password=updated.must_change_password,
        last_login_at=updated.last_login_at,
    )


@router.post("/{account_id}/reset-password", response_model=UserCreateResponse)
def reset_internal_user_password(
    account_id: int,
    payload: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("users:reset_password")),
) -> UserCreateResponse:
    updated = reset_account_password(
        db,
        account_id=account_id,
        payload=payload,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return UserCreateResponse(
        id=updated.id,
        user_id=updated.usuario.id,
        full_name=updated.usuario.nombre_completo,
        username=updated.username,
        correo=updated.usuario.correo,
        ci=updated.usuario.ci,
        celular=updated.usuario.celular,
        zona=updated.usuario.zona,
        role_code=updated.rol.codigo,
        role_name=updated.rol.nombre,
        user_is_active=updated.usuario.activo,
        account_is_active=updated.is_active,
        must_change_password=updated.must_change_password,
        last_login_at=updated.last_login_at,
    )
