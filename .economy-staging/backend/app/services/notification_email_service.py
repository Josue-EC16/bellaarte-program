"""Credential email attempts, coordinated per account/destination, without resets.

Only call the sender after the surrounding business transaction has committed.
SMTP is not transactional: an abandoned attempt remains uncertain, never queued
automatically as if delivery had certainly failed.
"""

from datetime import timedelta
import logging
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, joinedload

from app.core.audit import register_audit_event
from app.core.notification_catalog import recipient_roles, utc_now
from app.core.security import verify_password
from app.models.account import Cuenta
from app.models.boutique_enums import PrioridadNotificacionEnum
from app.models.notification import EnvioNotificacionCorreo, Notificacion
from app.models.user import Usuario
from app.services.email_service import send_welcome_email
from app.services.notification_query_service import get_notification_detail
from app.services.notification_sync_service import create_notifications_for_roles, resolve_notifications_by_reference


logger = logging.getLogger(__name__)
SAFE_EMAIL_CATEGORIES = frozenset({
    "SMTP_NO_CONFIGURADO", "SMTP_AUTENTICACION", "SMTP_RECHAZADO", "SMTP_TEMPORAL",
    "SMTP_INCIERTO", "SMTP_CONFIGURACION", "CUENTA_NO_ELEGIBLE", "RESET_EXPLICITO_REQUERIDO", "DESTINO_CAMBIADO",
    "PRESUPUESTO_AGOTADO",
})


def email_retry_eligibility(account: Cuenta) -> tuple[bool, str | None]:
    if not account.is_active or not account.usuario.activo or not account.rol.activo:
        return False, "CUENTA_NO_ELEGIBLE"
    if not account.must_change_password or account.last_login_at is not None:
        return False, "RESET_EXPLICITO_REQUERIDO"
    try:
        matches = verify_password(account.usuario.ci.upper(), account.password_hash)
    except (ValueError, TypeError):
        matches = False
    return (True, None) if matches else (False, "RESET_EXPLICITO_REQUERIDO")


def _locked_account(db: Session, user_id: int) -> Cuenta | None:
    # User -> account is the shared write order with user_service. Holding both
    # rows through the bounded SMTP call prevents sending stale credentials.
    user = db.execute(select(Usuario).where(Usuario.id == user_id).with_for_update()
                      .execution_options(populate_existing=True)).scalar_one_or_none()
    if user is None:
        return None
    account = db.execute(select(Cuenta).options(joinedload(Cuenta.rol)).where(Cuenta.usuario_id == user_id)
                         .with_for_update(of=Cuenta).execution_options(populate_existing=True)).scalar_one_or_none()
    if account is not None:
        account.usuario = user
    return account


def create_email_failure_notification(db: Session, *, user_id: int, recipient_email: str = "", error_message: str) -> None:
    category = error_message if error_message in SAFE_EMAIL_CATEGORIES else "SMTP_CONFIGURACION"
    create_notifications_for_roles(db, role_codes=recipient_roles("ERROR_ENVIO_CORREO"), tipo="ERROR_ENVIO_CORREO",
        prioridad=PrioridadNotificacionEnum.URGENTE, titulo="ERROR AL ENVIAR CREDENCIALES",
        mensaje=f"NO SE CONFIRMÓ EL ENVÍO DE BIENVENIDA PARA EL USUARIO #{user_id}. CATEGORÍA: {category}. REVISE EL ESTADO ANTES DE REINTENTAR.",
        modulo="SEGURIDAD", tabla_referencia="USUARIOS", id_referencia=user_id)


def resolve_email_failure_notifications(db: Session, *, user_id: int) -> None:
    resolve_notifications_by_reference(db, notification_types=("ERROR_ENVIO_CORREO",),
                                       tabla_referencia="USUARIOS", id_referencia=user_id, reason="ENVIO_CONFIRMADO")


def queue_welcome_email(db: Session, *, account: Cuenta) -> None:
    """Persist intent with the account transaction; never store its credential."""
    db.execute(insert(EnvioNotificacionCorreo).values(
        cuenta_id=account.id, destino=account.usuario.correo.strip().lower(),
        estado="FALLIDO", intentos=0, proximo_intento=utc_now(),
    ).on_conflict_do_nothing(index_elements=[EnvioNotificacionCorreo.cuenta_id, EnvioNotificacionCorreo.destino]))


