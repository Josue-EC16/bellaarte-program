"""No real SMTP, password reset, or database connection is permitted here."""

from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
import smtplib
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services import email_service as smtp
from app.services import notification_email_service as email
from app.services import notification_job_service as jobs


NOW = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)


@pytest.fixture
def smtp_settings(monkeypatch):
    monkeypatch.setattr(smtp.settings, "smtp_username", "synthetic@example.invalid")
    monkeypatch.setattr(smtp.settings, "smtp_password", "SYNTHETIC_SMTP_PASSWORD")
    monkeypatch.setattr(smtp.settings, "smtp_server", "smtp.invalid")
    monkeypatch.setattr(smtp.settings, "smtp_port", 465)
    # Avoid attachment filesystem dependencies; this is a sender contract test.
    monkeypatch.setattr(smtp.Path, "exists", lambda _path: False)


def send():
    return smtp.send_welcome_email("recipient@example.invalid", "QA SINTETICO", "qa_user", "SYNTHETIC_INITIAL_PASSWORD")


def test_disabled_smtp_is_failure_and_never_prints_credentials(monkeypatch, capsys, caplog):
    monkeypatch.setattr(smtp.settings, "smtp_username", None)
    monkeypatch.setattr(smtp.settings, "smtp_password", None)
    assert send() == (False, "SMTP_NO_CONFIGURADO")
    output = capsys.readouterr()
    combined = output.out + output.err + caplog.text
    assert "SYNTHETIC_INITIAL_PASSWORD" not in combined
    assert "recipient@example.invalid" not in combined


def test_successful_smtp_uses_bounded_timeout_and_does_not_change_credentials(monkeypatch, smtp_settings):
    server = Mock()
    server.__enter__ = Mock(return_value=server)
    server.__exit__ = Mock(return_value=False)
    server.send_message.return_value = {}
    constructor = Mock(return_value=server)
    monkeypatch.setattr(smtp.smtplib, "SMTP_SSL", constructor)
    assert send() == (True, None)
    assert constructor.call_args.kwargs["timeout"] == 10
    server.send_message.assert_called_once()


def test_post_data_disconnect_is_uncertain_and_error_text_is_redacted(monkeypatch, smtp_settings, caplog):
    server = Mock()
    server.__enter__ = Mock(return_value=server)
    server.__exit__ = Mock(return_value=False)
    server.send_message.side_effect = smtplib.SMTPServerDisconnected("DO NOT LOG SYNTHETIC_INITIAL_PASSWORD")
    monkeypatch.setattr(smtp.smtplib, "SMTP_SSL", Mock(return_value=server))
    assert send() == (False, "SMTP_INCIERTO")
    assert "DO NOT LOG" not in caplog.text
    assert "SYNTHETIC_INITIAL_PASSWORD" not in caplog.text


def test_failed_quit_does_not_undo_confirmed_acceptance(monkeypatch, smtp_settings):
    server = Mock()
    server.__enter__ = Mock(return_value=server)
    server.__exit__ = Mock(side_effect=OSError("QUIT failed"))
    server.send_message.return_value = {}
    monkeypatch.setattr(smtp.smtplib, "SMTP_SSL", Mock(return_value=server))
    assert send() == (True, None)


def eligible_account():
    return SimpleNamespace(id=31, is_active=True, must_change_password=True, last_login_at=None,
        password_hash="SYNTHETIC_EXISTING_HASH", username="qa",
        rol=SimpleNamespace(activo=True),
        usuario=SimpleNamespace(activo=True, ci="qa_ci", correo="recipient@example.invalid", nombre_completo="QA"))


@pytest.mark.parametrize("attribute,value", [("must_change_password", False), ("last_login_at", NOW), ("is_active", False)])
def test_email_retry_rejects_changed_or_used_credentials_without_reset(monkeypatch, attribute, value):
    account = eligible_account()
    setattr(account, attribute, value)
    before = account.password_hash
    monkeypatch.setattr(email, "verify_password", Mock(return_value=True))
    assert email.email_retry_eligibility(account)[0] is False
    assert account.password_hash == before


def test_hash_mismatch_requires_explicit_reset_without_mutation(monkeypatch):
    account = eligible_account()
    monkeypatch.setattr(email, "verify_password", Mock(return_value=False))
    assert email.email_retry_eligibility(account) == (False, "RESET_EXPLICITO_REQUERIDO")
    assert account.password_hash == "SYNTHETIC_EXISTING_HASH"


def test_error_notification_contains_only_safe_category(monkeypatch):
    create = Mock()
    monkeypatch.setattr(email, "create_notifications_for_roles", create)
    email.create_email_failure_notification(Mock(), user_id=71, recipient_email="recipient@example.invalid",
                                            error_message="dsn secret SYNTHETIC_INITIAL_PASSWORD")
    payload = create.call_args.kwargs
    assert set(payload["role_codes"]) == {"ADMIN"}
    assert "SMTP_CONFIGURACION" in payload["mensaje"]
    assert "secret" not in payload["mensaje"]
    assert "recipient@example.invalid" not in payload["mensaje"]


class Result:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value

    scalar_one_or_none = scalar_one


