"""Account/session invariants on the manifest-validated PostgreSQL test cluster.

Sequential cases use an outer rollback, even when the service commits. No
application lifespan, SMTP, business configuration or existing accounts are used.
"""
from concurrent.futures import ThreadPoolExecutor
import asyncio
import json
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import casbin
import pytest
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def _setup(db):
    from app.core.security import hash_password
    from app.models.account import Cuenta
    from app.models.role import Rol
    from app.models.user import Usuario
    token = uuid4().hex[:16]
    roles = {}
    for code in ("ADMIN", "CAJA", "MODISTA"):
        role = db.scalar(select(Rol).where(Rol.codigo == code))
        if role is None:
            role = Rol(codigo=code, nombre="QA_USER_ROLE_" + code, activo=True)
            db.add(role)
            db.flush()
        roles[code] = role
    actors = []
    password_hash = hash_password("Temporal123!")
    for index, role_code in enumerate(("ADMIN", "ADMIN", "CAJA")):
        person = Usuario(nombres="ANA", apellido_paterno="PEREZ", ci=str(uuid4().int)[:20],
            celular="70000000", correo=f"{token}{index}@example.com", zona="SOLO TEST", activo=True)
        db.add(person)
        db.flush()
        account = Cuenta(usuario_id=person.id, rol_id=roles[role_code].id,
            username=f"QA_USER_{token}_{index}", password_hash=password_hash,
            must_change_password=False, is_active=True)
        db.add(account)
        actors.append(account)
    db.flush()
    db.commit()
    return SimpleNamespace(db=db, admin=actors[0], peer=actors[1], cashier=actors[2], roles=roles)


@pytest.fixture
def users(pg_cluster):
    with pg_cluster.engine.connect() as connection:
        pg_cluster.assert_identity(connection, pg_cluster.manifest)
        connection.rollback()
        transaction = connection.begin()
        db = Session(connection, autoflush=False, join_transaction_mode="create_savepoint", expire_on_commit=False)
        try:
            yield _setup(db)
        finally:
            db.close()
            transaction.rollback()


@pytest.fixture
def users_api(users):
    from app.api.routers.auth import router as auth_router
    from app.api.routers.users import router as users_router
    from app.api.routers.roles import router as roles_router
    from app.core.database import get_db
    from app.deps.auth import get_enforcer
    from app.services.auth_session_service import create_session
    security = Path(__file__).resolve().parents[2] / "app/security"
    enforcer = casbin.Enforcer(str(security / "model.conf"), str(security / "policy.csv"))
    app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1/auth")
    app.include_router(users_router, prefix="/api/v1/users")
    app.include_router(roles_router, prefix="/api/v1/roles")
    def database():
        yield users.db
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_enforcer] = lambda: enforcer
    def headers(account):
        payload = create_session(users.db, account)
        users.db.commit()
        return {"Authorization": "Bearer " + payload["access_token"]}, payload
    with TestClient(app) as client:
        yield client, headers


def _edit(account, role_code=None, **changes):
    from app.schemas.auth import UpdateUserRequest
    values = dict(nombres=account.usuario.nombres, apellido_paterno=account.usuario.apellido_paterno,
        apellido_materno=account.usuario.apellido_materno, ci=account.usuario.ci,
        celular=account.usuario.celular, correo=account.usuario.correo, zona=account.usuario.zona,
        direccion=account.usuario.direccion, role_code=role_code or account.rol.codigo,
        user_is_active=account.usuario.activo, account_is_active=account.is_active)
    values.update(changes)
    return UpdateUserRequest(**values)


def test_database_rejects_a_second_account_for_the_same_collaborator(users):
    from app.models.account import Cuenta
    with pytest.raises(IntegrityError):
        with users.db.begin_nested():
            users.db.add(Cuenta(usuario_id=users.cashier.usuario_id, rol_id=users.cashier.rol_id,
                username="QA_SECOND_" + uuid4().hex, password_hash="NOT_A_REAL_HASH"))
            users.db.flush()


@pytest.mark.parametrize("operation", ["status", "user_flag", "account_flag", "role"])
def test_admin_cannot_disable_or_demote_self_by_any_public_write(users, users_api, operation):
    client, headers = users_api
    auth, _ = headers(users.admin)
    if operation == "status":
        result = client.patch(f"/api/v1/users/{users.admin.id}/status", json={"is_active": False}, headers=auth)
    else:
        changes = {"user_is_active": False} if operation == "user_flag" else {"account_is_active": False} if operation == "account_flag" else {"role_code": "CAJA"}
        result = client.patch(f"/api/v1/users/{users.admin.id}", json=_edit(users.admin, **changes).model_dump(), headers=auth)
    assert result.status_code == 409, result.text
    users.db.rollback()
    users.db.refresh(users.admin)
    assert users.admin.is_active and users.admin.usuario.activo and users.admin.rol.codigo == "ADMIN"


