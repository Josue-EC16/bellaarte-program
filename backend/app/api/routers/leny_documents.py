"""ADMIN-only private library. Authorize before consuming multipart bodies."""
from functools import lru_cache
import json
from pathlib import Path
import unicodedata
from uuid import UUID, uuid4

import anyio
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.routing import APIRoute
from pydantic import ValidationError
from python_multipart import MultipartParser
from python_multipart.multipart import parse_options_header
from python_multipart.exceptions import MultipartParseError
from starlette.requests import ClientDisconnect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.deps.auth import require_permission
from app.models.account import Cuenta
from app.schemas.leny_documents import (DocumentChange, DocumentFilters, DocumentUpload, FolderCreate,
    FolderUpdate, PurgeConfirm, PurgePreview, VersionUpload, DocumentPage, FolderList, DocumentDetail, VersionPage,
    PublicationRequest, UnpublicationRequest)
from app.services.leny_document_service import DocumentService
from app.services.leny_document_storage import DocumentError
from app.services.leny_store import LenyActor


class DocumentRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def safe_handler(request):
            try:
                return await handler(request)
            except DocumentError as error:
                retry = (settings.leny_documents_rate_window_seconds if error.code == 'DOCUMENT_RATE_LIMITED'
                         else 60 if error.code == 'RAG_RATE_LIMITED' else 3)
                return JSONResponse({'detail':{'code':error.code, 'message':error.message}}, status_code=error.status,
                                    headers={'Retry-After':str(retry)} if error.status == 429 else {})
            except (ValidationError, RequestValidationError):
                return JSONResponse({'detail':{'code':'DOCUMENT_INVALID_INPUT', 'message':'Revisa los campos y valores enviados.'}}, status_code=422)
            except MultipartParseError:
                return JSONResponse({'detail':{'code':'DOCUMENT_MULTIPART_INVALID', 'message':'La carga multipart no es válida.'}}, status_code=422)
            except SQLAlchemyError:
                return JSONResponse({'detail':{'code':'DOCUMENT_STORAGE_UNAVAILABLE', 'message':'La biblioteca documental no está disponible.'}}, status_code=503)
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                return JSONResponse({'detail':{'code':'DOCUMENT_OPERATION_FAILED', 'message':'No se pudo completar la operación documental.'}}, status_code=503)
        return safe_handler


router = APIRouter(route_class=DocumentRoute)


def document_actor(request: Request, account: Cuenta = Depends(require_permission('leny:admin')),
                   db: Session = Depends(get_db)):
    try:
        if account.rol.codigo != 'ADMIN' or account.must_change_password or not account.usuario or account.usuario.id != account.usuario_id:
            raise HTTPException(403, detail='La biblioteca requiere una cuenta ADMIN individual habilitada.')
        if not settings.leny_documents_enabled:
            raise DocumentError('DOCUMENT_LIBRARY_DISABLED', 'La biblioteca documental aún no está habilitada.', 503)
        return LenyActor(account.id, account.usuario_id, str(uuid4()), request.client.host if request.client else None,
                         request.headers.get('user-agent'))
    finally:
        db.close()


@lru_cache
def get_document_service():
    return DocumentService(settings, SessionLocal)


async def small_json(request, contract):
    data, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > 16384:
            raise DocumentError('DOCUMENT_BODY_LIMIT', 'Los metadatos superan el tamaño permitido.', 413)
        data.append(chunk)
    return contract.model_validate_json(b''.join(data))


async def mutate(service, function, *args, **kwargs):
    def run():
        with service.lock():
            service.recover()
            return function(*args, **kwargs)
    return await anyio.to_thread.run_sync(run)


@router.get('/folders', response_model=FolderList)
def folders(actor=Depends(document_actor), service=Depends(get_document_service)):
    return service.folders(actor)


@router.get('/options')
def document_options(actor=Depends(document_actor)):
    # Only public UI limits, never filesystem paths, secrets or Ollama options.
    return dict(batch_size=settings.leny_documents_batch_size, max_file_bytes=settings.leny_documents_max_file_bytes,
                image_bytes=settings.leny_documents_image_bytes, max_pixels=settings.leny_documents_max_pixels,
                pdf_pages=settings.leny_documents_pdf_pages)


@router.post('/folders')
async def create_folder(request: Request, actor=Depends(document_actor), service=Depends(get_document_service)):
    data = await small_json(request, FolderCreate)
    return await mutate(service, service.save_folder, actor, data)