@pytest.mark.parametrize("state,attempts,manual,confirm,expected", [
    ("INCIERTO", 1, False, False, "uncertain"),
    ("INCIERTO", 1, True, False, "uncertain"),
    ("FALLIDO", 3, False, False, "blocked"),
    ("BLOQUEADO", 1, False, False, "blocked"),
    ("EN_CURSO", 1, False, False, "skipped"),
])
def test_uncertainty_and_retry_budget_prevent_automatic_resend(monkeypatch, state, attempts, manual, confirm, expected):
    account = eligible_account()
    delivery = SimpleNamespace(estado=state, intentos=attempts, ultimo_intento=NOW,
                               proximo_intento=None, categoria_error="SMTP_CONFIGURACION")
    database = Mock()
    database.execute.side_effect = [Result(None), Result(delivery)]
    monkeypatch.setattr(email, "utc_now", lambda: NOW)
    monkeypatch.setattr(email, "_locked_account", lambda *_args: account)
    monkeypatch.setattr(email, "verify_password", Mock(return_value=True))
    sender = Mock()
    monkeypatch.setattr(email, "send_welcome_email", sender)
    monkeypatch.setattr(email, "create_email_failure_notification", Mock())
    result = email.attempt_credential_email(database, user_id=71, manual=manual, confirm_uncertain=confirm)
    assert result["status"] == expected
    sender.assert_not_called()
    assert account.password_hash == "SYNTHETIC_EXISTING_HASH"


def test_abandoned_attempt_becomes_uncertain_without_resending(monkeypatch):
    account = eligible_account()
    delivery = SimpleNamespace(estado="EN_CURSO", intentos=1, ultimo_intento=NOW - timedelta(minutes=3),
                               proximo_intento=None, categoria_error=None)
    database = Mock()
    database.execute.side_effect = [Result(None), Result(delivery)]
    monkeypatch.setattr(email, "utc_now", lambda: NOW)
    monkeypatch.setattr(email, "_locked_account", lambda *_args: account)
    monkeypatch.setattr(email, "verify_password", Mock(return_value=True))
    sender = Mock()
    monkeypatch.setattr(email, "send_welcome_email", sender)
    failure_notification = Mock()
    monkeypatch.setattr(email, "create_email_failure_notification", failure_notification)
    assert email.attempt_credential_email(database, user_id=71)["status"] == "uncertain"
    assert delivery.estado == "INCIERTO"
    sender.assert_not_called()
    failure_notification.assert_called_once_with(database, user_id=71, error_message="SMTP_INCIERTO")


def test_explicit_manual_retry_can_exceed_automatic_budget_without_reset(monkeypatch):
    account = eligible_account()
    delivery = SimpleNamespace(id=55, estado="FALLIDO", intentos=3, ultimo_intento=NOW - timedelta(hours=1),
                               proximo_intento=None, categoria_error="SMTP_TEMPORAL")
    database = Mock()
    database.execute.side_effect = [Result(None), Result(delivery), Result(delivery)]
    monkeypatch.setattr(email, "utc_now", lambda: NOW)
    monkeypatch.setattr(email, "_locked_account", lambda *_args: account)
    monkeypatch.setattr(email, "verify_password", Mock(return_value=True))
    sender = Mock(return_value=(True, None))
    monkeypatch.setattr(email, "send_welcome_email", sender)
    monkeypatch.setattr(email, "resolve_email_failure_notifications", Mock())
    audit = Mock()
    monkeypatch.setattr(email, "register_audit_event", audit)
    actor = SimpleNamespace(usuario=SimpleNamespace())
    result = email.attempt_credential_email(database, user_id=71, manual=True, requested_by=actor)
    assert result["status"] == "sent"
    assert delivery.intentos == 4 and delivery.estado == "ENVIADO"
    sender.assert_called_once()
    assert account.password_hash == "SYNTHETIC_EXISTING_HASH"
    assert account.must_change_password is True
    audit.assert_called_once()
    assert "QA_CI" not in audit.call_args.kwargs["description"]


def test_daily_job_reports_errors_without_counting_rolled_back_effects(monkeypatch, caplog):
    class Rows:
        def __init__(self, value):
            self.value = value

        def scalars(self):
            return self

        def all(self):
            return self.value

    database = Mock()
    previous = {"created": 900}
    database.info = {"notification_counters": previous}
    database.execute.side_effect = [Rows([1, 2]), *[Rows([]) for _ in range(6)]]
    database.begin_nested.side_effect = lambda: nullcontext()

    def synchronize(_db, *, item_id):
        counters = database.info["notification_counters"]
        if item_id == 1:
            counters["created"] += 1
            raise ValueError("PRIVATE_SYNTHETIC_ERROR")
        counters["unchanged"] += 1

    monkeypatch.setattr(jobs, "sync_boutique_stock_notification", synchronize)
    result = jobs.run_daily_notification_checks(database, today=NOW.date())
    assert result["status"] == "failed"
    assert result["errors"] == 1
    assert result["created"] == 0 and result["unchanged"] == 1
    assert result["boutique_stock_checked"] == 2
    assert database.info["notification_counters"] is previous
    assert "PRIVATE_SYNTHETIC_ERROR" not in caplog.text


def test_job_lock_always_releases_owned_lock_on_failure():
    connection = Mock()
    connection.execute.return_value = Result(True)
    context = Mock()
    context.__enter__ = Mock(return_value=connection)
    context.__exit__ = Mock(return_value=False)
    engine = SimpleNamespace(connect=Mock(return_value=context))
    with pytest.raises(RuntimeError, match="synthetic job failure"):
        with jobs.notification_job_lock(engine, "daily") as acquired:
            assert acquired is True
            raise RuntimeError("synthetic job failure")
    assert "pg_try_advisory_lock" in str(connection.execute.call_args_list[0].args[0])
    assert "pg_advisory_unlock" in str(connection.execute.call_args_list[1].args[0])


def test_job_lock_does_not_unlock_another_owners_lock():
    connection = Mock()
    connection.execute.return_value = Result(False)
    context = Mock()
    context.__enter__ = Mock(return_value=connection)
    context.__exit__ = Mock(return_value=False)
    engine = SimpleNamespace(connect=Mock(return_value=context))
    with jobs.notification_job_lock(engine, "daily") as acquired:
        assert acquired is False
    connection.execute.assert_called_once()
