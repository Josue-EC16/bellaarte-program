"""ADMIN-only job admission/status; no endpoint retrieves fragment text."""
from functools import lru_cache
from uuid import UUID

import anyio
from fastapi import APIRouter, Depends, Query, Request, Response

from app.api.routers.leny_documents import DocumentRoute, document_actor, small_json
from app.core.config import settings
from app.core.database import SessionLocal
from app.schemas.leny_rag import ContextualizationRequest, ContextualizationJob, ContextualizationPage
from app.services.leny_rag_service import RagService

router = APIRouter(route_class=DocumentRoute)


@lru_cache
def get_rag_service():
    return RagService(settings, SessionLocal)


@router.post('/documents/{identity}/versions/{version_id}/contextualizations', response_model=ContextualizationJob)
async def submit(identity: UUID, version_id: UUID, request: Request, response: Response,
                 actor=Depends(document_actor), service=Depends(get_rag_service)):
    data = await small_json(request, ContextualizationRequest)
    result, created = await anyio.to_thread.run_sync(service.submit, actor, identity, version_id, data)
    response.status_code = 202 if created else 200
    return result


@router.get('/documents/{identity}/versions/{version_id}/contextualizations', response_model=ContextualizationPage)
def history(identity: UUID, version_id: UUID, page: int = Query(1, ge=1), page_size: int = Query(5, ge=1, le=20),
            actor=Depends(document_actor), service=Depends(get_rag_service)):
    return service.history(identity, version_id, page, page_size)


@router.get('/contextualizations/{job_id}', response_model=ContextualizationJob)
def job(job_id: UUID, actor=Depends(document_actor), service=Depends(get_rag_service)):
    return service.get(job_id)


@router.post('/contextualizations/{job_id}/cancel', response_model=ContextualizationJob)
async def cancel(job_id: UUID, request: Request, actor=Depends(document_actor), service=Depends(get_rag_service)):
    # No configurable provider fields or unbounded body accepted on cancellation.
    from pydantic import BaseModel, ConfigDict
    class Empty(BaseModel):
        model_config = ConfigDict(extra='forbid')
    size, blocks = 0, []
    async for block in request.stream():
        size += len(block)
        if size > 16384:
            from app.services.leny_document_storage import DocumentError
            raise DocumentError('DOCUMENT_BODY_LIMIT', 'Los metadatos superan el tamaño permitido.', 413)
        blocks.append(block)
    Empty.model_validate_json(b''.join(blocks) or b'{}')
    return await anyio.to_thread.run_sync(service.cancel, actor, job_id)


@router.get('/admin/rag/status')
def status(actor=Depends(document_actor), service=Depends(get_rag_service)):
    return service.status()
