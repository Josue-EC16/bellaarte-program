"""Session security contracts with no database/network/application startup."""
import asyncio
from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi import HTTPException
from jose import jwt
import pytest
from starlette.requests import Request

from app.core.config import Settings, settings
from app.core.security import (ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE, TokenExpired,
    create_access_token, create_refresh_token, decode_token, hash_password, verify_password)
from app.models.auth_session import AuthSession
from app.services import auth_session_service as sessions


def account(**changes):
    value = SimpleNamespace(id=3, usuario_id=8, auth_version=2, security_version=4, is_active=True,
        must_change_password=False, usuario=SimpleNamespace(activo=True),
        rol=SimpleNamespace(codigo="ADMIN", activo=True))
    value.__dict__.update(changes)
    return value


def state(**changes):
    value = SimpleNamespace(id=uuid4(), cuenta_id=3, auth_version=2, revoked_at=None,
        revocation_reason=None, refresh_hash="", expires_at=datetime.now(timezone.utc) + timedelta(days=1))
    value.__dict__.update(changes)
    return value


def database(session):
    db = Mock()
    db.execute.return_value.scalar_one_or_none.return_value = session
    return db


def payload(session):
    return {"sid": str(session.id), "ver": 2, "sub": "3"}


def request(path="/api/v1/users", headers=()):
    return Request({"type": "http", "method": "GET", "path": path, "headers": list(headers),
                    "client": ("127.0.0.1", 1234), "server": ("localhost", 8000), "scheme": "http"})


def test_tokens_are_bound_to_session_issuer_audience_and_generation():
    sid = str(uuid4())
    token = create_access_token("3", "ADMIN", session_id=sid, auth_version=2)
    claims = decode_token(token, ACCESS_TOKEN_TYPE)
    assert claims["sid"] == sid and claims["ver"] == 2
    assert claims["iss"] == settings.jwt_issuer and claims["aud"] == settings.jwt_audience
    assert claims["jti"]


def test_refresh_and_access_are_not_interchangeable():
    token = create_refresh_token("3", "ADMIN")
    with pytest.raises(ValueError):
        decode_token(token, ACCESS_TOKEN_TYPE)


@pytest.mark.parametrize("change", [{"aud": "another-app"}, {"iss": "another-server"}, {"ver": True}, {"sid": None}])
def test_invalid_claims_rejected(change):
    claims = decode_token(create_access_token("3", "ADMIN"), ACCESS_TOKEN_TYPE)
    claims.update(change)
    token = jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(ValueError):
        decode_token(token, ACCESS_TOKEN_TYPE)


