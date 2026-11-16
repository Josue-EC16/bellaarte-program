from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.security import ACCESS_TOKEN_TYPE, REFRESH_COOKIE_NAME, REFRESH_TOKEN_TYPE, decode_token
from app.deps.auth import get_current_account
from app.models.account import Cuenta
from app.schemas.auth import ChangePasswordRequest, LoginRequest, LoginResponse, MeResponse
from app.services.auth_service import (
    authenticate,
    build_login_payload,
    change_password,
    get_account_by_id,
    logout,
)
from app.services.user_service import build_user_summary
from app.services.auth_session_service import auth_error, rotate_session
from app.services.auth_events import session_events


class SafeAuthRoute(APIRoute):
    """Validation errors keep field locations without echoing credentials."""
    def get_route_handler(self):
        handler = super().get_route_handler()
        async def safe_handler(request):
            try:
                return await handler(request)
            except RequestValidationError as error:
                errors = [{key: item[key] for key in ("type", "loc", "msg") if key in item}
                          for item in error.errors()]
                return JSONResponse(status_code=422, content={"detail": errors})
        return safe_handler


router = APIRouter(route_class=SafeAuthRoute)


def _set_refresh_cookie(response: Response, refresh_token: str, expires_at=None) -> None:
    from datetime import datetime, timezone
    remaining = max(0, int((expires_at - datetime.now(timezone.utc)).total_seconds())) if expires_at else 60 * 60 * 24 * settings.refresh_token_days
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=remaining,
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/", httponly=True,
                           secure=settings.is_production, samesite="lax")


def require_trusted_origin(request: Request) -> None:
    # JSON + SameSite cookie prevents a cross-site form fallback. API clients
    # without an Origin remain supported; browsers may only use the SPA origin.
    origin = request.headers.get("origin")
    if ((origin is not None and origin.rstrip("/") != settings.frontend_url.rstrip("/"))
            or (origin is None and request.headers.get("sec-fetch-site") == "cross-site")):
        raise HTTPException(status_code=403, detail={"code": "ORIGIN_NOT_ALLOWED", "message": "Origen de solicitud no permitido."})


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    require_trusted_origin(request)
    account = authenticate(
        db,
        payload.username,
        payload.password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    login_payload = build_login_payload(account)
    _set_refresh_cookie(response, login_payload["refresh_token"], login_payload["expires_at"])
    return LoginResponse(access_token=login_payload["access_token"], user=login_payload["user"])


@router.post("/refresh", response_model=LoginResponse)
def refresh_session(request: Request, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    require_trusted_origin(request)
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise auth_error("TOKEN_INVALID", "No existe una sesión para renovar.")
    try:
        payload = decode_token(refresh_token, REFRESH_TOKEN_TYPE)
        account_id = int(payload["sub"])
    except (ValueError, KeyError, TypeError):
        raise auth_error("TOKEN_INVALID") from None

    account = get_account_by_id(db, account_id)
    if account is None:
        raise auth_error()

    login_payload = rotate_session(db, account, payload, refresh_token)
    _set_refresh_cookie(response, login_payload["refresh_token"], login_payload["expires_at"])
    return LoginResponse(access_token=login_payload["access_token"], user=login_payload["user"])


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def close_session(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Response:
    require_trusted_origin(request)
    # Logout is idempotent and also works after the access JWT expires. A signed
    # refresh cookie can identify its own session, never another account's.
    authorization = request.headers.get("authorization", "")
    credentials = [(authorization.removeprefix("Bearer ").strip(), ACCESS_TOKEN_TYPE)] if authorization.startswith("Bearer ") else []
    credentials.append((request.cookies.get(REFRESH_COOKIE_NAME), REFRESH_TOKEN_TYPE))
    for token, token_type in credentials:
        if not token:
            continue
        try:
            payload = decode_token(token, token_type)
            account = get_account_by_id(db, int(payload["sub"]))
        except (ValueError, KeyError, TypeError):
            continue
        if account is not None:
            account._auth_payload = payload
            try:
                logout(db, account=account,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"))
            except HTTPException as error:
                db.rollback()
                if error.status_code != 401:
                    raise
        break
    _clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=MeResponse)
def me(account: Cuenta = Depends(get_current_account)) -> MeResponse:
    return MeResponse(user=build_user_summary(account))


@router.get("/events")
def auth_events(request: Request, db: Session = Depends(get_db), account: Cuenta = Depends(get_current_account)):
    account_id, payload = account.id, dict(account._auth_payload)
    # Dependency cleanup alone happens after streaming; release its transaction
    # before waiting so idle browser tabs do not retain pooled connections.
    db.close()
    return StreamingResponse(session_events(request, account_id, payload), media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@router.post("/change-password", response_model=MeResponse)
def update_password(
    payload: ChangePasswordRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(get_current_account),
) -> MeResponse:
    updated_account = change_password(
        db,
        account=account,
        current_password=payload.current_password,
        new_password=payload.new_password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    _clear_refresh_cookie(response)
    return MeResponse(user=build_user_summary(updated_account))
