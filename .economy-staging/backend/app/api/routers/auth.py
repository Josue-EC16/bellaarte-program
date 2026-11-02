from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import REFRESH_COOKIE_NAME, REFRESH_TOKEN_TYPE, decode_token
from app.deps.auth import get_current_account
from app.models.account import Cuenta
from app.schemas.auth import ChangePasswordRequest, LoginRequest, LoginResponse, MeResponse
from app.services.auth_service import (
    authenticate,
    build_login_payload,
    change_password,
    get_account_by_id,
    logout,
    validate_active_account,
)
from app.services.user_service import build_user_summary


router = APIRouter()


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/")


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    account = authenticate(
        db,
        payload.username,
        payload.password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    login_payload = build_login_payload(account)
    _set_refresh_cookie(response, login_payload["refresh_token"])
    return LoginResponse(access_token=login_payload["access_token"], user=login_payload["user"])


@router.post("/refresh", response_model=LoginResponse)
def refresh_session(request: Request, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No existe una sesion para renovar.")
    try:
        payload = decode_token(refresh_token, REFRESH_TOKEN_TYPE)
        account_id = int(payload["sub"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="El token de sesion no es valido.")

    account = get_account_by_id(db, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="La cuenta no existe.")
    validate_active_account(account)

    login_payload = build_login_payload(account)
    _set_refresh_cookie(response, login_payload["refresh_token"])
    return LoginResponse(access_token=login_payload["access_token"], user=login_payload["user"])


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def close_session(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    account: Cuenta = Depends(get_current_account),
) -> Response:
    logout(
        db,
        account=account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    _clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=MeResponse)
def me(account: Cuenta = Depends(get_current_account)) -> MeResponse:
    return MeResponse(user=build_user_summary(account))


@router.post("/change-password", response_model=MeResponse)
def update_password(
    payload: ChangePasswordRequest,
    request: Request,
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
    return MeResponse(user=build_user_summary(updated_account))
