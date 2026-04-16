from collections.abc import Callable

import casbin
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.models.account import Cuenta
from app.services.auth_service import get_account_by_id, validate_active_account


def get_current_account(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Cuenta:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de acceso requerido.")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token, ACCESS_TOKEN_TYPE)
        account_id = int(payload["sub"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido.")

    account = get_account_by_id(db, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="La cuenta no existe.")

    validate_active_account(account)
    return account


def get_enforcer() -> casbin.Enforcer:
    from app.api.router import enforcer

    return enforcer


def require_permission(permission: str) -> Callable:
    def dependency(
        account: Cuenta = Depends(get_current_account),
        enforcer_instance: casbin.Enforcer = Depends(get_enforcer),
    ) -> Cuenta:
        allowed = enforcer_instance.enforce(account.rol.codigo, permission, "use")
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para realizar esta accion.")
        return account

    return dependency
