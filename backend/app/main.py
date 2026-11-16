from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.backup_runtime import BACKUP_BLOCKED_MESSAGE, is_backup_exempt_request, is_backup_lock_active
from app.core.audit import prime_audit_request_context, reset_audit_request_context
from app.core.config import settings
from app.core.database import SessionLocal
from app.services.backup_service import cleanup_stale_backup_lock


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    from app.services.leny_runtime import LenyRuntime
    import anyio
    runtime=LenyRuntime(settings)
    app.state.leny_runtime=runtime
    try:
        await runtime.start()
        async with erp_lifespan(app):
            yield
    finally:
        # Uvicorn reload/Ctrl+C must finish owned child cleanup, including if
        # another startup step failed or ASGI is cancelling its task group.
        with anyio.CancelScope(shield=True):
            await runtime.close()


@asynccontextmanager
async def erp_lifespan(_app: FastAPI):
    db = SessionLocal()
    try:
        cleanup_stale_backup_lock(db)
    finally:
        db.close()
    if settings.leny_enabled:
        from app.api.routers.leny import get_leny_service
        try:
            await get_leny_service().reconcile()
        except Exception:
            # Missing migration or another active generator must not stop the ERP.
            logging.getLogger(__name__).warning("LENY_STARTUP_RECONCILIATION_DEFERRED")
    if settings.leny_documents_enabled:
        import anyio
        from app.api.routers.leny_documents import get_document_service
        from app.services.leny_document_maintenance import maintenance_loop
        async with anyio.create_task_group() as tasks:
            tasks.start_soon(maintenance_loop, get_document_service(), settings.leny_documents_maintenance_seconds)
            try:
                yield
            finally:
                tasks.cancel_scope.cancel()
    else:
        yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="BellaArte API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=app_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Retry-After", "Content-Disposition"],
    )

    @app.middleware("http")
    async def attach_audit_context(request, call_next):
        if request.method.upper() == "OPTIONS":
            return await call_next(request)
        if is_backup_lock_active():
            db = SessionLocal()
            try:
                cleanup_stale_backup_lock(db)
            finally:
                db.close()
        if is_backup_lock_active() and not is_backup_exempt_request(request.url.path, request.method):
            return JSONResponse(
                status_code=503,
                content={
                    "detail": BACKUP_BLOCKED_MESSAGE,
                    "code": "BACKUP_IN_PROGRESS",
                },
            )
        tokens = prime_audit_request_context(
            method=request.method,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        try:
            return await call_next(request)
        finally:
            reset_audit_request_context(tokens)

    @app.get("/health", tags=["health"])
    def healthcheck() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
