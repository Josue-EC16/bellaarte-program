from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps.auth import require_permission
from app.models.account import Cuenta
from app.schemas.role import RoleResponse
from app.services.user_service import list_roles


router = APIRouter()


@router.get("", response_model=list[RoleResponse])
def get_roles(
    db: Session = Depends(get_db),
    _account: Cuenta = Depends(require_permission("roles:list")),
) -> list[RoleResponse]:
    return [RoleResponse.model_validate(role) for role in list_roles(db)]