@router.patch('/folders/{identity}')
async def change_folder(identity: UUID, request: Request, actor=Depends(document_actor), service=Depends(get_document_service)):
    data = await small_json(request, FolderUpdate)
    return await mutate(service, service.save_folder, actor, data, identity)


@router.delete('/folders/{identity}')
async def delete_folder(identity: UUID, actor=Depends(document_actor), service=Depends(get_document_service)):
    return await mutate(service, service.delete_folder, actor, identity)


@router.get('', response_model=DocumentPage)
def list_documents(filters: DocumentFilters = Depends(), actor=Depends(document_actor), service=Depends(get_document_service)):
    return service.list_documents(filters)


@router.get('/trash', response_model=DocumentPage)
def trash_list(filters: DocumentFilters = Depends(), actor=Depends(document_actor), service=Depends(get_document_service)):
    return service.list_documents(filters, trash=True)


@router.post('/trash/purge-preview')
async def purge_preview(request: Request, actor=Depends(document_actor), service=Depends(get_document_service)):
    data = await small_json(request, PurgePreview)
    return await mutate(service, service.purge_preview, actor, data)


@router.post('/trash/empty')
async def purge_empty(request: Request, actor=Depends(document_actor), service=Depends(get_document_service)):
    data = await small_json(request, PurgeConfirm)
    return await mutate(service, service.purge, actor, data)


class MultipartUpload:
    """Single file + first metadata field, bounded independently of headers."""
    def __init__(self, service, actor, boundary, document_id):
        self.service, self.actor, self.document_id = service, actor, document_id
        self.headers, self.header_name, self.header_value = {}, bytearray(), bytearray()
        self.metadata, self.part_name, self.parts = bytearray(), None, 0
        self.data, self.stage, self.file, self.filename, self.extension = None, None, None, None, None
        self.size, self.complete, self.duplicate = 0, False, None
        self.parser = MultipartParser(boundary, {'on_part_begin':self.begin, 'on_header_field':self.header_field,
            'on_header_value':self.header_value_data, 'on_header_end':self.header_end,
            'on_headers_finished':self.headers_end, 'on_part_data':self.part_data, 'on_part_end':self.part_end,
            'on_end':self.end})

    def begin(self):
        self.parts += 1
        if self.parts > 2:
            raise DocumentError('DOCUMENT_MULTIPART_INVALID', 'Envía metadatos y un único archivo.', 422)
        self.headers = {}

    def header_field(self, data, start, end):
        self.header_name.extend(data[start:end])
        if len(self.header_name) > 128:
            raise DocumentError('DOCUMENT_MULTIPART_INVALID', 'Cabeceras no permitidas.', 422)

    def header_value_data(self, data, start, end):
        self.header_value.extend(data[start:end])
        if len(self.header_value) > 1024:
            raise DocumentError('DOCUMENT_MULTIPART_INVALID', 'Cabeceras demasiado extensas.', 422)

    def header_end(self):
        key = bytes(self.header_name).lower()
        if key in self.headers or len(self.headers) > 5:
            raise DocumentError('DOCUMENT_MULTIPART_INVALID', 'Cabeceras no permitidas.', 422)
        self.headers[key] = bytes(self.header_value)
        self.header_name.clear()
        self.header_value.clear()

    def headers_end(self):
        raw_disposition = self.headers.get(b'content-disposition', b'')
        # python-multipart strips legacy IE Windows paths; reject the raw path
        # rather than accidentally accepting a disguised filename afterwards.
        if b'\\' in raw_disposition:
            raise DocumentError('DOCUMENT_FILENAME_INVALID', 'El nombre de archivo no es válido.', 422)
        disposition, options = parse_options_header(raw_disposition)
        name = options.get(b'name')
        if disposition != b'form-data' or name != (b'metadata' if self.parts == 1 else b'file'):
            raise DocumentError('DOCUMENT_MULTIPART_INVALID', 'Envía primero los metadatos y después el archivo.', 422)
        self.part_name = name
        if self.parts == 2:
            raw = options.get(b'filename', b'')
            self.filename = raw.decode('utf-8', errors='strict')
            if (not self.filename or len(self.filename) > 255 or any(c in self.filename for c in '/\\:')
                    or any(unicodedata.category(c) in {'Cc', 'Cs'} for c in self.filename)):
                raise DocumentError('DOCUMENT_FILENAME_INVALID', 'El nombre de archivo no es válido.', 422)
            self.extension = Path(self.filename).suffix.lower()
            if self.extension not in {'.pdf','.docx','.jpg','.jpeg','.png'}:
                raise DocumentError('DOCUMENT_FORMAT_UNSUPPORTED', 'Formato no admitido. Usa PDF, DOCX, JPG o PNG.', 415)
            if self.duplicate is None:
                self.file = self.service.storage.path(self.stage).open('ab')

    def part_data(self, data, start, end):
        if self.part_name == b'metadata':
            self.metadata.extend(data[start:end])
            if len(self.metadata) > 16384:
                raise DocumentError('DOCUMENT_BODY_LIMIT', 'Los metadatos superan el límite.', 413)
        else:
            self.size += end-start
            maximum = self.service.settings.leny_documents_image_bytes if self.extension in {'.png','.jpg','.jpeg'} else self.service.settings.leny_documents_max_file_bytes
            if self.size > maximum:
                raise DocumentError('DOCUMENT_SIZE_LIMIT', 'El archivo supera el tamaño permitido.', 413)
            if self.file:
                self.file.write(data[start:end])

    def part_end(self):
        if self.part_name == b'metadata':
            contract = VersionUpload if self.document_id else DocumentUpload
            self.data = contract.model_validate_json(self.metadata)
            stage, duplicate = self.service.begin_upload(self.actor, self.data, self.document_id)
            if duplicate:
                self.duplicate = stage
            else:
                self.stage = stage
        elif self.file:
            import os
            self.file.flush()
            os.fsync(self.file.fileno())
            self.file.close()
            self.file = None

    def end(self):
        self.complete = True

    def close(self):
        if self.file:
            self.file.close()
            self.file = None