def test_role_change_updates_backend_permissions_with_the_same_access_token(users, users_api):
    client, headers = users_api
    peer_auth, _ = headers(users.peer)
    assert client.get("/api/v1/users", headers=peer_auth).status_code == 200
    admin_auth, _ = headers(users.admin)
    result = client.patch(f"/api/v1/users/{users.peer.id}", json=_edit(users.peer, "CAJA").model_dump(), headers=admin_auth)
    assert result.status_code == 200, result.text
    me = client.get("/api/v1/auth/me", headers=peer_auth)
    assert me.status_code == 200 and me.json()["user"]["role_code"] == "CAJA"
    assert "users:list" not in me.json()["user"]["permissions"]
    assert client.get("/api/v1/users", headers=peer_auth).status_code == 403
    assert client.get("/api/v1/roles", headers=peer_auth).status_code == 403


def test_disabled_and_reactivated_account_cannot_reuse_its_old_tokens(users, users_api):
    client, headers = users_api
    target_auth, old = headers(users.cashier)
    admin_auth, _ = headers(users.admin)
    assert client.patch(f"/api/v1/users/{users.cashier.id}/status", json={"is_active": False}, headers=admin_auth).status_code == 200
    assert client.get("/api/v1/auth/me", headers=target_auth).status_code == 401
    assert client.patch(f"/api/v1/users/{users.cashier.id}/status", json={"is_active": True}, headers=admin_auth).status_code == 200
    assert client.get("/api/v1/auth/me", headers=target_auth).status_code == 401
    from app.core.security import REFRESH_COOKIE_NAME
    client.cookies.set(REFRESH_COOKIE_NAME, old["refresh_token"])
    assert client.post("/api/v1/auth/refresh").status_code == 401


@pytest.mark.parametrize("target_name", ["admin", "peer", "cashier"])
def test_reset_including_self_revokes_every_session_and_generates_initials_ci(users, users_api, target_name):
    from app.core.security import verify_password
    client, headers = users_api
    target = getattr(users, target_name)
    target_auth, _ = headers(target)
    other_auth, _ = headers(target)
    admin_auth, _ = headers(users.admin)
    response = client.post(f"/api/v1/users/{target.id}/reset-password", json={}, headers=admin_auth)
    assert response.status_code == 200, response.text
    users.db.refresh(target)
    assert verify_password("AP" + target.usuario.ci, target.password_hash)
    assert target.must_change_password
    for auth in (target_auth, other_auth):
        assert client.get("/api/v1/auth/me", headers=auth).status_code == 401


def test_temporary_account_can_only_read_session_change_password_or_leave(users, users_api):
    client, headers = users_api
    users.admin.must_change_password = True
    users.db.commit()
    auth, _ = headers(users.admin)
    assert client.get("/api/v1/auth/me", headers=auth).status_code == 200
    rejected = client.get("/api/v1/users", headers=auth)
    assert rejected.status_code == 403 and rejected.json()["detail"]["code"] == "PASSWORD_CHANGE_REQUIRED"
    result = client.post("/api/v1/auth/change-password", headers=auth,
        json={"current_password": "Temporal123!", "new_password": "NuevaClave456!"})
    assert result.status_code == 200, result.text
    assert client.get("/api/v1/auth/me", headers=auth).status_code == 401


def test_refresh_rotation_detects_reuse_and_revokes_its_family(users, users_api):
    from app.core.security import REFRESH_COOKIE_NAME
    client, headers = users_api
    auth, old = headers(users.cashier)
    client.cookies.set(REFRESH_COOKIE_NAME, old["refresh_token"])
    refreshed = client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200, refreshed.text
    new_auth = {"Authorization": "Bearer " + refreshed.json()["access_token"]}
    assert client.get("/api/v1/auth/me", headers=new_auth).status_code == 200
    client.cookies.clear()
    client.cookies.set(REFRESH_COOKIE_NAME, old["refresh_token"])
    assert client.post("/api/v1/auth/refresh").status_code == 401
    assert client.get("/api/v1/auth/me", headers=new_auth).status_code == 401
    assert client.get("/api/v1/auth/me", headers=auth).status_code == 401


