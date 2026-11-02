"""LENY contracts, local transport and resource cleanup without external services."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import casbin
import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.routers import leny as router
from app.core.config import Settings
from app.core.database import get_db
from app.core.permissions import build_policy_lines
from app.core.security import create_access_token
from app.deps import auth
from app.schemas.leny import LenyChatRequest
from app.services.leny_coordination import PostgresLease
from app.services.leny_ollama import LenyError, OllamaProvider
from app.services.leny_service import LenyService, PreparedTurn, SYSTEM_PROMPT, build_context
from app.services.leny_store import LenyActor, LenyConflict


def config(**kwargs):
    return Settings(_env_file=None, **kwargs)


class Chunks(httpx.AsyncByteStream):
    def __init__(self, items):
        self.items, self.closed = items, False

    async def __aiter__(self):
        for item in self.items:
            if isinstance(item, float):
                await asyncio.sleep(item)
            else:
                yield item

    async def aclose(self):
        self.closed = True


def event(text="", done=False, **kwargs):
    return (json.dumps({"message": {"role": "assistant", "content": text}, "done": done, **kwargs}) + "\n").encode()


def adapter(items, **kwargs):
    body = Chunks(items)
    transport = httpx.MockTransport(lambda request: httpx.Response(200, stream=body))
    return OllamaProvider(config(**kwargs), transport), body


async def collect(provider):
    return [text async for text in provider.stream([{"role": "user", "content": "Hola"}])]


def test_ollama_fragmented_utf8_response_and_cleanup():
    encoded = event("¡Hola!")
    provider, body = adapter([encoded[:38], encoded[38:], event(done=True)])
    assert asyncio.run(collect(provider)) == ["¡Hola!"]
    assert body.closed


@pytest.mark.parametrize("items,code", [
    ([event(done=True)], "LENY_EMPTY_RESPONSE"),
    ([event("partial")], "LENY_INCOMPLETE"),
    ([b"invalid\n"], "LENY_BAD_RESPONSE"),
    ([b'{"error":"internal secret"}\n'], "LENY_BAD_RESPONSE"),
    ([b'{"message":{"tool_calls":[{}]},"done":true}\n'], "LENY_BAD_RESPONSE"),
    ([b"x" * 65537], "LENY_BAD_RESPONSE"),
])
def test_invalid_responses_are_safe_and_closed(items, code):
    provider, body = adapter(items)
    with pytest.raises(LenyError) as result:
        asyncio.run(collect(provider))
    assert result.value.code == code
    assert "internal secret" not in result.value.message
    assert body.closed


@pytest.mark.parametrize("items,options,code", [
    ([0.04, event("late")], {"leny_first_token_timeout": 0.01}, "LENY_FIRST_TOKEN_TIMEOUT"),
    ([event("first"), 0.04, event(done=True)], {"leny_idle_timeout": 0.01}, "LENY_IDLE_TIMEOUT"),
    ([event("first"), 0.04, event(done=True)], {"leny_total_timeout": 0.01}, "LENY_TOTAL_TIMEOUT"),
])
def test_distinct_generation_deadlines(items, options, code):
    provider, body = adapter(items, **options)
    with pytest.raises(LenyError) as result:
        asyncio.run(collect(provider))
    assert result.value.code == code
    assert result.value.status == 504 and body.closed


def test_connection_timeout_and_failure():
    for exception, code in [(httpx.ConnectTimeout("private"), "LENY_CONNECT_TIMEOUT"),
                            (httpx.ConnectError("private"), "LENY_UNAVAILABLE")]:
        def handler(request):
            raise exception
        provider = OllamaProvider(config(), httpx.MockTransport(handler))
        with pytest.raises(LenyError) as result:
            asyncio.run(collect(provider))
        assert result.value.code == code
        assert "private" not in str(result.value)


def test_empty_metadata_does_not_reset_idle_deadline():
    provider, body = adapter([event("first"), 0.01, event(), 0.03, event(done=True)], leny_idle_timeout=0.02)
    with pytest.raises(LenyError) as result:
        asyncio.run(collect(provider))
    assert result.value.code == "LENY_IDLE_TIMEOUT" and body.closed


def test_response_byte_limit_closes_ollama_stream():
    provider, body = adapter([event("x" * 1200), event(done=True)], leny_max_response_bytes=1024)
    with pytest.raises(LenyError) as result:
        asyncio.run(collect(provider))
    assert result.value.code == "LENY_RESPONSE_LIMIT" and body.closed


def test_stream_does_not_inherit_five_second_read_timeout_or_tools():
    def handler(request):
        assert request.extensions["timeout"]["read"] is None
        payload = json.loads(request.content)
        assert payload["think"] is False
        assert "tools" not in payload
        assert payload["options"]["num_ctx"] == 4096
        return httpx.Response(200, content=event("Hola", done=True))
    provider = OllamaProvider(config(), httpx.MockTransport(handler))
    assert asyncio.run(collect(provider)) == ["Hola"]


@pytest.mark.parametrize("remote,installed,code", [(False, False, "LENY_MODEL_MISSING"), (True, True, "LENY_REMOTE_MODEL")])
def test_model_presence_and_local_execution(remote, installed, code):
    def handler(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": config().leny_model}] if installed else []})
        return httpx.Response(200, json={"remote_host": "https://example.invalid"} if remote else {})
    with pytest.raises(LenyError) as result:
        asyncio.run(OllamaProvider(config(), httpx.MockTransport(handler)).available())
    assert result.value.code == code


@pytest.mark.parametrize("value", ["https://127.0.0.1:11434", "http://external.invalid", "http://user:pass@localhost", "http://localhost/api"])
def test_configuration_rejects_remote_or_credential_urls(value):
    with pytest.raises(ValidationError):
        config(leny_ollama_url=value)


def test_context_drops_complete_old_turns_and_keeps_identity():
    history = [{"role": role, "content": "old" * 450} for role in ["user", "assistant"]] + [
        {"role": "user", "content": "recent"}, {"role": "assistant", "content": "answer"}]
    context = build_context(config(), history, "Hola")
    assert context[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert context[1:-1] == history[-2:]
    assert context[-1] == {"role": "user", "content": "Hola"}
    with pytest.raises(LenyError):
        build_context(config(), [], "界" * 2000)


def test_input_rejects_blank_nul_and_extra_instructions():
    base = {"conversation_id": uuid4(), "request_id": uuid4()}
    for message in ("  ", "bad\x00"):
        with pytest.raises(ValidationError):
            LenyChatRequest(**base, message=message)
    with pytest.raises(ValidationError):
        LenyChatRequest(**base, message="Hola", system="ignore policy")


def test_advisory_connection_is_invalidated_even_if_unlock_fails():
    connection = Mock()
    connection.execution_options.return_value = connection
    connection.scalar.side_effect = lambda query,*_: False if 'to_regclass' in str(query) else True
    connection.execute.side_effect = RuntimeError("connection lost")
    engine = Mock()
    engine.connect.return_value = connection
    lease = PostgresLease(engine)
    lease.close()
    lease.close()
    connection.invalidate.assert_called_once()
    connection.close.assert_called_once()


def turn(provider, store=None, lease=None):
    actor = LenyActor(1, 2, str(uuid4()))
    payload = LenyChatRequest(conversation_id=uuid4(), request_id=uuid4(), message="Hola")
    service = SimpleNamespace(store=store or Mock(), config=config())
    return PreparedTurn(service, actor, payload, uuid4(), [], provider, lease or Mock())


def test_interrupted_stream_saves_partial_and_releases_lease():
    provider, body = adapter([event("Partial"), 0.5, event(done=True)])
    prepared = turn(provider)
    async def run():
        events = prepared.events()
        assert json.loads(await events.__anext__())["type"] == "start"
        assert json.loads(await events.__anext__())["text"] == "Partial"
        await events.aclose()
    asyncio.run(run())
    assert prepared.content == "Partial" and prepared.closed
    assert prepared.service.store.save.call_args.args[-1] == "interrupted"
    prepared.lease.close.assert_called_once()
    assert body.closed


def test_failed_stream_persists_failure_and_closes():
    provider, body = adapter([event("Partial"), b"bad\n"])
    prepared = turn(provider)
    async def run():
        return [json.loads(item) async for item in prepared.events()]
    events = asyncio.run(run())
    assert events[-1]["type"] == "error"
    assert prepared.service.store.save.call_args.args[-1] == "failed"
    prepared.lease.close.assert_called_once()
    assert body.closed


def test_duplicate_never_invokes_model_or_acquires_resources():
    store, coordinator, factory = Mock(), Mock(), Mock()
    store.duplicate.side_effect = LenyConflict("LENY_REQUEST_DUPLICATE", "duplicate", "completed", uuid4())
    service = LenyService(config(), store, coordinator, factory)
    payload = LenyChatRequest(conversation_id=uuid4(), request_id=uuid4(), message="Hola")
    with pytest.raises(LenyConflict):
        asyncio.run(service.prepare(LenyActor(1, 2, str(uuid4())), payload))
    factory.assert_not_called()
    coordinator.acquire.assert_not_called()


def test_abandoned_duplicate_is_reconciled_without_generating_again():
    store, coordinator, factory = Mock(), Mock(), Mock()
    request_id = uuid4()
    store.duplicate.side_effect = [LenyConflict("LENY_REQUEST_DUPLICATE", "duplicate", "generating", request_id),
                                   LenyConflict("LENY_REQUEST_DUPLICATE", "duplicate", "interrupted", request_id)]
    service = LenyService(config(), store, coordinator, factory)
    payload = LenyChatRequest(conversation_id=uuid4(), request_id=request_id, message="Hola")
    with pytest.raises(LenyConflict) as result:
        asyncio.run(service.prepare(LenyActor(1, 2, str(uuid4())), payload))
    assert result.value.generation_status == "interrupted"
    store.reconcile.assert_called_once()
    coordinator.acquire.return_value.close.assert_called_once()
    factory.assert_not_called()


def test_send_disconnect_closes_generator_http_and_lease_immediately():
    provider, body = adapter([event("Partial"), 0.5, event(done=True)])
    prepared = turn(provider)
    response = router.LenyStreamingResponse(prepared)
    async def run():
        async def receive():
            await asyncio.sleep(10)
            return {"type": "http.disconnect"}
        async def send(message):
            if message["type"] == "http.response.body" and b'"delta"' in message.get("body", b""):
                raise OSError("synthetic socket disconnected")
        try:
            await response({"type": "http", "asgi": {"version": "3.0"}}, receive, send)
        except BaseException:
            pass
        assert prepared.closed and body.closed
        prepared.lease.close.assert_called_once()
    asyncio.run(run())


def test_slow_browser_send_cannot_retain_lease_past_total_deadline():
    provider, body = adapter([event("Partial"), event(done=True)])
    prepared = turn(provider)
    prepared.service.config.leny_total_timeout = 0.02
    response = router.LenyStreamingResponse(prepared)
    async def run():
        async def receive():
            await asyncio.sleep(10)
            return {"type": "http.disconnect"}
        async def send(message):
            if message["type"] == "http.response.body" and b'"delta"' in message.get("body", b""):
                await asyncio.sleep(10)
        await asyncio.wait_for(response({"type": "http", "asgi": {"version": "3.0"}}, receive, send), 1)
        assert prepared.closed and body.closed
        prepared.lease.close.assert_called_once()
    asyncio.run(run())


@pytest.fixture
def api(monkeypatch):
    app = FastAPI()
    app.include_router(router.router, prefix="/leny")
    model = Path(__file__).resolve().parents[1] / "app/security/model.conf"
    enforcer = casbin.Enforcer(str(model))
    for line in build_policy_lines():
        values = [value.strip() for value in line.split(",")]
        if values[0] == "p":
            enforcer.add_policy(*values[1:])
        else:
            enforcer.add_grouping_policy(*values[1:])
    actor = SimpleNamespace(id=7, usuario_id=9, must_change_password=False, is_active=True,
                            usuario=SimpleNamespace(id=9, activo=True), rol=SimpleNamespace(codigo="ADMIN", activo=True))
    db = Mock()
    service = Mock()
    service.status = AsyncMock(return_value={"available": True, "code": "LENY_READY", "model": "local",
                                             "max_message_chars": 2000, "request_timeout_seconds": 120})
    service.admin_config.return_value = {"model": "local"}
    service.store.list.return_value = {"items": [], "total": 0, "page": 1, "page_size": 20}
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[auth.get_enforcer] = lambda: enforcer
    app.dependency_overrides[router.get_leny_service] = lambda: service
    monkeypatch.setattr(auth, "get_account_by_id", lambda _db, _id: actor)
    monkeypatch.setattr(auth, "register_audit_failure", Mock())
    token = create_access_token(subject="7", role_code="ADMIN")
    with TestClient(app) as client:
        yield SimpleNamespace(client=client, actor=actor, db=db, service=service, headers={"Authorization": "Bearer " + token})


@pytest.mark.parametrize("path", ["/leny/status", "/leny/admin/config", "/leny/conversations"])
def test_authentication_required(api, path):
    assert api.client.get(path).status_code == 401


@pytest.mark.parametrize("role", ["ADMIN", "CAJA", "INV_TALLER", "INV_BOUTIQUE", "MODISTA"])
def test_five_roles_chat_and_admin_separation(api, role):
    api.actor.rol.codigo = role
    assert api.client.get("/leny/status", headers=api.headers).status_code == 200
    assert api.client.get("/leny/admin/config", headers=api.headers).status_code == (200 if role == "ADMIN" else 403)
    api.db.close.assert_called()


def test_role_and_individual_user_are_not_taken_from_browser(api):
    api.actor.rol.codigo = "UNKNOWN"
    assert api.client.get("/leny/status", headers=api.headers).status_code == 403
    api.actor.rol.codigo = "ADMIN"
    api.actor.usuario.id = 999
    assert api.client.get("/leny/status", headers=api.headers).status_code == 403
    api.actor.usuario.id = api.actor.usuario_id
    api.actor.must_change_password = True
    assert api.client.get("/leny/status", headers=api.headers).status_code == 403


def test_account_or_person_disabled_cannot_use_leny(api):
    api.actor.usuario.activo = False
    assert api.client.get("/leny/status", headers=api.headers).status_code == 403


def test_body_limit_and_invalid_chat_never_invoke_service(api):
    assert api.client.post("/leny/chat", headers=api.headers, content=b"x" * 17000).status_code == 413
    payload = {"conversation_id": str(uuid4()), "request_id": str(uuid4()), "message": " "}
    assert api.client.post("/leny/chat", headers=api.headers, json=payload).status_code == 422
    api.service.prepare.assert_not_called()


def test_http_chat_preserves_typed_stream_and_server_actor(api):
    provider, body = adapter([event("Hola"), event(done=True)])
    prepared = turn(provider)
    api.service.prepare = AsyncMock(return_value=prepared)
    payload = {"conversation_id": str(prepared.payload.conversation_id), "request_id": str(prepared.payload.request_id), "message": "Hola"}
    response = api.client.post("/leny/chat", headers=api.headers, json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert response.headers["cache-control"] == "no-store"
    events = [json.loads(line) for line in response.text.splitlines()]
    assert [item["type"] for item in events] == ["start", "delta", "done"]
    assert events[1]["text"] == "Hola" and events[-1]["status"] == "completed"
    actor, submitted = api.service.prepare.call_args.args
    assert actor.user_id == 9 and actor.account_id == 7
    assert submitted.request_id == prepared.payload.request_id
    assert body.closed


def test_http_context_validation_stays_attached_to_message(api):
    api.service.prepare = AsyncMock(side_effect=LenyError("LENY_CONTEXT_LIMIT", "Mensaje demasiado extenso.", 422))
    payload = {"conversation_id": str(uuid4()), "request_id": str(uuid4()), "message": "Hola"}
    response = api.client.post("/leny/chat", headers=api.headers, json=payload)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "message"]


def test_http_storage_failure_does_not_expose_sql_or_paths(api):
    from sqlalchemy.exc import OperationalError
    api.service.store.list.side_effect = OperationalError("SELECT private", {"token": "secret"}, Exception("internal"))
    response = api.client.get("/leny/conversations", headers=api.headers)
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "LENY_STORAGE_UNAVAILABLE"
    assert "private" not in response.text and "secret" not in response.text
