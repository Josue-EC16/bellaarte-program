from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"
REFRESH_COOKIE_NAME = "bellaarte_refresh_token"


class TokenExpired(ValueError):
    pass


def hash_password(password: str) -> str:
    if not password or "\x00" in password or len(password.encode("utf-8")) > 72:
        raise ValueError("La contraseña debe contener entre 1 y 72 bytes UTF-8.")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or len(plain_password.encode("utf-8")) > 72:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError):
        return False


def _build_token(
    subject: str,
    role_code: str,
    token_type: str,
    secret: str,
    expires_delta: timedelta,
    session_id: str | None = None,
    auth_version: int = 0,
    expires_at: datetime | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role_code,
        "type": token_type,
        "iat": now,
        "exp": min(now + expires_delta, expires_at) if expires_at else now + expires_delta,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "jti": str(uuid4()),
        "sid": session_id or str(uuid4()),
        "ver": auth_version,
    }
    return jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, role_code: str, *, session_id: str | None = None,
                        auth_version: int = 0, expires_at: datetime | None = None) -> str:
    return _build_token(
        subject=subject,
        role_code=role_code,
        token_type=ACCESS_TOKEN_TYPE,
        secret=settings.jwt_secret_key,
        expires_delta=timedelta(minutes=settings.access_token_minutes),
        session_id=session_id, auth_version=auth_version, expires_at=expires_at,
    )


def create_refresh_token(subject: str, role_code: str, *, session_id: str | None = None,
                         auth_version: int = 0, expires_at: datetime | None = None) -> str:
    return _build_token(
        subject=subject,
        role_code=role_code,
        token_type=REFRESH_TOKEN_TYPE,
        secret=settings.jwt_refresh_secret_key,
        expires_delta=timedelta(days=settings.refresh_token_days),
        session_id=session_id, auth_version=auth_version, expires_at=expires_at,
    )


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    secret = settings.jwt_secret_key if expected_type == ACCESS_TOKEN_TYPE else settings.jwt_refresh_secret_key
    try:
        payload = jwt.decode(token, secret, algorithms=[settings.jwt_algorithm],
                             issuer=settings.jwt_issuer, audience=settings.jwt_audience,
                             options={"require_exp": True, "require_iat": True,
                                      "require_sub": True, "require_jti": True,
                                      "require_aud": True, "require_iss": True})
    except ExpiredSignatureError as exc:
        raise TokenExpired("Token expirado.") from exc
    except JWTError as exc:
        raise ValueError("Token invalido o expirado.") from exc

    if (payload.get("type") != expected_type or not isinstance(payload.get("sid"), str)
            or not isinstance(payload.get("ver"), int) or isinstance(payload.get("ver"), bool)
            or payload["ver"] < 0):
        raise ValueError("Tipo de token invalido.")
    return payload