async def receive_upload(request, actor, service, identity=None):
    content_type, options = parse_options_header(request.headers.get('content-type', ''))
    boundary = options.get(b'boundary', b'')
    if content_type != b'multipart/form-data' or not 1 <= len(boundary) <= 70:
        raise DocumentError('DOCUMENT_MULTIPART_INVALID', 'Se requiere una carga multipart válida.', 422)
    # Lease acquired/released on worker threads, physical NullPool connection.
    lease = await anyio.to_thread.run_sync(service.acquire)
    upload = None
    failure_code = 'DOCUMENT_UPLOAD_INTERRUPTED'
    try:
        await anyio.to_thread.run_sync(service.run_leased, lease, service.recover)
        upload = MultipartUpload(service, actor, boundary, identity)
        count = 0
        with anyio.fail_after(settings.leny_documents_upload_seconds):
            iterator = request.stream().__aiter__()
            while True:
                try:
                    with anyio.fail_after(settings.leny_documents_idle_seconds):
                        chunk = await iterator.__anext__()
                except StopAsyncIteration:
                    break
                count += len(chunk)
                if count > settings.leny_documents_max_body_bytes:
                    raise DocumentError('DOCUMENT_BODY_LIMIT', 'La carga supera el límite HTTP.', 413)
                await anyio.to_thread.run_sync(service.run_leased, lease, upload.parser.write, chunk)
                if upload.duplicate is not None:
                    return await anyio.to_thread.run_sync(service.detail, upload.duplicate)
            upload.parser.finalize()
        if not upload.complete or upload.parts != 2 or upload.size == 0:
            raise DocumentError('DOCUMENT_MULTIPART_INVALID', 'La carga está vacía o incompleta.', 422)
        upload.close()
        result = await anyio.to_thread.run_sync(service.run_leased, lease, service.complete_upload, actor, upload.data.request_id,
                                               upload.stage, upload.filename, upload.extension)
        return result
    except DocumentError as error:
        failure_code = error.code
        raise
    except TimeoutError:
        failure_code = 'DOCUMENT_UPLOAD_TIMEOUT'
        raise DocumentError('DOCUMENT_UPLOAD_TIMEOUT', 'La carga superó el tiempo permitido.', 408) from None
    except ClientDisconnect:
        raise DocumentError('DOCUMENT_UPLOAD_INTERRUPTED', 'La carga fue interrumpida.', 408) from None
    finally:
        # Shield disposal from disconnected-client/task cancellation.
        with anyio.CancelScope(shield=True):
            try:
                if upload:
                    upload.close()
                    if upload.data:
                        from functools import partial
                        await anyio.to_thread.run_sync(service.run_leased, lease,
                            partial(service.fail_upload, actor, upload.data.request_id, code=failure_code))
            finally:
                await anyio.to_thread.run_sync(lease.close)


@router.post('')
async def create_document(request: Request, actor=Depends(document_actor), service=Depends(get_document_service)):
    return await receive_upload(request, actor, service)


@router.get('/{identity}', response_model=DocumentDetail)
def detail(identity: UUID, actor=Depends(document_actor), service=Depends(get_document_service)):
    return service.detail(identity)