def attempt_credential_email(db: Session, *, user_id: int, manual: bool = False,
                             confirm_uncertain: bool = False, requested_by: Cuenta | None = None,
                             ip_address: str | None = None, user_agent: str | None = None) -> dict[str, str]:
    account = _locked_account(db, user_id)
    if account is None:
        db.rollback()
        return {"status": "blocked", "category": "CUENTA_NO_ELEGIBLE"}
    destination = account.usuario.correo.strip().lower()
    db.execute(insert(EnvioNotificacionCorreo).values(
        cuenta_id=account.id, destino=destination, estado="FALLIDO", intentos=0,
    ).on_conflict_do_nothing(index_elements=[EnvioNotificacionCorreo.cuenta_id, EnvioNotificacionCorreo.destino]))
    delivery = db.execute(select(EnvioNotificacionCorreo).where(
        EnvioNotificacionCorreo.cuenta_id == account.id, EnvioNotificacionCorreo.destino == destination,
    ).with_for_update().execution_options(populate_existing=True)).scalar_one()
    now = utc_now()

    def publish_failure(status: str, category: str) -> dict[str, str]:
        # Persist delivery state and release its user/account locks before
        # acquiring ADMIN recipient locks. Reconciliation can hold the ADMIN
        # row while waiting for this target account, so nesting them deadlocks.
        db.commit()
        create_email_failure_notification(db, user_id=user_id, error_message=category)
        db.commit()
        return {"status": status, "category": category}

    if delivery.estado == "ENVIADO":
        resolve_email_failure_notifications(db, user_id=user_id)
        db.commit()
        return {"status": "already_sent", "category": "ENVIO_CONFIRMADO"}
    if delivery.estado == "EN_CURSO":
        if delivery.ultimo_intento and delivery.ultimo_intento > now - timedelta(minutes=2):
            db.rollback()
            return {"status": "skipped", "category": "ENVIO_EN_CURSO"}
        delivery.estado, delivery.categoria_error = "INCIERTO", "SMTP_INCIERTO"
        delivery.fecha_resultado = now
    if delivery.estado == "INCIERTO" and not (manual and confirm_uncertain):
        return publish_failure("uncertain", "SMTP_INCIERTO")
    eligible, category = email_retry_eligibility(account)
    if not eligible:
        delivery.estado, delivery.categoria_error, delivery.fecha_resultado = "BLOQUEADO", category, now
        return publish_failure("blocked", category)
    if delivery.intentos >= 3 and not manual:
        return publish_failure("blocked", "PRESUPUESTO_AGOTADO")
    if delivery.estado == "BLOQUEADO" and not manual:
        return publish_failure("blocked", delivery.categoria_error or "SMTP_CONFIGURACION")
    if delivery.proximo_intento and delivery.proximo_intento > now:
        db.commit()
        return {"status": "skipped", "category": "ESPERA_REINTENTO"}
    attempt_id = str(uuid4())
    delivery_id = delivery.id
    delivery.estado, delivery.intento_id = "EN_CURSO", attempt_id
    delivery.intentos += 1
    delivery.ultimo_intento, delivery.proximo_intento, delivery.fecha_resultado, delivery.categoria_error = now, None, None, None
    db.commit()  # Durable intent before the external side effect.

    try:
        account = _locked_account(db, user_id)
        delivery = db.execute(select(EnvioNotificacionCorreo).where(
            EnvioNotificacionCorreo.id == delivery_id, EnvioNotificacionCorreo.intento_id == attempt_id,
        ).with_for_update().execution_options(populate_existing=True)).scalar_one()
        eligible, category = email_retry_eligibility(account) if account else (False, "CUENTA_NO_ELEGIBLE")
        if eligible and account.usuario.correo.strip().lower() != destination:
            eligible, category = False, "DESTINO_CAMBIADO"
        if eligible:
            success, category = send_welcome_email(recipient_email=destination, full_name=account.usuario.nombre_completo,
                username=account.username, initial_password=account.usuario.ci.upper())
        else:
            success = False
        now = utc_now()
        if success:
            delivery.estado, delivery.categoria_error = "ENVIADO", None
            resolve_email_failure_notifications(db, user_id=user_id)
        else:
            category = category if category in SAFE_EMAIL_CATEGORIES else "SMTP_CONFIGURACION"
            delivery.categoria_error = category
            delivery.estado = "INCIERTO" if category == "SMTP_INCIERTO" else "FALLIDO" if category == "SMTP_TEMPORAL" else "BLOQUEADO"
            if delivery.estado == "FALLIDO" and delivery.intentos < 3:
                delivery.proximo_intento = now + timedelta(minutes=5 if delivery.intentos == 1 else 30)
        delivery.fecha_resultado = now
        if requested_by is not None:
            register_audit_event(db, action="NOTIFICATION_EMAIL_RETRIED",
                description=f"Intento de bienvenida #{delivery.intentos}: {delivery.estado}. No se modificaron credenciales.",
                account=requested_by, user=requested_by.usuario, reference=str(delivery.id),
                ip_address=ip_address, user_agent=user_agent)
        result = {"status": "sent" if success else "uncertain" if delivery.estado == "INCIERTO" else "failed", "category": category or "ENVIO_CONFIRMADO"}
        db.commit()
        if not success:
            create_email_failure_notification(db, user_id=user_id, error_message=category)
            db.commit()
        return result
    except Exception:
        # The pre-send intent survives rollback. A later run treats abandoned
        # EN_CURSO as uncertain, never as permission to send automatically again.
        db.rollback()
        logger.error("SMTP_RESULTADO_NO_CONFIRMADO")
        return {"status": "uncertain", "category": "SMTP_INCIERTO"}


def send_welcome_email_with_tracking(*, user_id: int, **_legacy_context) -> None:
    from app.core.database import SessionLocal

    with SessionLocal() as db:
        attempt_credential_email(db, user_id=user_id)


def retry_email_notification(db: Session, *, notification_id: int, retried_by: Cuenta,
    ip_address: str | None, user_agent: str | None, confirm_uncertain: bool = False):
    notification = db.execute(select(Notificacion).where(Notificacion.id == notification_id)).scalar_one_or_none()
    if notification is None:
        raise HTTPException(status_code=404, detail="Notificación no encontrada.")
    if notification.tipo != "ERROR_ENVIO_CORREO" or notification.tabla_referencia != "USUARIOS" or notification.id_referencia is None:
        raise HTTPException(status_code=409, detail="La notificación no corresponde a un envío de bienvenida.")
    result = attempt_credential_email(db, user_id=notification.id_referencia, manual=True,
        confirm_uncertain=confirm_uncertain, requested_by=retried_by, ip_address=ip_address, user_agent=user_agent)
    if result["status"] not in {"sent", "already_sent"}:
        raise HTTPException(status_code=409, detail=f"No se confirmó el reenvío ({result['category']}). Si la credencial ya cambió, utiliza el restablecimiento explícito.")
    return get_notification_detail(db, notification_id=notification_id, account=retried_by, supervision=True)
