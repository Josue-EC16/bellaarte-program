from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps.auth import require_permission
from app.models.account import Cuenta
from app.schemas.role import RoleCreateRequest, RoleResponse, RoleStatusUpdateRequest, RoleUpdateRequest
from app.services.user_service import create_role, get_role, list_roles, set_role_status, update_role


router = APIRouter()


@router.get("", response_model=list[RoleResponse])
def get_roles(
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("roles:list")),
) -> list[RoleResponse]:
    return [RoleResponse.model_validate(role) for role in list_roles(db)]


@router.get("/{role_id}", response_model=RoleResponse)
def get_role_detail(
    role_id: int,
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("roles:view")),
) -> RoleResponse:
    return RoleResponse.model_validate(get_role(db, role_id))


@router.post("", response_model=RoleResponse, status_code=201)
def create_role_record(
    payload: RoleCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("roles:create")),
) -> RoleResponse:
    role = create_role(
        db,
        payload=payload,
        created_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return RoleResponse.model_validate(role)


@router.patch("/{role_id}", response_model=RoleResponse)
def update_role_record(
    role_id: int,
    payload: RoleUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("roles:update")),
) -> RoleResponse:
    role = update_role(
        db,
        role_id=role_id,
        payload=payload,
        updated_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return RoleResponse.model_validate(role)


@router.patch("/{role_id}/status", response_model=RoleResponse)
def update_role_record_status(
    role_id: int,
    payload: RoleStatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(require_permission("roles:update_status")),
) -> RoleResponse:
    role = set_role_status(
        db,
        role_id=role_id,
        activo=payload.activo,
        changed_by=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return RoleResponse.model_validate(role)