def test_legacy_token_without_session_cannot_authenticate():
    token = jwt.encode({"sub": "3", "type": "access", "exp": datetime.now(timezone.utc) + timedelta(minutes=1)},
                       settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(ValueError):
        decode_token(token, ACCESS_TOKEN_TYPE)


def test_access_cannot_outlive_absolute_session_expiry():
    expiry = datetime.now(timezone.utc) + timedelta(seconds=45)
    claims = decode_token(create_access_token("3", "ADMIN", expires_at=expiry), ACCESS_TOKEN_TYPE)
    assert claims["exp"] == int(expiry.timestamp())


def test_expired_access_identified_for_refresh():
    token = create_access_token("3", "ADMIN", expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    with pytest.raises(TokenExpired):
        decode_token(token, ACCESS_TOKEN_TYPE)


def test_bcrypt_does_not_silently_truncate_utf8():
    with pytest.raises(ValueError):
        hash_password("é" * 37)
    hashed = hash_password("Example123!")
    assert not verify_password("é" * 37, hashed)


def test_session_validation_preserves_current_role_and_records_context():
    item = state()
    actor = account(rol=SimpleNamespace(codigo="CAJA", activo=True))
    assert sessions.validate_session(database(item), actor, payload(item)) is item
    assert actor.rol.codigo == "CAJA" and actor._auth_session_id == item.id


@pytest.mark.parametrize("change,code", [
    ({"revoked_at": datetime.now(timezone.utc)}, "SESSION_REVOKED"),
    ({"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)}, "SESSION_EXPIRED"),
    ({"auth_version": 1}, "SESSION_REVOKED"),
])
def test_invalid_sessions_rejected(change, code):
    item = state(**change)
    with pytest.raises(HTTPException) as error:
        sessions.validate_session(database(item), account(), payload(item))
    assert error.value.status_code == 401 and error.value.detail["code"] == code


@pytest.mark.parametrize("attribute", ["is_active", "usuario", "rol"])
def test_disabled_account_collaborator_or_role_rejected(attribute):
    item = state()
    actor = account()
    if attribute == "is_active":
        actor.is_active = False
    else:
        getattr(actor, attribute).activo = False
    with pytest.raises(HTTPException) as error:
        sessions.validate_session(database(item), actor, payload(item))
    assert error.value.detail["code"] == "ACCOUNT_DISABLED"


def test_missing_session_rejected():
    with pytest.raises(HTTPException) as error:
        sessions.validate_session(database(None), account(), payload(state()))
    assert error.value.detail["code"] == "SESSION_REVOKED"


def test_revoking_account_changes_generations_without_committing():
    actor, db = account(), Mock()
    sessions.revoke_account_sessions(db, actor, "PASSWORD_RESET")
    assert actor.auth_version == 3 and actor.security_version == 5
    db.commit.assert_not_called()
    assert "sesion_cuenta" in str(db.execute.call_args_list[0].args[0])
    assert "pg_notify" in str(db.execute.call_args_list[-1].args[0])


def test_permission_notification_does_not_revoke_sessions():
    actor, db = account(), Mock()
    sessions.notify_account_change(db, actor)
    assert actor.auth_version == 2 and actor.security_version == 5
    db.commit.assert_not_called()
    assert db.execute.call_count == 1


def test_signed_refresh_reuse_revokes_only_its_session(monkeypatch):
    actor, item = account(), state(refresh_hash=sessions.token_digest("already-rotated"))
    db = database(item)
    monkeypatch.setattr(sessions, "lock_account", lambda *_: actor)
    monkeypatch.setattr("app.core.audit.register_audit_event", Mock())
    with pytest.raises(HTTPException) as error:
        sessions.rotate_session(db, actor, payload(item), "old-token")
    assert error.value.detail["code"] == "SESSION_REVOKED"
    assert item.revocation_reason == "REFRESH_REUSE" and actor.auth_version == 2
    db.commit.assert_called_once()


def test_refresh_rotates_digest_and_preserves_absolute_expiry(monkeypatch):
    actor, item = account(), state(refresh_hash=sessions.token_digest("valid-token"))
    db = database(item)
    monkeypatch.setattr(sessions, "lock_account", lambda *_: actor)
    monkeypatch.setattr("app.services.user_service.build_user_summary", lambda *_: {"id": 3})
    result = sessions.rotate_session(db, actor, payload(item), "valid-token")
    claims = decode_token(result["refresh_token"], REFRESH_TOKEN_TYPE)
    assert claims["exp"] == int(item.expires_at.timestamp())
    assert item.refresh_hash == sessions.token_digest(result["refresh_token"])
    assert result["refresh_token"] != "valid-token"
    db.commit.assert_called_once()


def test_current_account_uses_durable_session_and_forces_password_change(monkeypatch):
    from app.deps import auth
    actor = account(must_change_password=True)
    item = state()
    token = create_access_token("3", "ADMIN", session_id=str(item.id), auth_version=2)
    monkeypatch.setattr(auth, "get_account_by_id", lambda *_: actor)
    with pytest.raises(HTTPException) as error:
        auth.get_current_account(request(), authorization=f"Bearer {token}", db=database(item))
    assert error.value.detail["code"] == "PASSWORD_CHANGE_REQUIRED"
    assert auth.get_current_account(request("/api/v1/auth/change-password"), authorization=f"Bearer {token}", db=database(item)) is actor


def test_user_admin_policy_cannot_be_granted_to_other_role(monkeypatch):
    from app.deps import auth
    actor = account(rol=SimpleNamespace(codigo="CAJA", activo=True))
    enforcer = Mock()
    enforcer.enforce.return_value = True
    monkeypatch.setattr(auth, "register_audit_failure", Mock())
    with pytest.raises(HTTPException) as error:
        auth.require_permission("users:list")(request(), database(None), actor, enforcer)
    assert error.value.status_code == 403


def test_production_rejects_development_secrets():
    with pytest.raises(ValueError):
        Settings(_env_file=None, environment="production", frontend_url="https://erp.example",
                 jwt_secret_key="bellaarte-dev-access-secret", jwt_refresh_secret_key="bellaarte-dev-refresh-secret")


def test_untrusted_origin_rejected_and_native_client_supported():
    from app.api.routers.auth import require_trusted_origin
    with pytest.raises(HTTPException) as error:
        require_trusted_origin(request(headers=[(b"origin", b"https://attacker.example")]))
    assert error.value.status_code == 403
    require_trusted_origin(request())


def test_cookie_uses_configured_lifetime_and_security(monkeypatch):
    from app.api.routers import auth
    response = Mock()
    monkeypatch.setattr(auth, "settings", SimpleNamespace(is_production=True, refresh_token_days=2))
    auth._set_refresh_cookie(response, "not-a-real-token")
    fields = response.set_cookie.call_args.kwargs
    assert fields["httponly"] is True and fields["secure"] is True
    assert fields["max_age"] == 2 * 86400


def test_event_stream_revokes_without_retaining_request_database(monkeypatch):
    from app.services import auth_events
    monkeypatch.setattr(auth_events, "broker", SimpleNamespace(subscribe=Mock(), unsubscribe=Mock(), revision=lambda _: 0))
    monkeypatch.setattr(auth_events, "session_snapshot", Mock(side_effect=sessions.auth_error()))
    async def run():
        stream = auth_events.session_events(SimpleNamespace(is_disconnected=AsyncMock(return_value=False)), 3,
                                           {"exp": datetime.now(timezone.utc).timestamp() + 60})
        event = json.loads(await anext(stream))
        await stream.aclose()
        return event
    assert asyncio.run(run())["type"] == "revoked"
    auth_events.broker.unsubscribe.assert_called_once()


def test_rate_keys_do_not_expose_identity_and_normalize_username():
    assert sessions._rate_key("pair", " Test ", "127.0.0.1") == sessions._rate_key("pair", "test", "127.0.0.1")
    assert len(sessions._rate_key("pair", "sensitive-user", "127.0.0.1")) == 64


def test_session_model_has_no_plaintext_token_column():
    assert set(AuthSession.__table__.columns.keys()) == {
        "id", "cuenta_id", "auth_version", "refresh_hash", "created_at", "expires_at", "revoked_at", "revocation_reason",
    }


def test_auth_validation_does_not_echo_password_input():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.routers import auth
    from app.core.database import get_db
    application = FastAPI()
    application.include_router(auth.router, prefix="/api/v1/auth")
    application.dependency_overrides[get_db] = lambda: Mock()
    response = TestClient(application).post("/api/v1/auth/login", json={"username": "test", "password": "secret"})
    assert response.status_code == 422
    assert "secret" not in response.text and '"input"' not in response.text
    assert response.json()["detail"][0]["loc"] == ["body", "password"]


def test_rate_limit_rejects_before_account_query_and_returns_retry_after():
    from app.models.auth_session import LoginBucket
    db = Mock()
    db.get.return_value = LoginBucket(key="a" * 64, failures=100,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=90))
    with pytest.raises(HTTPException) as error:
        sessions.lock_login_buckets(db, "test", "127.0.0.1")
    assert error.value.status_code == 429
    assert 1 <= int(error.value.headers["Retry-After"]) <= 91
    db.rollback.assert_called_once()


def test_expired_rate_window_reopens_without_permanent_account_lock():
    from app.models.auth_session import LoginBucket
    db = Mock()
    bucket = LoginBucket(key="a" * 64, failures=100,
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    db.get.return_value = bucket
    rows = sessions.lock_login_buckets(db, "test", "127.0.0.1")
    assert len(rows) == 2 and bucket.failures == 0
    assert bucket.expires_at > datetime.now(timezone.utc)


def test_event_stream_updates_permissions_without_logout(monkeypatch):
    from app.services import auth_events
    fake_broker = SimpleNamespace(subscribe=Mock(), unsubscribe=Mock(), revision=lambda _: 0)
    monkeypatch.setattr(auth_events, "broker", fake_broker)
    monkeypatch.setattr(auth_events, "session_snapshot", lambda *_: {"type": "session", "version": 9,
        "user": {"id": 3, "role_code": "CAJA", "permissions": ["dashboard:view"]}})
    async def run():
        stream = auth_events.session_events(SimpleNamespace(is_disconnected=AsyncMock(return_value=False)), 3,
                                           {"exp": datetime.now(timezone.utc).timestamp() + 60})
        value = json.loads(await anext(stream))
        await stream.aclose()
        return value
    assert asyncio.run(run())["user"]["role_code"] == "CAJA"
    fake_broker.unsubscribe.assert_called_once()
