from contextlib import asynccontextmanager

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
async def app_lifespan(_app: FastAPI):
    db = SessionLocal()
    try:
        cleanup_stale_backup_lock(db)
    finally:
        db.close()
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
