"""Session transactions. The business coordinator owns commit/rollback."""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import delete, select, text, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.models.account import Cuenta
from app.models.auth_session import AuthSession, LoginBucket
from app.models.user import Usuario


AUTH_CHANNEL = "bab_auth_changes"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def auth_error(code: str = "SESSION_REVOKED", message: str = "Tu sesión terminó. Vuelve a iniciar sesión.") -> HTTPException:
    return HTTPException(status_code=401, detail={"code": code, "message": message},
                         headers={"WWW-Authenticate": "Bearer"})


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def lock_account(db: Session, account: Cuenta) -> Cuenta:
    """Shared mutation order: collaborator -> account; never locks its joined role."""
    db.execute(select(Usuario.id).where(Usuario.id == account.usuario_id).with_for_update())
    db.execute(select(Cuenta.id).where(Cuenta.id == account.id).with_for_update())
    db.refresh(account)
    db.refresh(account.usuario)
    db.refresh(account.rol)
    return account


def _notify(db: Session, account_id: int, version: int) -> None:
    # PostgreSQL delivers NOTIFY only after the surrounding transaction commits.
    db.execute(text("SELECT pg_notify(:channel, :payload)"),
               {"channel": AUTH_CHANNEL, "payload": json.dumps({"account_id": account_id, "version": version})})


def notify_account_change(db: Session, account: Cuenta) -> None:
    account.security_version = (account.security_version or 0) + 1
    db.flush()
    _notify(db, account.id, account.security_version)


def revoke_account_sessions(db: Session, account: Cuenta, reason: str) -> None:
    account.auth_version = (account.auth_version or 0) + 1
    db.execute(update(AuthSession).where(AuthSession.cuenta_id == account.id,
                                       AuthSession.revoked_at.is_(None)).values(
        revoked_at=now_utc(), revocation_reason=reason[:40]))
    notify_account_change(db, account)


def revoke_session(db: Session, session: AuthSession, reason: str) -> None:
    if session.revoked_at is None:
        session.revoked_at, session.revocation_reason = now_utc(), reason[:40]
        db.flush()
        _notify(db, session.cuenta_id, 0)


def create_session(db: Session, account: Cuenta) -> dict:
    identity = uuid4()
    expires = now_utc() + timedelta(days=settings.refresh_token_days)
    version = account.auth_version or 0
    refresh = create_refresh_token(str(account.id), account.rol.codigo, session_id=str(identity),
                                   auth_version=version, expires_at=expires)
    session = AuthSession(id=identity, cuenta_id=account.id, auth_version=version,
                          refresh_hash=token_digest(refresh), expires_at=expires)
    db.add(session)
    db.flush()
    account._auth_session_id = identity
    return session_payload(account, session, refresh)


def session_payload(account: Cuenta, session: AuthSession, refresh_token: str) -> dict:
    from app.services.user_service import build_user_summary
    return {"access_token": create_access_token(str(account.id), account.rol.codigo,
                session_id=str(session.id), auth_version=session.auth_version, expires_at=session.expires_at),
            "refresh_token": refresh_token, "expires_at": session.expires_at,
            "user": build_user_summary(account)}


def validate_session(db: Session, account: Cuenta, payload: dict, *, lock: bool = False) -> AuthSession:
    try:
        identity = UUID(payload["sid"])
    except (ValueError, KeyError, TypeError, AttributeError):
        raise auth_error("TOKEN_INVALID") from None
    stmt = select(AuthSession).where(AuthSession.id == identity, AuthSession.cuenta_id == account.id)
    if lock:
        stmt = stmt.with_for_update()
    session = db.execute(stmt.execution_options(populate_existing=True)).scalar_one_or_none()
    if session is None or session.revoked_at is not None:
        raise auth_error()
    if session.expires_at <= now_utc():
        raise auth_error("SESSION_EXPIRED")
    if payload.get("ver") != account.auth_version or session.auth_version != account.auth_version:
        raise auth_error()
    if not account.is_active or not account.usuario.activo or not account.rol.activo:
        raise auth_error("ACCOUNT_DISABLED", "La cuenta está deshabilitada.")
    account._auth_session_id = session.id
    account._auth_payload = payload
    return session


def rotate_session(db: Session, account: Cuenta, payload: dict, refresh_token: str) -> dict:
    lock_account(db, account)
    session = validate_session(db, account, payload, lock=True)
    if not hmac.compare_digest(session.refresh_hash, token_digest(refresh_token)):
        # A signed but already consumed refresh token compromises only its family.
        revoke_session(db, session, "REFRESH_REUSE")
        from app.core.audit import register_audit_event
        register_audit_event(db, action="LOGOUT", description="Sesión revocada por reutilización de renovación.",
                             account=account, user=account.usuario, reference=str(session.id))
        db.commit()  # Revocation must survive the HTTP error.
        raise auth_error()
    refresh = create_refresh_token(str(account.id), account.rol.codigo, session_id=str(session.id),
                                   auth_version=session.auth_version, expires_at=session.expires_at)
    session.refresh_hash = token_digest(refresh)
    result = session_payload(account, session, refresh)
    db.commit()
    return result


def _rate_key(kind: str, username: str, ip_address: str) -> str:
    message = f"{kind}\0{ip_address}\0{username.strip().casefold() if kind == 'pair' else ''}"
    return hmac.new(settings.jwt_secret_key.encode(), message.encode("utf-8"), hashlib.sha256).hexdigest()


def lock_login_buckets(db: Session, username: str, ip_address: str | None) -> list[tuple[LoginBucket, int]]:
    """Bounded fixed windows under transaction locks, shared by all API workers."""
    now = now_utc()
    keys = [(_rate_key("pair", username, ip_address or "unknown"), settings.auth_login_pair_limit),
            (_rate_key("ip", username, ip_address or "unknown"), settings.auth_login_ip_limit)]
    rows = []
    for key, limit in sorted(keys):
        lock_key = int.from_bytes(bytes.fromhex(key[:16]), "big", signed=True)
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
        bucket = db.get(LoginBucket, key, with_for_update=True, populate_existing=True)
        if bucket is None:
            bucket = LoginBucket(key=key, failures=0, expires_at=now + timedelta(seconds=settings.auth_login_window_seconds))
            db.add(bucket)
        elif bucket.expires_at <= now:
            bucket.failures, bucket.expires_at = 0, now + timedelta(seconds=settings.auth_login_window_seconds)
        if bucket.failures >= limit:
            retry = max(1, int((bucket.expires_at - now).total_seconds()) + 1)
            db.rollback()
            raise HTTPException(status_code=429, detail={"code": "LOGIN_RATE_LIMITED", "message": "Demasiados intentos. Intenta más tarde."},
                                headers={"Retry-After": str(retry)})
        rows.append((bucket, limit))
    # Expired rows are technical rate-limit data, not security audit history.
    expired = select(LoginBucket.key).where(LoginBucket.expires_at < now - timedelta(days=1)).limit(100).with_for_update(skip_locked=True)
    db.execute(delete(LoginBucket).where(LoginBucket.key.in_(expired)))
    return rows