@router.get('/{identity}/versions', response_model=VersionPage)
def versions(identity: UUID, page: int=Query(1, ge=1), page_size: int=Query(20, ge=1, le=100),
             actor=Depends(document_actor), service=Depends(get_document_service)):
    return service.versions(identity, page, page_size)


@router.post('/{identity}/versions')
async def add_version(identity: UUID, request: Request, actor=Depends(document_actor), service=Depends(get_document_service)):
    return await receive_upload(request, actor, service, identity)


@router.post('/{identity}/change-preview')
async def change_preview(identity: UUID, request: Request, actor=Depends(document_actor), service=Depends(get_document_service)):
    data = await small_json(request, DocumentChange)
    return await mutate(service, service.change_preview, actor, identity, data)


@router.patch('/{identity}')
async def change(identity: UUID, request: Request, actor=Depends(document_actor), service=Depends(get_document_service)):
    data = await small_json(request, DocumentChange)
    return await mutate(service, service.change, actor, identity, data)


@router.post('/{identity}/restore')
async def restore(identity: UUID, request: Request, actor=Depends(document_actor), service=Depends(get_document_service)):
    data = await small_json(request, DocumentChange)
    return await mutate(service, service.change, actor, identity, data, restore=True)


@router.delete('/{identity}')
async def trash(identity: UUID, revision: int=Query(..., ge=1), actor=Depends(document_actor), service=Depends(get_document_service)):
    return await mutate(service, service.trash, actor, identity, revision)


@router.delete('/{identity}/purge')
async def purge(identity: UUID, request: Request, actor=Depends(document_actor), service=Depends(get_document_service)):
    data = await small_json(request, PurgeConfirm)
    return await mutate(service, service.purge, actor, data, document_id=identity)


@router.post('/{identity}/publish')
async def publish(identity: UUID, request: Request, actor=Depends(document_actor), service=Depends(get_document_service)):
    from app.services.leny_rag_publication import PublicationService
    data = await small_json(request, PublicationRequest)
    publication = PublicationService(service.settings, service.sessions)
    try:
        return await anyio.to_thread.run_sync(publication.publish, actor, identity, data)
    finally:
        publication.documents.engine.dispose()


@router.post('/{identity}/unpublish')
async def unpublish(identity: UUID, request: Request, actor=Depends(document_actor), service=Depends(get_document_service)):
    from app.services.leny_rag_publication import PublicationService
    data = await small_json(request, UnpublicationRequest)
    publication = PublicationService(service.settings, service.sessions)
    try:
        return await anyio.to_thread.run_sync(publication.unpublish, actor, identity, data)
    finally:
        publication.documents.engine.dispose()


class AuthorizedFileResponse(StreamingResponse):
    def __init__(self, iterator, context, **kwargs):
        super().__init__(iterator, **kwargs)
        self.file_context = context

    async def __call__(self, scope, receive, send):
        try:
            with anyio.fail_after(settings.leny_documents_upload_seconds):
                await super().__call__(scope, receive, send)
        finally:
            # Includes cancellation/send errors before iterator's first yield.
            self.file_context.__exit__(None, None, None)


def serve_content(service, actor, identity, version_id, preview):
    key, mime, filename = service.content(actor, identity, version_id, preview)
    headers = {'Cache-Control':'no-store', 'X-Content-Type-Options':'nosniff',
               'Content-Security-Policy':"default-src 'none'; sandbox"}
    if not key:
        return JSONResponse({'kind':'download', 'message':'PDF disponible mediante descarga autenticada.'}, headers=headers)
    context = service.storage.open(key)
    handle = context.__enter__()  # authorize and open before response headers
    if preview and mime == 'application/json':
        try:
            return JSONResponse(json.loads(handle.read(1024*1024)), headers=headers)
        finally:
            context.__exit__(None, None, None)
    from urllib.parse import quote
    headers['Content-Disposition'] = ('inline' if preview else 'attachment') + "; filename*=UTF-8''" + quote(filename, safe='')

    def chunks():
        yield from iter(lambda:handle.read(65536), b'')
    return AuthorizedFileResponse(chunks(), context, media_type=mime, headers=headers)


@router.get('/{identity}/versions/{version_id}/content')
def content(identity: UUID, version_id: UUID, actor=Depends(document_actor), service=Depends(get_document_service)):
    return serve_content(service, actor, identity, version_id, False)


@router.get('/{identity}/versions/{version_id}/preview')
def preview(identity: UUID, version_id: UUID, actor=Depends(document_actor), service=Depends(get_document_service)):
    return serve_content(service, actor, identity, version_id, True)
