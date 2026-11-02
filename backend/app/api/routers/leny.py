"""LENY endpoints integrated with the ERP's JWT/Casbin dependencies."""
from functools import lru_cache
import logging
from uuid import UUID, uuid4

import anyio
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from fastapi.routing import APIRoute
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.audit import current_audit_event_id
from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.deps.auth import require_permission
from app.models.account import Cuenta
from app.schemas.leny import (ConversationDetailResponse, ConversationListResponse, ConversationResponse,
                              LenyChatRequest, LenyStatusResponse)
from app.services.leny_coordination import PostgresCoordinator
from app.services.leny_ollama import LenyError
from app.services.leny_service import LenyService
from app.services.leny_store import LenyActor, LenyConflict, LenyStore
from app.services.leny_rate_limit import RateLimiter


def http_error(error: LenyError) -> HTTPException:
    if error.status == 422:
        return HTTPException(422, detail=[{"loc": ["body", "message"], "msg": error.message, "type": "value_error"}])
    detail = {"code": error.code, "message": error.message}
    if isinstance(error, LenyConflict):
        detail.update(status=error.generation_status, request_id=str(error.request_id) if error.request_id else None)
    return HTTPException(error.status, detail=detail,
                         headers={"Retry-After": str(getattr(error, "retry_after", 3))} if error.status == 429 else None)


class LenyRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def bounded_handler(request: Request):
            if request.method == "POST":
                chunks, size = [], 0
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > settings.leny_max_body_bytes:
                        raise HTTPException(413, detail="La solicitud supera el tamaño permitido.")
                    chunks.append(chunk)
                request._body = b"".join(chunks)
            try:
                return await handler(request)
            except LenyError as error:
                raise http_error(error) from None
            except RequestValidationError as error:
                # FastAPI normally echoes input in 422, including pasted credentials.
                detail = [{"loc": list(item["loc"]), "msg": "Revisa el valor enviado. No incluyas credenciales ni caracteres de control.",
                           "type": item["type"]} for item in error.errors()]
                actor = getattr(request.state, "leny_actor", None)
                service = getattr(request.state, "leny_service", None)
                if actor is not None and service is not None:
                    try:
                        await anyio.to_thread.run_sync(service.store.input_rejected, actor)
                    except Exception:
                        logging.getLogger(__name__).warning("LENY_INPUT_AUDIT_DEFERRED")
                raise HTTPException(422, detail=detail) from None
            except SQLAlchemyError:
                raise HTTPException(503, detail={"code": "LENY_STORAGE_UNAVAILABLE",
                                               "message": "El historial de LENY no está disponible. Intenta nuevamente."}) from None
        return bounded_handler


router = APIRouter(route_class=LenyRoute)


@lru_cache
def get_leny_service() -> LenyService:
    from app.services.leny_rag_retrieval import RetrievalService
    from app.services.leny_rag_sources import SourceService
    from app.services.leny_inference_state import InferenceState
    sources=SourceService(settings,SessionLocal) if settings.leny_rag_chat_enabled else None
    return LenyService(settings, LenyStore(SessionLocal,sources), PostgresCoordinator(settings.effective_database_url),
                       rate_limiter=RateLimiter(SessionLocal, settings.leny_rate_limit, settings.leny_rate_window_seconds),
                       retrieval=RetrievalService(settings,SessionLocal) if sources else None,
                       sources=sources,inference_state=InferenceState(SessionLocal))


def actor_dependency(permission):
    def actor(request: Request, account: Cuenta = Depends(require_permission(permission)), db: Session = Depends(get_db),
              service: LenyService = Depends(get_leny_service)):
        try:
            if account.must_change_password:
                raise HTTPException(403, detail="Debes cambiar tu contraseña antes de utilizar LENY.")
            if account.usuario is None or account.usuario.id != account.usuario_id:
                raise HTTPException(403, detail="La cuenta requiere un usuario individual válido.")
            actor = LenyActor(account.id, account.usuario_id, current_audit_event_id() or str(uuid4()),
                              request.client.host if request.client else None, request.headers.get("user-agent"))
            request.state.leny_actor, request.state.leny_service = actor, service
            return actor
        finally:
            # Release the authentication SELECT transaction before any model wait.
            db.close()
    return actor


get_leny_actor = actor_dependency("leny:chat")
get_leny_admin = actor_dependency("leny:admin")


class LenyStreamingResponse(StreamingResponse):
    def __init__(self, turn):
        self.turn = turn
        super().__init__(turn.events(), media_type="application/x-ndjson",
                         headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    async def __call__(self, scope, receive, send):
        try:
            # Bound time spent in ASGI send too: a slow/disconnected browser must
            # not retain the model lease after Ollama's own generation deadline.
            with anyio.move_on_after(self.turn.remaining()):
                await super().__call__(scope, receive, send)
        finally:
            with anyio.CancelScope(shield=True):
                try:
                    await self.body_iterator.aclose()
                finally:
                    await self.turn.close()


@router.get("/status", response_model=LenyStatusResponse)
async def status(actor: LenyActor = Depends(get_leny_actor), service: LenyService = Depends(get_leny_service)):
    return await service.status()


@router.get("/admin/config")
def config(actor: LenyActor = Depends(get_leny_admin), service: LenyService = Depends(get_leny_service)):
    return service.admin_config()


@router.post("/conversations", response_model=ConversationResponse, status_code=201)
def create_conversation(actor: LenyActor = Depends(get_leny_actor), service: LenyService = Depends(get_leny_service)):
    return service.store.create(actor)


@router.get("/conversations", response_model=ConversationListResponse)
def list_conversations(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=50),
                       actor: LenyActor = Depends(get_leny_actor), service: LenyService = Depends(get_leny_service)):
    return service.store.list(actor, page, page_size)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(conversation_id: UUID, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100),
                     actor: LenyActor = Depends(get_leny_actor), service: LenyService = Depends(get_leny_service)):
    return service.store.detail(actor, conversation_id, page, page_size)


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: UUID, actor: LenyActor = Depends(get_leny_actor), service: LenyService = Depends(get_leny_service)):
    service.store.remove(actor, conversation_id)
    return Response(status_code=204)


@router.post("/chat")
async def chat(payload: LenyChatRequest, actor: LenyActor = Depends(get_leny_actor), service: LenyService = Depends(get_leny_service)):
    turn = await service.prepare(actor, payload)
    return LenyStreamingResponse(turn)
