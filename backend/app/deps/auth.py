from collections.abc import Callable

import casbin
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.audit import register_audit_failure
from app.core.database import get_db
from app.core.security import ACCESS_TOKEN_TYPE, TokenExpired, decode_token
from app.models.account import Cuenta
from app.services.auth_service import get_account_by_id
from app.services.auth_session_service import auth_error, validate_session


def get_current_account(
    request: Request,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Cuenta:
    if not authorization or not authorization.startswith("Bearer "):
        raise auth_error("TOKEN_INVALID", "Token de acceso requerido.")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token, ACCESS_TOKEN_TYPE)
        account_id = int(payload["sub"])
    except TokenExpired:
        raise auth_error("ACCESS_TOKEN_EXPIRED") from None
    except (ValueError, KeyError, TypeError):
        raise auth_error("TOKEN_INVALID") from None

    account = get_account_by_id(db, account_id)
    if account is None:
        raise auth_error()

    validate_session(db, account, payload)
    if account.must_change_password and request.url.path not in {
        "/api/v1/auth/me", "/api/v1/auth/change-password", "/api/v1/auth/logout", "/api/v1/auth/events",
    }:
        raise HTTPException(status_code=403, detail={"code": "PASSWORD_CHANGE_REQUIRED",
                            "message": "Debes cambiar tu contraseña antes de continuar."})
    return account


def get_enforcer() -> casbin.Enforcer:
    from app.api.router import enforcer

    return enforcer


def require_permission(permission: str) -> Callable:
    def dependency(
        request: Request,
        db: Session = Depends(get_db),
        account: Cuenta = Depends(get_current_account),
        enforcer_instance: casbin.Enforcer = Depends(get_enforcer),
    ) -> Cuenta:
        admin_resource = permission.startswith(("users:", "roles:", "exchange_rates_sync:"))
        allowed = (not admin_resource or account.rol.codigo == "ADMIN") and enforcer_instance.enforce(account.rol.codigo, permission, "use")
        if not allowed:
            try:
                register_audit_failure(
                    db,
                    action="ACCESS_DENIED",
                    description=f"Acceso denegado al permiso '{permission}'.",
                    account=account,
                    user=account.usuario,
                    reference=permission,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    http_method=request.method,
                )
                db.commit()
            except Exception:
                db.rollback()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para realizar esta accion.")
        return account

    return dependency
