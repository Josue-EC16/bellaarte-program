"""Durable administrative processing; all writes share the library backup gate."""
from __future__ import annotations

from datetime import timedelta
import hashlib
import math
from pathlib import Path
import shutil
from types import SimpleNamespace
from threading import Lock
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select, text

from app.models.account import Cuenta
from app.models.leny_documents import LenyDocument as Doc, LenyDocumentVersion as Version
from app.models.leny_rag import (LenyRagJob as Job, LenyRagIndexation as Indexation,
    LenyRagFragment as Fragment, LenyRagEmbedding as Embedding, LenyRagWorker as Worker)
from app.services.auth_service import get_account_by_id
from app.services.leny_document_service import DocumentService, now
from app.services.leny_rag_common import (RagError, TERMINAL, MESSAGES, canonical_hash,
    pipeline_config, ocr_paths, PIPELINE_VERSION, CHUNKING_VERSION, OCR_VERSION)


class RagService:
    def __init__(self, settings, session_factory):
        self.settings, self.sessions = settings, session_factory
        self.documents = DocumentService(settings, session_factory)
        self._policy_lock, self._policy_stamp, self._enforcer = Lock(), None, None

    def require_enabled(self):
        if not self.settings.leny_rag_enabled or not self.settings.leny_documents_enabled:
            raise RagError('RAG_DISABLED')

    def actor(self, db, actor):
        account = get_account_by_id(db, actor.account_id)
        if (not account or not account.is_active or account.must_change_password or not account.usuario
                or account.usuario_id != actor.user_id or not account.usuario.activo
                or not account.rol.activo or account.rol.codigo != 'ADMIN'):
            raise RagError('RAG_INVALIDATED', 403)
        import casbin
        security = Path(__file__).resolve().parents[1] / 'security'
        with self._policy_lock:
            stamp = tuple((security/name).stat().st_mtime_ns for name in ('model.conf','policy.csv'))
            if stamp != self._policy_stamp:
                self._enforcer = casbin.Enforcer(str(security / 'model.conf'), str(security / 'policy.csv'))
                self._policy_stamp = stamp
            if not self._enforcer.enforce(account.rol.codigo, 'leny:admin', 'use'):
                raise RagError('RAG_INVALIDATED', 403)
        return account

    def eligible(self, db, doc_id, version_id):
        doc, version = db.get(Doc, doc_id), db.get(Version, version_id)
        if not doc or not version or version.document_id != doc.id:
            raise RagError('RAG_NOT_FOUND', 404)
        if doc.state != 'active':
            raise RagError('RAG_INVALIDATED', 409)
        return doc, version

    def snapshot(self, job, indexation=None):
        return dict(id=job.id, document_id=job.document_id, version_id=job.version_id,
                    source_document_id=job.source_document_id, source_version_id=job.source_version_id,
                    status=job.status, stage=job.stage, progress=job.progress, attempts=job.attempts,
                    cancel_requested=job.cancel_requested, indexation_id=job.indexation_id,
                    retry_of=job.retry_of_id, error_code=job.error_code,
                    safe_message=MESSAGES.get(job.error_code, 'No se pudo procesar el documento de forma segura. Revisa el formato y los límites.') if job.error_code else None,
                    created_at=job.created_at, updated_at=job.updated_at, finished_at=job.completed_at,
                    model=self.settings.leny_rag_model, dimension=1024,
                    indexation_status=indexation.status if indexation else None,
                    chunk_count=indexation.chunk_count if indexation else None,
                    warnings=indexation.coverage.get('warnings', []) if indexation else [])

    def get(self, identity):
        self.require_enabled()
        with self.documents.reading() as db:
            job = db.get(Job, identity)
            if not job:
                raise RagError('RAG_NOT_FOUND', 404)
            return self.snapshot(job, db.get(Indexation, job.indexation_id) if job.indexation_id else None)

    def history(self, doc_id, version_id, page=1, page_size=5):
        self.require_enabled()
        with self.documents.reading() as db:
            self.eligible(db, doc_id, version_id)
            condition = (Job.source_document_id == doc_id, Job.source_version_id == version_id)
            total = db.scalar(select(func.count()).select_from(Job).where(*condition))
            jobs = db.scalars(select(Job).where(*condition).order_by(Job.created_at.desc(), Job.id.desc())
                              .offset((page-1)*page_size).limit(page_size)).all()
            ids = {job.indexation_id for job in jobs if job.indexation_id}
            indexes = {i.id:i for i in db.scalars(select(Indexation).where(Indexation.id.in_(ids)))} if ids else {}
            return dict(items=[self.snapshot(job, indexes.get(job.indexation_id)) for job in jobs],
                        total=total, page=page, page_size=page_size)

    def submit(self, actor, doc_id, version_id, data):
        self.require_enabled()
        config = pipeline_config(self.settings)
        digest = canonical_hash(config)
        intent = canonical_hash(dict(document_id=str(doc_id), version_id=str(version_id),
                                     action=data.action, retry_of=str(data.retry_of) if data.retry_of else None))
        with self.documents.lock(), self.documents.transaction() as db:
            self.actor(db, actor)
            previous = db.get(Job, data.request_id)
            if previous:
                if previous.account_id != actor.account_id or previous.fingerprint != intent:
                    raise RagError('RAG_REQUEST_CONFLICT', 409)
                if previous.status in {'failed', 'cancelled', 'invalidated'}:
                    raise RagError('RAG_REQUEST_TERMINAL', 409)
                return self.snapshot(previous), False
            _, version = self.eligible(db, doc_id, version_id)
            if version.validated_indexation_id and data.action == 'contextualize':
                raise RagError('RAG_ALREADY_VALIDATED', 409)
            if data.action == 'retry':
                parent = db.get(Job, data.retry_of) if data.retry_of else None
                if not parent or parent.source_version_id != version_id or parent.source_document_id != doc_id or parent.status not in {'failed','cancelled','invalidated'}:
                    raise RagError('RAG_RETRY_INVALID', 409)
            elif data.retry_of:
                raise RagError('RAG_RETRY_INVALID', 422)
            if db.scalar(select(Job.id).where(Job.source_version_id == version_id, Job.status.in_(['queued','running'])).limit(1)):
                raise RagError('RAG_ALREADY_ACTIVE', 409)
            count = db.scalar(select(func.count()).select_from(Job).where(Job.account_id == actor.account_id,
                                    Job.created_at >= now()-timedelta(seconds=60)))
            if count >= self.settings.leny_rag_rate_limit:
                self.documents.audit(db, actor, 'LENY_RAG_RATE_LIMITED', data.request_id)
                db.commit()
                raise RagError('RAG_RATE_LIMITED', 429)
            if db.scalar(select(func.count()).select_from(Job).where(Job.status.in_(['queued','running']))) >= self.settings.leny_rag_queue_limit:
                raise RagError('RAG_QUEUE_FULL', 429)
            if not self.local_dependencies()['ready']:
                raise RagError('RAG_NOT_READY')
            job = Job(id=data.request_id, account_id=actor.account_id, user_id=actor.user_id,
                      document_id=doc_id, version_id=version_id, source_document_id=doc_id,
                      source_version_id=version_id, sha256=version.sha256, action=data.action,
                      fingerprint=intent, pipeline_fingerprint=digest, retry_of_id=data.retry_of,
                      status='queued', stage='queued', progress={})
            db.add(job)
            self.documents.audit(db, actor, 'LENY_RAG_REQUESTED', job.id)
            db.flush()
            return self.snapshot(job), True

    def cancel(self, actor, identity):
        self.require_enabled()
        with self.documents.lock(), self.documents.transaction() as db:
            self.actor(db, actor)
            job = db.get(Job, identity)
            if not job:
                raise RagError('RAG_NOT_FOUND', 404)
            if job.status not in TERMINAL:
                job.cancel_requested = True
                if job.status == 'queued':
                    self._terminal(db, job, 'cancelled', 'RAG_CANCELLED')
                self.documents.audit(db, actor, 'LENY_RAG_CANCEL_REQUESTED', job.id)
            db.flush()
            return self.snapshot(job)

    def local_dependencies(self):
        tess, data = ocr_paths(self.settings)
        native = tess.is_file() and all((data / (language+'.traineddata')).is_file() for language in ('spa','eng','osd'))
        try:
            import pypdfium2  # noqa:F401
            parsers = True
        except (ImportError, OSError):
            parsers = False
        return dict(tesseract=native, parsers=parsers, ready=native and parsers)

    def status(self):
        dependencies = self.local_dependencies()
        available = False
        uncertain = False
        vector = False
        if self.settings.leny_rag_enabled:
            with self.documents.reading() as db:
                vector = db.execute(text("SELECT EXISTS(SELECT 1 FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='vector' AND e.extversion='0.8.7' AND n.nspname='leny')")).scalar_one()
                available = bool(db.scalar(select(Worker.id).where(Worker.stopped_at.is_(None),
                                         Worker.heartbeat_at >= now()-timedelta(seconds=self.settings.leny_rag_lease_seconds)).limit(1)))
                uncertain = bool(db.scalar(select(Worker.id).where(Worker.unsafe_reason.is_not(None)).limit(1)))
        dependencies['pgvector'] = vector
        with self.documents.reading() as db:
            publication_ready=bool(self.settings.leny_documents_enabled and self.settings.leny_rag_enabled and
                db.scalar(text("SELECT to_regclass('leny.inferencia_estado') IS NOT NULL")))
        ready = self.settings.leny_rag_enabled and dependencies['ready'] and vector and not uncertain
        code = 'RAG_INFERENCE_UNCERTAIN' if uncertain else 'RAG_DISABLED' if not self.settings.leny_rag_enabled else 'RAG_NOT_READY' if not ready else 'RAG_READY' if available else 'RAG_WORKER_STOPPED'
        return dict(enabled=self.settings.leny_rag_enabled, ready=ready, worker_available=available,
                    publication_ready=publication_ready,retrieval_ready=publication_ready and self.settings.leny_rag_chat_enabled,
                    model=self.settings.leny_rag_model, dimension=1024, cpu_only=True,
                    dependencies=dependencies, code=code,
                    message=MESSAGES.get(code, 'El procesador está disponible.' if available else 'En espera de procesador. Inicia el worker manualmente.'))

    def _terminal(self, db, job, state, code=None):
        job.status, job.stage, job.error_code, job.completed_at = state, state, code, now()
        job.lease_until, job.run_token = None, None
        if job.indexation_id:
            index = db.get(Indexation, job.indexation_id)
            if index and index.status == 'staging':
                index.status = 'failed' if state == 'failed' else state
        version = db.get(Version, job.version_id) if job.version_id else None
        if version:
            version.status = 'pending_publication' if version.validated_indexation_id else 'contextualization_error' if state == 'failed' else 'pending_contextualization'
        self.documents.audit(db, SimpleNamespace(account_id=job.account_id, user_id=job.user_id), 'LENY_RAG_' + state.upper(), job.id)

    def register(self, identity, host_instance, pid):
        self.require_enabled()
        with self.documents.lock(), self.documents.transaction() as db:
            # A previous in-flight HTTP request may still be executing in Ollama.
            # Preserve quarantine; do not equate release of PostgreSQL lock with
            # proof that the provider stopped computing.
            unsafe = db.scalars(select(Worker).where(Worker.provider_inflight.is_(True))).all()
            for worker in unsafe:
                worker.unsafe_reason = 'RAG_INFERENCE_UNCERTAIN'
            if unsafe:
                db.commit()
                raise RagError('RAG_INFERENCE_UNCERTAIN')
            for old in db.scalars(select(Worker).where(Worker.stopped_at.is_(None))):
                old.stopped_at = now()
            db.add(Worker(id=identity, host_instance=host_instance, pid=pid, heartbeat_at=now()))
            # Exclusive worker lease guarantees there is no live claimant.
            for job in db.scalars(select(Job).where(Job.status == 'running')):
                if job.cancel_requested:
                    self._terminal(db, job, 'cancelled', 'RAG_CANCELLED')
                elif job.attempts >= self.settings.leny_rag_max_attempts:
                    self._terminal(db, job, 'failed', 'RAG_OPERATION_FAILED')
                else:
                    job.status, job.stage, job.worker_id, job.run_token, job.lease_until = 'queued', 'queued', None, None, None
            self.documents.audit(db, None, 'LENY_RAG_WORKER_STARTED', identity)

    def heartbeat(self, identity, job_id=None, token=None, *, provider_inflight=None, unsafe_reason=None):
        with self.documents.lock(), self.documents.transaction() as db:
            worker = db.get(Worker, identity)
            if not worker or worker.stopped_at:
                raise RagError('RAG_LOCK_LOST')
            worker.heartbeat_at = now()
            worker.current_job_id = job_id
            if provider_inflight is not None:
                worker.provider_inflight = provider_inflight
                worker.provider_digest = self.settings.leny_rag_model_digest if provider_inflight else None
            if unsafe_reason:
                worker.unsafe_reason = unsafe_reason
            if job_id:
                job = db.get(Job, job_id)
                if provider_inflight is None and job and job.status != 'running':
                    return
                if provider_inflight is False and job and job.status in TERMINAL and job.worker_id == identity:
                    return  # Confirmed HTTP completion from this worker only.
                if provider_inflight is None:
                    self.check_claim(db, job, token)
                elif not job or job.status != 'running' or job.run_token != token:
                    raise RagError('RAG_LOCK_LOST')
                job.lease_until = now()+timedelta(seconds=self.settings.leny_rag_lease_seconds)

    def check_claim(self, db, job, token):
        if not job or job.status != 'running' or job.run_token != token or not job.lease_until or job.lease_until < now():
            raise RagError('RAG_LOCK_LOST')
        if job.cancel_requested:
            raise RagError('RAG_CANCELLED', 409)
        actor = SimpleNamespace(account_id=job.account_id, user_id=job.user_id)
        self.actor(db, actor)
        _, version = self.eligible(db, job.source_document_id, job.source_version_id)
        if version.sha256 != job.sha256:
            raise RagError('RAG_INTEGRITY')
        return version

    def check(self, job_id, token):
        with self.documents.reading() as db:
            return self.check_claim(db, db.get(Job, job_id), token).sha256

    def claim(self, worker_id):
        config = pipeline_config(self.settings)
        with self.documents.lock(), self.documents.transaction() as db:
            worker = db.get(Worker, worker_id)
            if not worker or worker.stopped_at is not None or worker.unsafe_reason is not None:
                raise RagError('RAG_LOCK_LOST')
            if db.scalar(select(Job.id).where(Job.status == 'running').limit(1)):
                return None
            job = db.scalar(select(Job).where(Job.status == 'queued').order_by(Job.created_at, Job.id).with_for_update(skip_locked=True).limit(1))
            if job is None:
                return None
            try:
                self.actor(db, SimpleNamespace(account_id=job.account_id, user_id=job.user_id))
                _, version = self.eligible(db, job.source_document_id, job.source_version_id)
                if job.pipeline_fingerprint != canonical_hash(config) or version.sha256 != job.sha256:
                    raise RagError('RAG_MODEL_CHANGED')
            except RagError:
                self._terminal(db, job, 'invalidated', 'RAG_INVALIDATED')
                return None
            job.status, job.stage, job.worker_id, job.run_token = 'running', 'extracting', worker_id, uuid4()
            job.lease_until = now()+timedelta(seconds=self.settings.leny_rag_lease_seconds)
            job.attempts += 1
            job.started_at = job.started_at or now()
            index = db.get(Indexation, job.indexation_id) if job.indexation_id else None
            if not index or index.status != 'staging':
                index = Indexation(id=uuid4(), version_id=version.id, model=self.settings.leny_rag_model,
                                   model_digest=self.settings.leny_rag_model_digest, dimension=1024,
                                   pipeline_version=PIPELINE_VERSION, chunking_version=CHUNKING_VERSION,
                                   ocr_version=OCR_VERSION, config=config, status='staging')
                db.add(index)
                db.flush()
                job.indexation_id = index.id
            if not version.validated_indexation_id:
                version.status = 'contextualizing'
            db.flush()
            return dict(id=job.id, token=job.run_token, indexation_id=index.id, version_id=version.id,
                        document_id=version.document_id, sha256=version.sha256, storage_key=version.storage_key,
                        size_bytes=version.size_bytes, media_type=version.media_type)

    def progress(self, identity, token, stage, values):
        allowed = {'pages_total','pages_done','ocr_pages_total','ocr_pages_done','chunks_total','chunks_done','seconds','warnings'}
        values = {k:v for k,v in values.items() if k in allowed}
        with self.documents.lock(), self.documents.transaction() as db:
            job = db.get(Job, identity)
            self.check_claim(db, job, token)
            job.stage, job.progress = stage, {**job.progress, **values}

    def fragments(self, claim, fragments, coverage):
        if not fragments or len(fragments) > self.settings.leny_rag_max_chunks:
            raise RagError('RAG_INTEGRITY')
        for ordinal, fragment in enumerate(fragments):
            value = fragment.get('text')
            if (not isinstance(value,str) or not value.strip() or fragment.get('ordinal') != ordinal
                    or fragment.get('sha256') != hashlib.sha256(value.encode()).hexdigest()
                    or fragment.get('char_count') != len(value) or fragment.get('byte_count') != len(value.encode())
                    or len(value) > self.settings.leny_rag_chunk_chars or len(value.encode()) > self.settings.leny_rag_chunk_bytes):
                raise RagError('RAG_INTEGRITY')
        with self.documents.lock(), self.documents.transaction() as db:
            job = db.get(Job, claim['id'])
            self.check_claim(db, job, claim['token'])
            index = db.get(Indexation, job.indexation_id)
            existing = db.scalars(select(Fragment).where(Fragment.indexation_id == index.id).order_by(Fragment.ordinal)).all()
            if existing:
                if len(existing) != len(fragments) or any((old.sha256, old.locator, old.text) != (new['sha256'],new['locator'],new['text']) for old,new in zip(existing,fragments)):
                    raise RagError('RAG_INTEGRITY')
            else:
                total = db.scalar(select(func.count()).select_from(Fragment))
                used = db.scalar(text("SELECT pg_total_relation_size('leny.rag_fragmentos') + pg_total_relation_size('leny.rag_embeddings')"))
                if total + len(fragments) > self.settings.leny_rag_max_total_chunks or used + sum(f['byte_count']+4500 for f in fragments) > self.settings.leny_rag_capacity_bytes:
                    raise RagError('RAG_CAPACITY', 409)
                for fragment in fragments:
                    db.add(Fragment(id=uuid4(), indexation_id=index.id, **fragment))
            index.chunk_count, index.coverage = len(fragments), coverage
            job.progress = {**job.progress, 'chunks_total':len(fragments)}

    def pending_fragments(self, index_id):
        with self.documents.reading() as db:
            rows = db.execute(select(Fragment.id, Fragment.text).outerjoin(Embedding, Embedding.fragment_id == Fragment.id)
                              .where(Fragment.indexation_id == index_id, Embedding.fragment_id.is_(None)).order_by(Fragment.ordinal)).all()
            return [(row.id,row.text) for row in rows]

    def save_vectors(self, claim, rows, vectors):
        if len(rows) != len(vectors) or any(len(v) != 1024 or not all(math.isfinite(x) for x in v) or not any(v) for v in vectors):
            raise RagError('RAG_PROVIDER_RESPONSE')
        with self.documents.lock(), self.documents.transaction() as db:
            job = db.get(Job, claim['id'])
            self.check_claim(db, job, claim['token'])
            for (identity, _), vector in zip(rows, vectors):
                fragment = db.get(Fragment, identity)
                if fragment is None or fragment.indexation_id != job.indexation_id:
                    raise RagError('RAG_INTEGRITY')
                previous = db.get(Embedding, identity)
                if previous is None:
                    db.add(Embedding(fragment_id=identity, indexation_id=job.indexation_id, embedding=vector))
            db.flush()
            count = db.scalar(select(func.count()).select_from(Embedding).where(Embedding.indexation_id == job.indexation_id))
            job.stage, job.progress = 'embedding', {**job.progress, 'chunks_done':count}

    def finish(self, claim):
        with self.documents.lock(), self.documents.transaction() as db:
            job = db.get(Job, claim['id'])
            version = self.check_claim(db, job, claim['token'])
            index = db.get(Indexation, job.indexation_id)
            chunks = db.scalar(select(func.count()).select_from(Fragment).where(Fragment.indexation_id == index.id))
            vectors = db.scalar(select(func.count()).select_from(Embedding).where(Embedding.indexation_id == index.id))
            if not chunks or chunks != vectors or chunks != index.chunk_count or not index.coverage.get('complete'):
                raise RagError('RAG_INTEGRITY')
            if index.config != pipeline_config(self.settings):
                raise RagError('RAG_MODEL_CHANGED')
            index.status, index.validated_at = 'validated', now()
            version.validated_indexation_id, version.status = index.id, 'pending_publication'
            job.status, job.stage, job.completed_at, job.lease_until = 'completed', 'completed', now(), None
            job.run_token = None
            self.documents.audit(db, SimpleNamespace(account_id=job.account_id, user_id=job.user_id), 'LENY_RAG_VALIDATED', job.id)

    def fail(self, claim, code):
        with self.documents.lock(), self.documents.transaction() as db:
            job = db.get(Job, claim['id'])
            if job and job.status == 'running' and job.run_token == claim['token']:
                state = 'cancelled' if code == 'RAG_CANCELLED' else 'invalidated' if code == 'RAG_INVALIDATED' else 'failed'
                self._terminal(db, job, state, code)

    def defer(self, claim, code):
        """Missing/local provider resources leave a durable, explicit waiting job."""
        with self.documents.lock(), self.documents.transaction() as db:
            job = db.get(Job, claim['id'])
            self.check_claim(db, job, claim['token'])
            job.status, job.stage, job.error_code = 'queued', 'waiting_resources', code
            job.worker_id, job.run_token, job.lease_until = None, None, None
            job.attempts = max(0, job.attempts-1)

    def stopped(self, identity):
        with self.documents.lock(), self.documents.transaction() as db:
            worker = db.get(Worker, identity)
            if worker:
                worker.stopped_at = now()
                worker.current_job_id = None