def test_login_logout_and_cookie_logout_are_durable_and_idempotent(users, users_api):
    from app.core.security import REFRESH_COOKIE_NAME
    client, _headers = users_api
    response = client.post("/api/v1/auth/login", json={"username": users.cashier.username, "password": "Temporal123!"})
    assert response.status_code == 200, response.text
    auth = {"Authorization": "Bearer " + response.json()["access_token"]}
    old_refresh = client.cookies.get(REFRESH_COOKIE_NAME)
    # Cookie-only logout also covers an expired/missing access JWT.
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/me", headers=auth).status_code == 401
    assert client.post("/api/v1/auth/logout").status_code == 204
    client.cookies.set(REFRESH_COOKIE_NAME, old_refresh)
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_login_budget_blocks_repeated_failures_with_retry_after(users, users_api):
    client, _headers = users_api
    for _ in range(5):
        assert client.post("/api/v1/auth/login", json={"username": users.cashier.username, "password": "Incorrecta123!"}).status_code == 401
    result = client.post("/api/v1/auth/login", json={"username": users.cashier.username, "password": "Temporal123!"})
    assert result.status_code == 429 and int(result.headers["Retry-After"]) > 0


def test_create_user_uses_initials_ci_and_queues_only_the_matching_credential(users):
    from app.core.security import verify_password
    from app.schemas.auth import CreateUserRequest
    from app.services.user_service import create_user
    from app.services.notification_email_service import _verified_temporary_credential
    ci = str(uuid4().int)[:20]
    created = create_user(users.db,
        payload=CreateUserRequest(nombres="  María   José ", apellido_paterno=" Pérez ",
            ci=ci, celular="70000000", correo=ci + "@example.com", zona="TEST", role_code="CAJA"),
        created_by=users.admin, background_tasks=BackgroundTasks(), ip_address=None, user_agent="QA_USER_CREATE")
    expected = "MP" + ci
    assert created.username == expected and created.must_change_password
    assert verify_password(expected, created.password_hash)
    assert _verified_temporary_credential(created) == expected


def test_committed_events_update_role_then_revoke_the_same_browser_session(pg_cluster, monkeypatch):
    from unittest.mock import AsyncMock
    from sqlalchemy.orm import sessionmaker
    from app.core import database
    from app.core.security import ACCESS_TOKEN_TYPE, decode_token
    from app.services import auth_events
    from app.services.auth_session_service import create_session
    from app.services.user_service import update_user, set_account_status
    # Owned committed test identities allow the listener/snapshot independent
    # sessions to observe real commits. They remain only in the test cluster.
    with Session(pg_cluster.engine, expire_on_commit=False) as db:
        state = _setup(db)
        login = create_session(db, state.peer)
        db.commit()
        peer_id, admin_id = state.peer.id, state.admin.id
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(pg_cluster.engine))
    monkeypatch.setattr(database, "engine", pg_cluster.engine)
    payload = decode_token(login["access_token"], ACCESS_TOKEN_TYPE)
    async def run():
        stream = auth_events.session_events(SimpleNamespace(is_disconnected=AsyncMock(return_value=False)), peer_id, payload)
        try:
            first = json.loads(await asyncio.wait_for(anext(stream), 7))
            assert first["type"] == "session" and first["user"]["role_code"] == "ADMIN"
            with Session(pg_cluster.engine, autoflush=False) as db:
                from app.models.account import Cuenta
                peer, admin = db.get(Cuenta, peer_id), db.get(Cuenta, admin_id)
                update_user(db, account_id=peer_id, payload=_edit(peer, "CAJA"), updated_by=admin,
                    background_tasks=BackgroundTasks(), ip_address=None, user_agent="QA_USER_EVENTS")
            updated = json.loads(await asyncio.wait_for(anext(stream), 7))
            assert updated["type"] == "session" and updated["user"]["role_code"] == "CAJA"
            assert "users:list" not in updated["user"]["permissions"]
            with Session(pg_cluster.engine) as db:
                from app.models.account import Cuenta
                set_account_status(db, account_id=peer_id, is_active=False, changed_by=db.get(Cuenta, admin_id),
                    ip_address=None, user_agent="QA_USER_EVENTS")
            ended = json.loads(await asyncio.wait_for(anext(stream), 7))
            assert ended["type"] == "revoked"
        finally:
            await stream.aclose()
    asyncio.run(run())
    # Allow the shared LISTEN connection to release before stopping test PG.
    if auth_events.broker.thread:
        auth_events.broker.thread.join(timeout=4)


