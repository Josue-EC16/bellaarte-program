"""SMTP is replaced; delivery/account locks and durable state use PostgreSQL."""

from sqlalchemy import text
from sqlalchemy.orm import Session


def test_email_failure_is_durable_and_releases_target_lock_before_admin_publication(pg_cluster, synthetic_recipient, monkeypatch):
    from app.services import notification_email_service as email

    monkeypatch.setattr(email, "verify_password", lambda *_args: True)
    monkeypatch.setattr(email, "send_welcome_email", lambda **_kwargs: (False, "SMTP_NO_CONFIGURADO"))
    publications = []

    def publish(_session, *, user_id, error_message):
        with pg_cluster.engine.begin() as observer:
            # NOWAIT makes a lock inversion fail deterministically, without a
            # timing assertion or any actual SMTP effect.
            observer.execute(text("SELECT id FROM cuentas WHERE id=:id FOR UPDATE NOWAIT"),
                             {"id": synthetic_recipient.account_id})
            state = observer.execute(text("SELECT estado FROM envio_notificacion_correo WHERE cuenta_id=:id"),
                                     {"id": synthetic_recipient.account_id}).scalar_one()
            assert state == "BLOQUEADO"
        publications.append((user_id, error_message))

    monkeypatch.setattr(email, "create_email_failure_notification", publish)
    with Session(pg_cluster.engine) as session:
        assert email.attempt_credential_email(session, user_id=synthetic_recipient.user_id) == {
            "status": "failed", "category": "SMTP_NO_CONFIGURADO"}
        assert email.attempt_credential_email(session, user_id=synthetic_recipient.user_id) == {
            "status": "blocked", "category": "SMTP_NO_CONFIGURADO"}
    assert publications == [(synthetic_recipient.user_id, "SMTP_NO_CONFIGURADO")] * 2