def invalidate_document(db, document_id):
    """Called inside the existing document transaction/lease."""
    for job in db.scalars(select(Job).where(Job.document_id == document_id, Job.status.in_(['queued','running']))):
        job.cancel_requested = True
        if job.status == 'queued':
            job.status, job.stage, job.error_code, job.completed_at = 'invalidated','invalidated','RAG_INVALIDATED',now()


def purge_derived(db, version_id):
    """Delete derived content atomically while retained request IDs remain reserved."""
    version = db.get(Version, version_id)
    if version:
        version.validated_indexation_id = None
        version.status = 'pending_contextualization'
        db.flush()
    for job in db.scalars(select(Job).where(Job.version_id == version_id)):
        job.status, job.stage, job.error_code, job.completed_at = 'invalidated','invalidated','RAG_INVALIDATED',now()
        job.cancel_requested, job.run_token, job.lease_until = True, None, None
        job.indexation_id = None
        job.version_id, job.document_id = None, None
        job.progress = {}
    db.flush()
    db.execute(delete(Indexation).where(Indexation.version_id == version_id))


def cleanup_staging(db, retention_days):
    """Bounded cleanup of unsuccessful derived text; never delete a valid index."""
    active = select(Job.indexation_id).where(Job.status.in_(['queued','running']), Job.indexation_id.is_not(None))
    protected = select(Version.validated_indexation_id).where(Version.validated_indexation_id.is_not(None))
    published = select(Doc.published_indexation_id).where(Doc.published_indexation_id.is_not(None)) if db.scalar(text(
        "SELECT to_regclass('leny.inferencia_estado') IS NOT NULL")) else None
    expired = list(db.scalars(select(Indexation.id).where(Indexation.status.in_(['failed','cancelled','invalidated']),
                           Indexation.updated_at < now()-timedelta(days=retention_days),
                           Indexation.id.not_in(active), Indexation.id.not_in(protected)).order_by(Indexation.updated_at).limit(20)))
    if published is not None and expired:
        retained = set(db.scalars(published))
        expired = [identity for identity in expired if identity not in retained]
    if expired:
        db.execute(delete(Indexation).where(Indexation.id.in_(expired)))
    return len(expired)
