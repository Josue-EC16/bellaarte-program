from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"
REFRESH_COOKIE_NAME = "bellaarte_refresh_token"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _build_token(
    subject: str,
    role_code: str,
    token_type: str,
    secret: str,
    expires_delta: timedelta,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role_code,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, role_code: str) -> str:
    return _build_token(
        subject=subject,
        role_code=role_code,
        token_type=ACCESS_TOKEN_TYPE,
        secret=settings.jwt_secret_key,
        expires_delta=timedelta(minutes=settings.access_token_minutes),
    )


def create_refresh_token(subject: str, role_code: str) -> str:
    return _build_token(
        subject=subject,
        role_code=role_code,
        token_type=REFRESH_TOKEN_TYPE,
        secret=settings.jwt_refresh_secret_key,
        expires_delta=timedelta(days=settings.refresh_token_days),
    )


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    secret = settings.jwt_secret_key if expected_type == ACCESS_TOKEN_TYPE else settings.jwt_refresh_secret_key
    try:
        payload = jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Token invalido o expirado.") from exc

    if payload.get("type") != expected_type:
        raise ValueError("Tipo de token invalido.")
    return payload
