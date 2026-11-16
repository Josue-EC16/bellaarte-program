"""Administrative library. Documents never enter a chat/model context here."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
from pathlib import Path
import unicodedata
from uuid import UUID, uuid4

from sqlalchemy import create_engine, delete, func, select, text
from sqlalchemy.pool import NullPool

from app.core.audit import register_audit_event
from app.models.account import Cuenta
from app.models.role import Rol
from app.models.leny_documents import (LenyDocument as Doc, LenyDocumentFolder as Folder,
    LenyDocumentReadRole as ReadRole, LenyFolderReadRole as FolderRole,
    LenyDocumentVersion as Version, LenyDocumentOperation as Operation)
from app.schemas.leny_documents import BASE_DOCUMENT_ROLES
from app.services.leny_document_storage import DocumentError, DocumentStorage
from app.services.leny_document_validation import validate_document

LIBRARY_LOCK = 0x4C454E590101
TRANSACTION_GATE = 0x4C454E590102
CURRENT_LEASE = ContextVar('leny_document_lease', default=None)


class LibraryLease:
    def __init__(self, connection):
        self.connection = connection
        self.pid = connection.scalar(text('SELECT pg_backend_pid()'))

    def check(self):
        try:
            if self.connection.closed or self.connection.invalidated or self.connection.scalar(text('SELECT pg_backend_pid()')) != self.pid:
                raise RuntimeError('lost')
        except Exception:
            raise DocumentError('DOCUMENT_LOCK_LOST', 'Se interrumpió la coordinación documental.', 503) from None

    def close(self):
        try:
            self.connection.invalidate()
        finally:
            self.connection.close()


def now():
    return datetime.now(timezone.utc)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, ensure_ascii=True).encode()).hexdigest()


class DocumentService:
    def __init__(self, settings, session_factory):
        self.settings, self.sessions = settings, session_factory
        self.storage = DocumentStorage(settings)
        self.engine = create_engine(settings.effective_database_url, poolclass=NullPool, connect_args={
            'connect_timeout': 5, 'options': '-c statement_timeout=5000',
            'keepalives': 1, 'keepalives_idle': 5, 'keepalives_interval': 2, 'keepalives_count': 2})
        self.initialized = False

    def acquire(self, allow_backup=False):
        if not self.settings.leny_documents_enabled:
            raise DocumentError('DOCUMENT_LIBRARY_DISABLED', 'La biblioteca documental aún no está habilitada.', 503)
        connection = self.engine.connect().execution_options(isolation_level='AUTOCOMMIT')
        try:
            if not connection.scalar(text('SELECT pg_try_advisory_lock(:key)'), {'key': TRANSACTION_GATE}):
                raise DocumentError('DOCUMENT_BUSY', 'La biblioteca está completando una transacción.', 429)
            if not connection.scalar(text('SELECT pg_try_advisory_lock(:key)'), {'key': LIBRARY_LOCK}):
                raise DocumentError('DOCUMENT_BUSY', 'La biblioteca está procesando otra operación. Intenta nuevamente.', 429)
            connection.execute(text('SELECT pg_advisory_unlock(:key)'), {'key':TRANSACTION_GATE})
            from app.core.backup_runtime import is_backup_lock_active
            if not allow_backup and is_backup_lock_active():
                raise DocumentError('BACKUP_IN_PROGRESS', 'El sistema está generando un respaldo.', 503)
            if not self.initialized:
                self.storage.initialize()
                self.initialized = True
            return LibraryLease(connection)
        except BaseException:
            connection.invalidate()
            connection.close()
            raise

    @contextmanager
    def lock(self, allow_backup=False):
        lease = self.acquire(allow_backup)
        token = CURRENT_LEASE.set(lease)
        try:
            yield lease
        finally:
            CURRENT_LEASE.reset(token)
            lease.close()

    def run_leased(self, lease, function, *args):
        token = CURRENT_LEASE.set(lease)
        try:
            lease.check()
            return function(*args)
        finally:
            CURRENT_LEASE.reset(token)

    @contextmanager
    def transaction(self):
        lease = CURRENT_LEASE.get()
        if lease is None:
            raise DocumentError('DOCUMENT_LOCK_REQUIRED', 'La operación requiere coordinación documental.', 503)
        with self.sessions.begin() as db:
            db.execute(text('SET LOCAL statement_timeout = 15000'))
            db.execute(text('SET LOCAL lock_timeout = 5000'))
            # New lease acquisition also needs this gate. Even if the physical
            # lease disappears, a new owner cannot pass our in-flight commit.
            db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key':TRANSACTION_GATE})
            lease.check()
            yield db
            lease.check()

    @contextmanager
    def reading(self):
        with self.sessions() as db:
            db.execute(text('SET LOCAL statement_timeout = 15000'))
            db.execute(text('SET LOCAL lock_timeout = 5000'))
            yield db

    def audit(self, db, actor, action, reference):
        account = db.get(Cuenta, actor.account_id) if actor else None
        register_audit_event(db, action=action, description=action, account=account,
                            reference=str(reference), module='LENY', submodule='DOCUMENTOS',
                            table='leny.documentos', functional_action=action,
                            ip_address=getattr(actor, 'ip_address', None),
                            user_agent=getattr(actor, 'user_agent', None))

    @staticmethod
    def _roles(db, model, column, identity):
        return sorted(db.scalars(select(Rol.codigo).join(model, model.role_id == Rol.id).where(column == identity)).all())

    @staticmethod
    def _set_roles(db, model, column, identity, codes):
        if not set(codes) <= BASE_DOCUMENT_ROLES:
            raise DocumentError('DOCUMENT_INVALID_ROLE', 'Selecciona únicamente roles base.', 422)
        ids = db.scalars(select(Rol.id).where(Rol.codigo.in_(codes), Rol.activo.is_(True))).all()
        if len(ids) != len(set(codes)):
            raise DocumentError('DOCUMENT_INVALID_ROLE', 'Uno de los roles seleccionados no está habilitado.', 422)
        db.execute(delete(model).where(column == identity))
        for role in ids:
            db.add(model(**{column.key: identity, 'role_id': role}))

    def folders(self, actor=None):
        with self.reading() as db:
            items = db.scalars(select(Folder).order_by(Folder.name_key, Folder.id)).all()
            roles = {}
            for identity, code in db.execute(select(FolderRole.folder_id, Rol.codigo).join(Rol, Rol.id == FolderRole.role_id)):
                roles.setdefault(identity, []).append(code)
            return {'items': [dict(id=f.id, parent_id=f.parent_id, name=f.name, description=f.description or '',
                                  role_codes=sorted(roles.get(f.id, []))) for f in items]}

    def save_folder(self, actor, data, folder_id=None):
        with self.transaction() as db:
            folders = {f.id: f for f in db.scalars(select(Folder)).all()}
            if folder_id and folder_id not in folders:
                raise DocumentError('DOCUMENT_NOT_FOUND', 'Carpeta no encontrada.', 404)
            if data.parent_id and data.parent_id not in folders:
                raise DocumentError('DOCUMENT_NOT_FOUND', 'Carpeta de destino no encontrada.', 404)
            if not folder_id and len(folders) >= self.settings.leny_documents_max_folders:
                raise DocumentError('DOCUMENT_FOLDER_LIMIT', 'Se alcanzó el límite de carpetas.')
            identity = folder_id or uuid4()
            parent_map = {key: value.parent_id for key, value in folders.items()}
            parent_map[identity] = data.parent_id
            for key in parent_map:
                seen, current = set(), key
                while current is not None:
                    if current in seen or len(seen) >= self.settings.leny_documents_max_depth:
                        raise DocumentError('DOCUMENT_FOLDER_CYCLE', 'La organización supera la profundidad permitida o crea un ciclo.', 422)
                    seen.add(current)
                    current = parent_map.get(current)
            name_key = unicodedata.normalize('NFKC', data.name).casefold().strip()
            if not 1 <= len(name_key) <= 480:
                raise DocumentError('DOCUMENT_FOLDER_NAME_INVALID', 'El nombre normalizado es demasiado extenso.', 422)
            if any(f.id != identity and f.parent_id == data.parent_id and f.name_key == name_key for f in folders.values()):
                raise DocumentError('DOCUMENT_FOLDER_DUPLICATE', 'Ya existe una carpeta con ese nombre en el destino.')
            folder = folders.get(identity) or Folder(id=identity, created_by=actor.user_id)
            folder.name, folder.name_key, folder.description, folder.parent_id = data.name, name_key, data.description, data.parent_id
            db.add(folder)
            db.flush()
            self._set_roles(db, FolderRole, FolderRole.folder_id, identity, data.role_codes)
            self.audit(db, actor, 'LENY_FOLDER_UPDATED' if folder_id else 'LENY_FOLDER_CREATED', identity)
        return self.folders(actor)

    def delete_folder(self, actor, identity):
        with self.transaction() as db:
            folder = db.get(Folder, identity)
            if folder is None:
                raise DocumentError('DOCUMENT_NOT_FOUND', 'Carpeta no encontrada.', 404)
            if db.scalar(select(func.count()).select_from(Folder).where(Folder.parent_id == identity)) or db.scalar(select(func.count()).select_from(Doc).where(Doc.folder_id == identity)):
                raise DocumentError('DOCUMENT_FOLDER_NOT_EMPTY', 'Primero reubica sus documentos y subcarpetas.')
            db.delete(folder)
            self.audit(db, actor, 'LENY_FOLDER_DELETED', identity)
        return {'deleted': True}

    def _doc(self, db, identity, revision=None):
        doc = db.get(Doc, identity)
        if doc is None:
            raise DocumentError('DOCUMENT_NOT_FOUND', 'Documento no encontrado.', 404)
        if revision is not None and doc.revision != revision:
            raise DocumentError('DOCUMENT_REVISION_CONFLICT', 'El documento cambió. Actualiza la información.')
        return doc

    def _item(self, db, doc):
        return self._items(db, [doc])[0]

    @staticmethod
    def _publication_schema(db):
        return bool(db.scalar(text("SELECT to_regclass('leny.inferencia_estado') IS NOT NULL")))

    def _clear_publication(self, db, doc):
        if self._publication_schema(db):
            doc.published_version_id = doc.published_indexation_id = None
            doc.published_at = doc.published_by = None

    def _items(self, db, docs):
        if not docs:
            return []
        identities = [doc.id for doc in docs]
        publication_schema = self._publication_schema(db)
        aggregates = {identity:(count, latest) for identity, count, latest in db.execute(
            select(Version.document_id, func.count(Version.id), func.max(Version.number)).where(Version.document_id.in_(identities)).group_by(Version.document_id))}
        latest_versions = {version.document_id:version for version in db.scalars(select(Version).where(Version.document_id.in_(identities))
            .distinct(Version.document_id).order_by(Version.document_id, Version.number.desc()))}
        roles = {}
        for identity, code in db.execute(select(ReadRole.document_id, Rol.codigo).join(Rol, Rol.id == ReadRole.role_id).where(ReadRole.document_id.in_(identities))):
            roles.setdefault(identity, []).append(code)
        return [dict(id=doc.id, folder_id=doc.folder_id, title=doc.title, description=doc.description or '',
                    state=doc.state, created_by=doc.created_by, created_at=doc.created_at, updated_at=doc.updated_at,
                    deleted_at=doc.deleted_at, purge_after=doc.purge_after, revision=doc.revision,
                    published_version_id=doc.published_version_id,
                    published_indexation_id=doc.published_indexation_id if publication_schema else None,
                    published_at=doc.published_at if publication_schema else None,
                    published_by=doc.published_by if publication_schema else None,
                    role_codes=sorted(roles.get(doc.id, [])),
                    version_count=aggregates.get(doc.id, (0,None))[0], latest_version_number=aggregates.get(doc.id, (0,None))[1],
                    latest_media_type=latest_versions[doc.id].media_type if doc.id in latest_versions else None,
                    latest_size_bytes=latest_versions[doc.id].size_bytes if doc.id in latest_versions else None,
                    status=latest_versions[doc.id].status if doc.id in latest_versions else 'pending_contextualization') for doc in docs]

    def _version(self, v, db=None):
        ready = False
        if db is not None and self.settings.leny_rag_enabled and self._publication_schema(db) and v.validated_indexation_id:
            from app.models.leny_rag import LenyRagIndexation
            from app.services.leny_rag_publication import indexation_compatible
            index = db.get(LenyRagIndexation, v.validated_indexation_id)
            ready = bool(index and indexation_compatible(index, self.settings))
        return dict(id=v.id, document_id=v.document_id, number=v.number, sha256=v.sha256, size_bytes=v.size_bytes,
                    media_type=v.media_type, original_name=v.original_name, created_at=v.created_at,
                    created_by=v.created_by, status=v.status, preview_available=bool(v.preview_key),
                    validated_indexation_id=v.validated_indexation_id if self.settings.leny_rag_enabled else None,
                    publication_ready=ready)

    def detail(self, identity):
        with self.reading() as db:
            doc = self._doc(db, identity)
            result = self._item(db, doc)
            result['versions'] = [self._version(v, db) for v in db.scalars(select(Version).where(Version.document_id == identity).order_by(Version.number.desc()).limit(100))]
            return result

    def versions(self, identity, page=1, page_size=20):
        with self.reading() as db:
            self._doc(db, identity)
            statement = select(Version).where(Version.document_id == identity)
            return dict(items=[self._version(v, db) for v in db.scalars(statement.order_by(Version.number.desc()).offset((page-1)*page_size).limit(page_size))],
                        total=db.scalar(select(func.count()).select_from(statement.subquery())), page=page, page_size=page_size)

    def list_documents(self, filters, trash=False):
        with self.reading() as db:
            conditions = [Doc.state.in_(['trash', 'purging']) if trash else Doc.state == 'active']
            if filters.folder_id:
                conditions.append(Doc.folder_id == filters.folder_id)
            if filters.search:
                conditions.append(Doc.title.ilike('%' + filters.search.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%', escape='\\'))
            if filters.creator_id:
                conditions.append(Doc.created_by == filters.creator_id)
            if filters.date_from:
                from zoneinfo import ZoneInfo
                conditions.append(Doc.created_at >= datetime.combine(filters.date_from, datetime.min.time(), ZoneInfo('America/La_Paz')))
            if filters.date_to:
                from zoneinfo import ZoneInfo
                conditions.append(Doc.created_at < datetime.combine(filters.date_to + timedelta(days=1), datetime.min.time(), ZoneInfo('America/La_Paz')))
            if filters.format:
                mime = {'pdf':'application/pdf', 'docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'png':'image/png', 'jpg':'image/jpeg', 'jpeg':'image/jpeg'}[filters.format]
                conditions.append(select(Version.id).where(Version.document_id == Doc.id, Version.media_type == mime).exists())
            statement = select(Doc).where(*conditions)
            total = db.scalar(select(func.count()).select_from(statement.subquery()))
            docs = db.scalars(statement.order_by(Doc.updated_at.desc(), Doc.id).offset((filters.page-1)*filters.page_size).limit(filters.page_size)).all()
            return dict(items=self._items(db, docs), total=total, page=filters.page, page_size=filters.page_size)

    def _change_payload(self, db, doc, data):
        destination = db.get(Folder, data.folder_id or doc.folder_id)
        if destination is None:
            raise DocumentError('DOCUMENT_NOT_FOUND', 'Carpeta de destino no encontrada.', 404)
        current = set(self._roles(db, ReadRole, ReadRole.document_id, doc.id))
        defaults = set(self._roles(db, FolderRole, FolderRole.folder_id, destination.id))
        proposed = sorted(set(data.role_codes) if data.role_codes is not None else (current & defaults if destination.id != doc.folder_id or doc.state == 'trash' else current))
        return dict(document_id=str(doc.id), revision=doc.revision, folder_id=str(destination.id),
                    defaults=sorted(defaults), previous=sorted(current), role_codes=proposed)

    def change_preview(self, actor, identity, data):
        with self.transaction() as db:
            doc = self._doc(db, identity, data.revision)
            if doc.state == 'purging':
                raise DocumentError('DOCUMENT_PURGING', 'El documento está en eliminación definitiva.')
            payload = self._change_payload(db, doc, data)
            token = uuid4()
            expiry = now() + timedelta(minutes=5)
            db.add(Operation(id=token, account_id=actor.account_id, user_id=actor.user_id,
                             kind='confirm_change', fingerprint=fingerprint(payload), status='completed',
                             document_id=identity, payload={**payload, 'expires_at': expiry.isoformat()}))
            return dict(token=token, role_codes=payload['role_codes'], broadens=bool(set(payload['role_codes'])-set(payload['previous'])), expires_at=expiry)

    def _confirmation(self, db, actor, token, kind, payload):
        operation = db.get(Operation, token) if token else None
        if (operation is None or operation.account_id != actor.account_id or operation.kind != kind
                or operation.status != 'completed' or operation.fingerprint != fingerprint(payload)
                or datetime.fromisoformat(operation.payload['expires_at']) <= now()):
            raise DocumentError('DOCUMENT_CONFIRMATION_REQUIRED', 'Revisa y confirma los elementos y permisos actuales.')
        return operation

    def change(self, actor, identity, data, restore=False):
        with self.transaction() as db:
            doc = self._doc(db, identity, data.revision)
            if restore:
                if doc.state != 'trash' or doc.purge_after <= now():
                    raise DocumentError('DOCUMENT_RESTORE_EXPIRED', 'El documento ya no puede restaurarse.')
            elif doc.state != 'active':
                raise DocumentError('DOCUMENT_IN_TRASH', 'Restaura el documento antes de editarlo.')
            payload = self._change_payload(db, doc, data)
            if restore or data.folder_id is not None or data.role_codes is not None:
                self._confirmation(db, actor, data.confirmation, 'confirm_change', payload)
            doc.folder_id = UUID(payload['folder_id'])
            if data.title is not None:
                doc.title = data.title
            if data.description is not None:
                doc.description = data.description
            self._set_roles(db, ReadRole, ReadRole.document_id, identity, payload['role_codes'])
            if self.settings.leny_rag_enabled and (data.role_codes is not None or data.folder_id is not None):
                from app.services.leny_rag_service import invalidate_document
                invalidate_document(db, identity)
            if restore:
                doc.state, doc.deleted_at, doc.purge_after, doc.deleted_by = 'active', None, None, None
            doc.updated_by, doc.revision = actor.user_id, doc.revision + 1
            self.audit(db, actor, 'LENY_DOCUMENT_RESTORED' if restore else 'LENY_DOCUMENT_UPDATED', identity)
        return self.detail(identity)

    def trash(self, actor, identity, revision):
        with self.transaction() as db:
            doc = self._doc(db, identity, revision)
            if doc.state != 'active':
                raise DocumentError('DOCUMENT_IN_TRASH', 'El documento ya está en la papelera.')
            self._clear_publication(db, doc)
            doc.state, doc.deleted_at, doc.deleted_by = 'trash', now(), actor.user_id
            doc.purge_after = doc.deleted_at + timedelta(days=self.settings.leny_documents_retention_days)
            if self.settings.leny_rag_enabled:
                from app.services.leny_rag_service import invalidate_document
                invalidate_document(db, identity)
            doc.revision += 1
            self.audit(db, actor, 'LENY_DOCUMENT_TRASHED', identity)
        return self.detail(identity)

    def begin_upload(self, actor, data, document_id=None):
        payload = data.model_dump(mode='json')
        payload['document_id'] = str(document_id) if document_id else None
        intent = fingerprint(payload)
        with self.transaction() as db:
            old = db.get(Operation, data.request_id)
            if old:
                if old.account_id != actor.account_id or old.fingerprint != intent:
                    raise DocumentError('DOCUMENT_IDEMPOTENCY_CONFLICT', 'El identificador ya corresponde a otra solicitud.')
                if old.status == 'completed':
                    if db.get(Doc, old.document_id) is None:
                        raise DocumentError('DOCUMENT_REQUEST_PURGED', 'El documento de esta solicitud fue eliminado definitivamente.')
                    return old.document_id, True
                raise DocumentError('DOCUMENT_REQUEST_INTERRUPTED' if old.status == 'failed' else 'DOCUMENT_REQUEST_IN_PROGRESS',
                                    'La solicitud anterior no terminó. Actualiza el estado y utiliza una solicitud nueva si falló.')
            if document_id:
                doc = self._doc(db, document_id, data.revision)
                if doc.state != 'active':
                    raise DocumentError('DOCUMENT_IN_TRASH', 'No se pueden versionar documentos en papelera.')
                if db.scalar(select(func.count()).select_from(Version).where(Version.document_id == document_id)) >= self.settings.leny_documents_max_versions:
                    raise DocumentError('DOCUMENT_VERSION_LIMIT', 'Se alcanzó el límite de versiones.')
            elif db.scalar(select(func.count()).select_from(Doc)) >= self.settings.leny_documents_max_documents:
                raise DocumentError('DOCUMENT_COUNT_LIMIT', 'Se alcanzó el límite de documentos.')
            elif db.get(Folder, data.folder_id) is None:
                raise DocumentError('DOCUMENT_NOT_FOUND', 'Carpeta no encontrada.', 404)
            if db.scalar(select(func.count()).select_from(Version)) >= self.settings.leny_documents_max_total_versions:
                raise DocumentError('DOCUMENT_VERSION_LIMIT', 'Se alcanzó el límite total de versiones de la biblioteca.')
            admitted = db.scalar(select(func.count()).select_from(Operation).where(Operation.user_id == actor.user_id,
                                 Operation.kind.in_(['upload', 'new_version']), Operation.created_at > now()-timedelta(seconds=self.settings.leny_documents_rate_window_seconds)))
            if admitted >= self.settings.leny_documents_rate_limit:
                self.audit(db, actor, 'LENY_DOCUMENT_RATE_LIMITED', actor.user_id)
                # Audit survives this intentional quota rejection.
                db.commit()
                raise DocumentError('DOCUMENT_RATE_LIMITED', 'Se alcanzó el límite de cargas por usuario. Espera antes de reintentar.', 429)
            stage = self.storage.new_stage()
            payload.update(stage_key=stage, target_document_id=str(document_id or uuid4()), target_version_id=str(uuid4()))
            db.add(Operation(id=data.request_id, account_id=actor.account_id, user_id=actor.user_id,
                             kind='new_version' if document_id else 'upload', fingerprint=intent, status='receiving',
                             document_id=UUID(payload['target_document_id']), version_id=UUID(payload['target_version_id']), payload=payload))
            return stage, False

    def fail_upload(self, actor, request_id, code='DOCUMENT_UPLOAD_INTERRUPTED'):
        with self.transaction() as db:
            operation = db.get(Operation, request_id)
            if operation is None or operation.account_id != actor.account_id or operation.status != 'receiving':
                return
            stage = operation.payload.get('stage_key')
            for key in (stage, operation.payload.get('preview_stage_key'),
                        stage.replace('.blob', '.json') if stage else None, stage.replace('.blob', '.png') if stage else None):
                if key:
                    self.storage.remove(key)
            operation.status, operation.error_code = 'failed', code
            operation.payload = {}
            self.audit(db, actor, code, request_id)

    def complete_upload(self, actor, request_id, stage_key, original_name, extension):
        with self.reading() as db:
            op = db.get(Operation, request_id)
            if op is None or op.account_id != actor.account_id or op.status != 'receiving' or op.payload['stage_key'] != stage_key:
                raise DocumentError('DOCUMENT_REQUEST_CONFLICT', 'La carga no está disponible.')
            expected = op.payload['sha256'].lower()
            size = self.storage.path(stage_key).stat().st_size
        maximum = self.settings.leny_documents_image_bytes if extension in {'.png', '.jpg', '.jpeg'} else self.settings.leny_documents_max_file_bytes
        if not 0 < size <= maximum:
            raise DocumentError('DOCUMENT_SIZE_LIMIT', 'El tamaño del archivo no está permitido.', 413)
        if self.storage.sha256(stage_key) != expected:
            raise DocumentError('DOCUMENT_HASH_MISMATCH', 'La carga está incompleta o cambió su contenido.', 422)
        used = self.stored_bytes()
        if used + size + 16*1024*1024 > self.settings.leny_documents_capacity_bytes or self.storage.free_space() < self.settings.leny_documents_min_free_bytes + 32*1024*1024:
            raise DocumentError('DOCUMENT_CAPACITY', 'No hay capacidad documental suficiente.', 409)
        result = validate_document(self.storage, stage_key, extension, self.settings)
        with self.transaction() as db:
            operation = db.get(Operation, request_id)
            version_id = operation.version_id
            payload = dict(operation.payload)
            payload.update(result, size_bytes=size, original_name=original_name,
                           storage_key=f'versions/{version_id.hex}.blob',
                           preview_key=f'previews/{version_id.hex}.json' if extension == '.docx' else f'previews/{version_id.hex}.png')
            if not result['preview_type']:
                payload['preview_key'] = None
            operation.payload, operation.status = payload, 'staged'
        self._commit_stage(request_id, actor)
        with self.reading() as db:
            identity = db.get(Operation, request_id).document_id
        return self.detail(identity)

    def stored_bytes(self):
        with self.reading() as db:
            return db.scalar(select(func.coalesce(func.sum(Version.size_bytes + Version.preview_size_bytes), 0)))

    def _commit_stage(self, request_id, actor=None):
        with self.transaction() as db:
            operation = db.get(Operation, request_id)
            if not operation or operation.status != 'staged':
                return
            payload = operation.payload
            doc = db.get(Doc, operation.document_id)
            if operation.kind == 'new_version':
                doc = self._doc(db, operation.document_id, payload['revision'])
                if doc.state != 'active':
                    raise DocumentError('DOCUMENT_IN_TRASH', 'La versión no puede completarse en papelera.')
            else:
                if doc is not None:
                    raise DocumentError('DOCUMENT_ID_CONFLICT', 'El documento ya existe.')
                if db.get(Folder, UUID(payload['folder_id'])) is None:
                    raise DocumentError('DOCUMENT_FOLDER_MISSING', 'La carpeta de la carga ya no existe.')
                doc = Doc(id=operation.document_id, folder_id=UUID(payload['folder_id']), title=payload['title'],
                          description=payload['description'], created_by=operation.user_id, revision=1)
                db.add(doc)
                db.flush()
                codes = self._roles(db, FolderRole, FolderRole.folder_id, doc.folder_id)
                self._set_roles(db, ReadRole, ReadRole.document_id, doc.id, codes)
            number = (db.scalar(select(func.max(Version.number)).where(Version.document_id == doc.id)) or 0) + 1
            destination = self.storage.path(payload['storage_key'])
            if not destination.exists():
                self.storage.promote(payload['stage_key'], payload['storage_key'])
            if self.storage.sha256(payload['storage_key']) != payload['sha256'].lower():
                raise DocumentError('DOCUMENT_STORAGE_INTEGRITY', 'La versión requiere revisión de integridad.', 503)
            preview_bytes = 0
            if payload['preview_key']:
                if not self.storage.path(payload['preview_key']).exists():
                    self.storage.promote(payload['preview_stage_key'], payload['preview_key'])
                preview_bytes = self.storage.path(payload['preview_key']).stat().st_size
            db.add(Version(id=operation.version_id, document_id=doc.id, number=number, storage_key=payload['storage_key'],
                           sha256=payload['sha256'].lower(), size_bytes=payload['size_bytes'], media_type=payload['media_type'],
                           original_name=payload['original_name'], preview_key=payload['preview_key'],
                           preview_type=payload['preview_type'], preview_size_bytes=preview_bytes,
                           created_by=operation.user_id, status='pending_contextualization'))
            if operation.kind == 'new_version':
                doc.revision += 1
                doc.updated_by = operation.user_id
            operation.status, operation.error_code = 'completed', None
            # Only the durable UUID/fingerprint result is needed for replay.
            # Do not retain duplicate titles/descriptions/paths after completion.
            operation.payload = {}
            self.audit(db, actor, 'LENY_DOCUMENT_VERSION_CREATED', doc.id)

    def purge_preview(self, actor, data):
        with self.transaction() as db:
            query = select(Doc).where(Doc.state == 'trash').order_by(Doc.id)
            if not data.all:
                query = query.where(Doc.id.in_(data.ids))
            total = db.scalar(select(func.count()).select_from(query.subquery()))
            docs = db.scalars(query.limit(1000)).all()
            if not data.all and {d.id for d in docs} != set(data.ids):
                raise DocumentError('DOCUMENT_PURGE_SELECTION', 'Revisa la selección actual de papelera.')
            payload = {'items': [{'id':str(d.id), 'revision':d.revision} for d in docs]}
            token, expiry = uuid4(), now()+timedelta(minutes=5)
            db.add(Operation(id=token, account_id=actor.account_id, user_id=actor.user_id, kind='confirm_purge',
                             fingerprint=fingerprint(payload), status='completed', payload={**payload, 'expires_at':expiry.isoformat()}))
            return dict(token=token, count=len(docs), remaining=max(0, total-len(docs)), items=[dict(id=d.id, title=d.title) for d in docs], expires_at=expiry)

    def purge(self, actor, data, document_id=None):
        with self.transaction() as db:
            old = db.get(Operation, data.request_id)
            intent = fingerprint({'confirmation':str(data.confirmation), 'document_id':str(document_id)})
            if old:
                if old.account_id != actor.account_id or old.kind != 'purge' or old.fingerprint != intent:
                    raise DocumentError('DOCUMENT_IDEMPOTENCY_CONFLICT', 'El identificador corresponde a otra operación.')
                if old.status == 'completed':
                    return {'purged':len(old.payload['items'])}
                if old.status == 'purging':
                    items = old.payload['items']
                else:
                    raise DocumentError('DOCUMENT_REQUEST_FAILED', 'La operación anterior falló.')
            else:
                confirmation = db.get(Operation, data.confirmation)
                if confirmation is None or confirmation.kind != 'confirm_purge' or confirmation.account_id != actor.account_id:
                    raise DocumentError('DOCUMENT_CONFIRMATION_REQUIRED', 'Revisa la selección antes de eliminar.')
                items = confirmation.payload['items']
                payload = {'items':items}
                self._confirmation(db, actor, data.confirmation, 'confirm_purge', payload)
                if document_id and [str(document_id)] != [item['id'] for item in items]:
                    raise DocumentError('DOCUMENT_PURGE_SELECTION', 'La confirmación no corresponde al documento.')
                for item in items:
                    doc = self._doc(db, UUID(item['id']), item['revision'])
                    if doc.state != 'trash':
                        raise DocumentError('DOCUMENT_PURGE_SELECTION', 'La selección de papelera cambió.')
                    doc.state, doc.revision = 'purging', doc.revision+1
                db.add(Operation(id=data.request_id, account_id=actor.account_id, user_id=actor.user_id, kind='purge',
                                 fingerprint=intent, status='purging', payload=payload))
                self.audit(db, actor, 'LENY_DOCUMENT_PURGE_STARTED', data.request_id)
        self._finish_purge(data.request_id, actor)
        return {'purged':len(items)}

    def _finish_purge(self, request_id, actor=None):
        with self.transaction() as db:
            operation = db.get(Operation, request_id)
            if not operation or operation.status != 'purging':
                return
            for item in operation.payload['items']:
                identity = UUID(item['id'])
                doc = db.get(Doc, identity)
                if doc is None:
                    continue
                if doc.state != 'purging':
                    raise DocumentError('DOCUMENT_PURGE_CONFLICT', 'La eliminación requiere reconciliación.')
                self._clear_publication(db, doc)
                versions = db.scalars(select(Version).where(Version.document_id == identity)).all()
                for version in versions:
                    if self.settings.leny_rag_enabled:
                        from app.services.leny_rag_service import purge_derived
                        purge_derived(db, version.id)
                    self.storage.remove(version.storage_key)
                    if version.preview_key:
                        self.storage.remove(version.preview_key)
                    db.delete(version)
                db.flush()
                db.delete(doc)
                self.audit(db, actor, 'LENY_DOCUMENT_PURGED', identity)
            operation.status, operation.error_code = 'completed', None

    def content(self, actor, identity, version_id, preview=False):
        # Content authorization is a bounded read; its audit insert does not
        # mutate library lifecycle or need the upload/backup write lease.
        with self.reading() as db:
            doc = self._doc(db, identity)
            if doc.state != 'active':
                raise DocumentError('DOCUMENT_IN_TRASH', 'Restaura el documento antes de abrir su contenido.', 409)
            version = db.get(Version, version_id)
            if version is None or version.document_id != identity:
                raise DocumentError('DOCUMENT_NOT_FOUND', 'Versión no encontrada.', 404)
            self.audit(db, actor, 'LENY_DOCUMENT_PREVIEWED' if preview else 'LENY_DOCUMENT_DOWNLOADED', identity)
            if preview and not version.preview_key:
                result = (None, 'application/json', version.original_name)
            else:
                result = (version.preview_key if preview else version.storage_key,
                          version.preview_type if preview else version.media_type, version.original_name)
            db.commit()
            return result

    def recover(self):
        """Caller holds the exclusive library lease; no active upload can be swept."""
        with self.reading() as db:
            pending = db.scalars(select(Operation.id).where(Operation.status.in_(['receiving','staged','purging'])).order_by(Operation.created_at).limit(20)).all()
        for identity in pending:
            try:
                with self.reading() as db:
                    op = db.get(Operation, identity)
                    status, payload = op.status, dict(op.payload)
                    from types import SimpleNamespace
                    actor = SimpleNamespace(account_id=op.account_id, user_id=op.user_id)
                if status == 'staged':
                    self._commit_stage(identity, actor)
                elif status == 'purging':
                    self._finish_purge(identity, actor)
                else:
                    self.fail_upload(actor, identity)
            except Exception:
                logging.getLogger(__name__).warning('LENY_DOCUMENT_RECOVERY_DEFERRED')
        with self.reading() as db:
            referenced = {key for op in db.scalars(select(Operation).where(Operation.status.in_(['receiving','staged'])))
                          for key in (op.payload.get('stage_key'), op.payload.get('preview_stage_key')) if key}
        for file in (self.storage.root / 'staging').iterdir():
            key = 'staging/' + file.name
            if key not in referenced:
                try:
                    self.storage.remove(key)
                except DocumentError:
                    logging.getLogger(__name__).warning('LENY_DOCUMENT_UNKNOWN_TEMPORARY')
        with self.reading() as db:
            incomplete = db.scalar(select(func.count()).select_from(Operation).where(Operation.status.in_(['receiving','staged','purging'])))
        if incomplete:
            raise DocumentError('DOCUMENT_RECOVERY_REQUIRED', 'Hay operaciones documentales pendientes de recuperación. Intenta nuevamente.', 503)

    def expire(self):
        with self.transaction() as db:
            expired = db.scalars(select(Doc).where(Doc.state == 'trash', Doc.purge_after <= now()).order_by(Doc.purge_after).limit(20)).all()
            for doc in expired:
                identity = uuid4()
                payload = {'items':[{'id':str(doc.id), 'revision':doc.revision}]}
                doc.state, doc.revision = 'purging', doc.revision+1
                db.add(Operation(id=identity, account_id=db.scalar(select(Cuenta.id).where(Cuenta.usuario_id == doc.deleted_by)),
                                 user_id=doc.deleted_by, kind='purge_expired', fingerprint=fingerprint(payload), status='purging', payload=payload))
                self.audit(db, None, 'LENY_DOCUMENT_RETENTION_EXPIRED', doc.id)
        self.recover()
