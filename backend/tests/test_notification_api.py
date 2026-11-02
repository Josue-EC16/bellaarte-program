"""HTTP contracts and real Casbin policies with persistence explicitly replaced."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import casbin
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.api.routers import notifications as router
from app.core.database import get_db
from app.deps import auth


@pytest.fixture
def api(monkeypatch):
    security = Path(__file__).resolve().parents[1] / "app" / "security"
    enforcer = casbin.Enforcer(str(security / "model.conf"), str(security / "policy.csv"))
    actor = SimpleNamespace(usuario_id=71, rol=SimpleNamespace(codigo="INV_BOUTIQUE"))
    database = SimpleNamespace(commit=Mock(), rollback=Mock())
    app = FastAPI()
    app.include_router(router.router, prefix="/notificaciones")
    app.dependency_overrides[get_db] = lambda: database
    app.dependency_overrides[auth.get_current_account] = lambda: actor
    app.dependency_overrides[auth.get_enforcer] = lambda: enforcer
    monkeypatch.setattr(auth, "register_audit_failure", Mock())
    with TestClient(app) as client:
        yield SimpleNamespace(client=client, actor=actor, enforcer=enforcer, database=database)


def test_admin_default_list_remains_personal_and_pagination_is_server_contract(api, monkeypatch):
    api.actor.rol.codigo = "ADMIN"
    service = Mock(return_value={"items": [], "total": 0, "page": 2, "page_size": 25})
    monkeypatch.setattr(router, "list_notifications", service)
    response = api.client.get("/notificaciones", params={"page": 2, "user_id": 999})
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "page": 2, "page_size": 25}
    assert service.call_args.kwargs["account"] is api.actor
    assert service.call_args.kwargs.get("supervision", False) is False


@pytest.mark.parametrize("path", ["/notificaciones/supervision", "/notificaciones/supervision/1", "/notificaciones/reportes/resumen"])
def test_operational_role_cannot_enter_supervision_or_reports(api, path):
    assert api.client.get(path).status_code == 403


def test_supervision_permission_works_without_admin_role_name(api, monkeypatch):
    api.actor.rol.codigo = "QA_SUPERVISOR"
    api.enforcer.add_policy("QA_SUPERVISOR", "notifications:list_all", "use")
    service = Mock(return_value={"items": [], "total": 0, "page": 1, "page_size": 25})
    monkeypatch.setattr(router, "list_notifications", service)
    response = api.client.get("/notificaciones/supervision", params={"user_id": 99})
    assert response.status_code == 200
    assert service.call_args.kwargs["supervision"] is True
    assert service.call_args.kwargs["filters"].user_id == 99


@pytest.mark.parametrize("params", [{"page_size": 101}, {"page_size": 0}, {"page": 0}])
def test_bad_pagination_is_rejected_before_service(api, monkeypatch, params):
    service = Mock()
    monkeypatch.setattr(router, "list_notifications", service)
    assert api.client.get("/notificaciones", params=params).status_code == 422
    service.assert_not_called()


@pytest.mark.parametrize("payload", [None, {}, {"revision": 0}])
def test_read_requires_the_visible_revision(api, monkeypatch, payload):
    service = Mock()
    monkeypatch.setattr(router, "mark_notification_read", service)
    assert api.client.patch("/notificaciones/8/read", json=payload).status_code == 422
    service.assert_not_called()


def test_read_all_always_passes_current_personal_account(api, monkeypatch):
    api.actor.rol.codigo = "ADMIN"
    service = Mock(return_value={"updated": 1})
    monkeypatch.setattr(router, "mark_all_notifications_read", service)
    response = api.client.patch("/notificaciones/read-all?user_id=999&supervision=true")
    assert response.status_code == 200
    assert service.call_args.kwargs == {"account": api.actor}


def test_desktop_claim_uses_only_authenticated_user(api, monkeypatch):
    service = Mock(return_value={"items": []})
    monkeypatch.setattr(router, "claim_desktop_notifications", service)
    assert api.client.post("/notificaciones/escritorio/reclamar", json={"user_id": 999}).status_code == 200
    assert service.call_args.kwargs == {"account": api.actor}


@pytest.mark.parametrize("path", ["/notificaciones/8/resolve", "/notificaciones/8/retry-email"])
def test_operational_role_cannot_resolve_or_retry_email(api, path):
    method = api.client.patch if path.endswith("resolve") else api.client.post
    assert method(path, json={"motivo": "QA MOTIVO"}).status_code == 403