def test_failed_creation_rolls_back_account_and_person(users, monkeypatch):
    from app.models.account import Cuenta
    from app.models.user import Usuario
    from app.schemas.auth import CreateUserRequest
    from app.services import user_service
    token = str(uuid4().int)[:20]
    payload = CreateUserRequest(nombres="MARIA", apellido_paterno="PEREZ", ci=token,
        celular="70000000", correo=token + "@example.com", zona="TEST", role_code="CAJA")
    def fail(*args, **kwargs):
        raise RuntimeError("Injected failure before commit")
    monkeypatch.setattr(user_service, "queue_welcome_email", fail)
    with pytest.raises(RuntimeError):
        user_service.create_user(users.db, payload=payload, created_by=users.admin,
            background_tasks=BackgroundTasks(), ip_address=None, user_agent="QA_USERS")
    users.db.rollback()
    assert users.db.scalar(select(Usuario).where(Usuario.ci == token)) is None
    assert users.db.scalar(select(Cuenta).where(Cuenta.username == "MP" + token)) is None


def test_simultaneous_cross_demotion_reauthorizes_the_waiting_admin(pg_cluster):
    from app.models.account import Cuenta
    from app.services.user_service import update_user
    # Committed synthetic actors remain exclusively in testing as QA evidence.
    with Session(pg_cluster.engine, expire_on_commit=False) as setup:
        state = _setup(setup)
        ids = (state.admin.id, state.peer.id)
    barrier = Barrier(2)
    def demote(actor_id, target_id):
        with Session(pg_cluster.engine, autoflush=False) as db:
            actor, target = db.get(Cuenta, actor_id), db.get(Cuenta, target_id)
            payload = _edit(target, "CAJA")
            barrier.wait(timeout=10)
            try:
                update_user(db, account_id=target.id, payload=payload, updated_by=actor,
                    background_tasks=BackgroundTasks(), ip_address=None, user_agent="QA_USERS_CONCURRENT")
                return 200
            except HTTPException as error:
                db.rollback()
                return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(demote, ids[0], ids[1])
        second = pool.submit(demote, ids[1], ids[0])
        assert sorted([first.result(timeout=20), second.result(timeout=20)]) == [200, 403]
    with Session(pg_cluster.engine) as db:
        accounts = [db.get(Cuenta, identity) for identity in ids]
        assert sum(account.rol.codigo == "ADMIN" and account.is_active and account.usuario.activo for account in accounts) == 1


def test_migration_0022_roundtrip_is_transactionally_reversible(pg_cluster):
    import importlib.util
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import text
    migration_file = Path(__file__).resolve().parents[2] / "alembic/versions/20261103_0022_account_sessions.py"
    spec = importlib.util.spec_from_file_location("reviewed_account_sessions_migration", migration_file)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with pg_cluster.migration_engine.connect() as connection:
        pg_cluster.assert_identity(connection, pg_cluster.manifest, migrator=True)
        before = connection.scalar(text("SELECT count(*) FROM sesion_cuenta"))
        connection.rollback()
        transaction = connection.begin()
        try:
            with Operations.context(MigrationContext.configure(connection)):
                migration.downgrade()
                assert connection.scalar(text("SELECT to_regclass('public.sesion_cuenta')")) is None
                migration.upgrade()
                assert connection.scalar(text("SELECT to_regclass('public.sesion_cuenta')")) is not None
                assert connection.scalar(text("SELECT count(*) FROM cuentas WHERE auth_version IS NULL OR security_version IS NULL")) == 0
        finally:
            # Restore the exact session metadata, not merely an empty schema.
            transaction.rollback()
        assert connection.scalar(text("SELECT count(*) FROM sesion_cuenta")) == before


def test_two_simultaneous_refreshes_cannot_both_consume_one_refresh(pg_cluster):
    from app.models.account import Cuenta
    from app.core.security import REFRESH_TOKEN_TYPE, decode_token
    from app.services.auth_session_service import create_session, rotate_session
    with Session(pg_cluster.engine, expire_on_commit=False) as db:
        state = _setup(db)
        account_id = state.cashier.id
        login = create_session(db, state.cashier)
        db.commit()
    claims = decode_token(login["refresh_token"], REFRESH_TOKEN_TYPE)
    barrier = Barrier(2)
    def rotate():
        with Session(pg_cluster.engine) as db:
            actor = db.get(Cuenta, account_id)
            barrier.wait(timeout=10)
            try:
                rotate_session(db, actor, claims, login["refresh_token"])
                return 200
            except HTTPException as error:
                db.rollback()
                return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.submit(rotate), pool.submit(rotate)
        assert sorted([first.result(timeout=20), second.result(timeout=20)]) == [200, 401]
    from app.models.auth_session import AuthSession
    from uuid import UUID
    with Session(pg_cluster.engine) as db:
        session = db.get(AuthSession, UUID(claims["sid"]))
        assert session.revoked_at is not None and session.revocation_reason == "REFRESH_REUSE"
