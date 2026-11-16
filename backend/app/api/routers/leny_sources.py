"""Read-only, individually owned source access, separate from the ADMIN library."""
from functools import lru_cache
from uuid import UUID
from urllib.parse import quote

from fastapi import APIRouter, Depends

from app.api.routers.leny import LenyRoute, get_leny_actor
from app.api.routers.leny_documents import AuthorizedFileResponse
from app.core.config import settings
from app.core.database import SessionLocal
from app.schemas.leny_rag_chat import SourceDetail
from app.services.leny_rag_sources import SourceService
from app.services.leny_ollama import LenyError
from app.services.leny_document_storage import DocumentError

router=APIRouter(route_class=LenyRoute)

@lru_cache
def get_source_service():return SourceService(settings,SessionLocal)

@router.get('/rag/sources/{source_id}',response_model=SourceDetail)
def resolve(source_id:UUID,actor=Depends(get_leny_actor),service=Depends(get_source_service)):
    from fastapi.responses import JSONResponse
    detail=service.resolve(actor,source_id)
    service.audit_read(actor,source_id)
    return JSONResponse(detail,headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'none'; sandbox"})

@router.get('/rag/sources/{source_id}/download')
def download(source_id:UUID,actor=Depends(get_leny_actor),service=Depends(get_source_service)):
    if not settings.leny_rag_allow_source_download:
        raise LenyError('LENY_SOURCE_UNAVAILABLE','Fuente no disponible.',404)
    row=service.resolve(actor,source_id,internal=True)
    service.audit_read(actor,source_id,download=True)
    try:
        if service.documents.storage.sha256(row['storage_key'])!=row['sha256']:
            raise LenyError('LENY_SOURCE_UNAVAILABLE','Fuente no disponible.',404)
        context=service.documents.storage.open(row['storage_key'])
        handle=context.__enter__()
    except DocumentError:
        raise LenyError('LENY_SOURCE_UNAVAILABLE','Fuente no disponible.',404) from None
    def chunks():
        while True:
            block=handle.read(65536)
            if not block:break
            service.resolve(actor,source_id,internal=True)
            yield block
    return AuthorizedFileResponse(chunks(),context,media_type=row['media_type'],headers={
        'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
        'Content-Security-Policy':"default-src 'none'; sandbox",
        'Content-Length':str(row['size_bytes']),
        'Content-Disposition':"attachment; filename*=UTF-8''"+quote(row['original_name'],safe='')})
