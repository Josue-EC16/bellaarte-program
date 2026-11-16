from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.audit import register_audit_event, register_audit_failure
from app.core.security import hash_password, verify_password, pwd_context
from app.models.account import Cuenta
from app.services.auth_session_service import (create_session, lock_account, lock_login_buckets,
    revoke_account_sessions, revoke_session, validate_session)


def get_account_by_username(db: Session, username: str) -> Cuenta | None:
    stmt = (
        select(Cuenta)
        .where(Cuenta.username == username.strip())
        .options(joinedload(Cuenta.usuario), joinedload(Cuenta.rol))
    )
    return db.execute(stmt.execution_options(populate_existing=True)).scalar_one_or_none()


def get_account_by_id(db: Session, account_id: int) -> Cuenta | None:
    stmt = (
        select(Cuenta)
        .where(Cuenta.id == account_id)
        .options(joinedload(Cuenta.usuario), joinedload(Cuenta.rol))
    )
    return db.execute(stmt.execution_options(populate_existing=True)).scalar_one_or_none()


def validate_active_account(account: Cuenta) -> None:
    if not account.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="La cuenta esta deshabilitada.")
    if not account.usuario.activo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="El usuario esta deshabilitado.")
    if not account.rol.activo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="El rol asignado esta deshabilitado.")


def authenticate(db: Session, username: str, password: str, *, ip_address: str | None, user_agent: str | None) -> Cuenta:
    buckets = lock_login_buckets(db, username, ip_address)
    account = get_account_by_username(db, username)
    if account is not None:
        lock_account(db, account)
    valid = verify_password(password, account.password_hash) if account is not None else False
    if account is None:
        pwd_context.dummy_verify()
    if not valid:
        for bucket, _limit in buckets:
            bucket.failures += 1
        register_audit_event(
            db,
            action="LOGIN_FAILED",
            description="Intento de inicio de sesion fallido.",
            reference=username,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales invalidas.")

    validate_active_account(account)
    account.last_login_at = datetime.now(timezone.utc)
    register_audit_event(
        db,
        action="LOGIN_SUCCESS",
        description="Inicio de sesion exitoso.",
        account=account,
        user=account.usuario,
        reference=account.username,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    account._login_payload = create_session(db, account)
    db.commit()
    return account


def build_login_payload(account: Cuenta) -> dict:
    # Issuance occurs inside authenticate's transaction, before releasing locks.
    return account._login_payload


def change_password(
    db: Session,
    *,
    account: Cuenta,
    current_password: str,
    new_password: str,
    ip_address: str | None,
    user_agent: str | None,
) -> Cuenta:
    lock_account(db, account)
    validate_session(db, account, account._auth_payload, lock=True)
    if not verify_password(current_password, account.password_hash):
        register_audit_failure(
            db,
            action="PASSWORD_CHANGE_FAILED",
            description="Intento fallido de cambio de contrasena por contrasena actual invalida.",
            account=account,
            user=account.usuario,
            reference=account.username,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La contrasena actual no es valida.")
    if current_password == new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La nueva contrasena no puede ser igual a la actual.")

    account.password_hash = hash_password(new_password)
    account.must_change_password = False
    revoke_account_sessions(db, account, "PASSWORD_CHANGED")
    register_audit_event(
        db,
        action="PASSWORD_CHANGED",
        description="La cuenta cambio su contrasena.",
        account=account,
        user=account.usuario,
        reference=account.username,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(account)
    return account


def logout(
    db: Session,
    *,
    account: Cuenta,
    ip_address: str | None,
    user_agent: str | None,
) -> None:
    lock_account(db, account)
    session = validate_session(db, account, account._auth_payload, lock=True)
    revoke_session(db, session, "LOGOUT")
    register_audit_event(
        db,
        action="LOGOUT",
        description="Cierre de sesion exitoso.",
        account=account,
        user=account.usuario,
        reference=account.username,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
