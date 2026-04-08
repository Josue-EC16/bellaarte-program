from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps.auth import require_permission
from app.models.account import Cuenta
from app.schemas.auth import CreateUserRequest, StatusUpdateRequest
from app.schemas.user import UserCreateResponse, UserListItem
from app.services.user_service import create_user, list_accounts, set_account_status


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
                is_active=account.is_active,
                must_change_password=account.must_change_password,
                last_login_at=account.last_login_at,
            )
        )
    return users


@router.post("", response_model=UserCreateResponse, status_code=201)
def create_internal_user(
    payload: CreateUserRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("users:create")),
) -> UserCreateResponse:
    created = create_user(
        db,
        payload=payload,
        created_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return UserCreateResponse(
        id=created.id,
        user_id=created.usuario.id,
        full_name=created.usuario.nombre_completo,
        username=created.username,
        role_code=created.rol.codigo,
        role_name=created.rol.nombre,
        is_active=created.is_active,
        must_change_password=created.must_change_password,
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
        role_code=updated.rol.codigo,
        role_name=updated.rol.nombre,
        is_active=updated.is_active,
        must_change_password=updated.must_change_password,
    )

