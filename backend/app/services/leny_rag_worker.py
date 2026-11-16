"""One manually launched Windows worker, durable jobs and bounded CPU inference."""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from pathlib import Path
import shutil
import threading
import time
from uuid import uuid4

from sqlalchemy import text

from app.services.leny_coordination import PostgresCoordinator
from app.services.leny_ollama import LenyError
from app.services.leny_document_service import LibraryLease
from app.services.leny_document_storage import DocumentError, _check_path, protect_directory
from app.services.leny_rag_common import RagError, available_ram
from app.services.leny_rag_embeddings import EmbeddingProvider
from app.services.leny_rag_service import RagService

WORKER_LOCK = 0x4C454E590201


class RagWorker:
    def __init__(self, settings, session_factory, provider_factory=None):
        self.settings = settings
        self.service = RagService(settings, session_factory)
        self.coordinator = PostgresCoordinator(settings.effective_database_url)
        self.provider_factory = provider_factory or (lambda: EmbeddingProvider(settings))
        self.id = uuid4()
        self.stop = threading.Event()
        self.claim = None
        self.claim_started = None
        self.lease = None
        self.thread = None
        self.heartbeat_error = None
        self.mutex = threading.Lock()
        self.metadata_lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
        self.stop_file = None
        self.shutdown_file = None

    def write(self, function, *args, **kwargs):
        """Heartbeat and main thread never contend for their own library lease.

        An upload/backup in another process can own the shared gate briefly;
        retry that admission failure without failing a valid processing job.
        """
        deadline = time.monotonic()+30
        while True:
            try:
                with self.metadata_lock:
                    return function(*args, **kwargs)
            except DocumentError as error:
                if error.code not in {'DOCUMENT_BUSY','BACKUP_IN_PROGRESS'} or time.monotonic() >= deadline:
                    raise
                time.sleep(0.1)

    def acquire(self):
        connection = self.service.documents.engine.connect().execution_options(isolation_level='AUTOCOMMIT')
        try:
            if not connection.scalar(text('SELECT pg_try_advisory_lock(:key)'), {'key':WORKER_LOCK}):
                raise RagError('RAG_ALREADY_ACTIVE', 409)
            self.lease = LibraryLease(connection)
        except BaseException:
            connection.invalidate()
            connection.close()
            raise

    def check(self):
        if getattr(self,'shutdown_file',None) and self.shutdown_file.exists():
            self.stop.set()
            raise RagError('RAG_WORKER_SHUTDOWN',409)
        if self.stop_file and self.stop_file.exists():
            self.stop.set()
        if self.stop.is_set():
            raise RagError('RAG_CANCELLED', 409)
        if self.heartbeat_error:
            raise RagError('RAG_LOCK_LOST')
        with self.mutex:
            self.lease.check()
        if self.claim:
            if time.monotonic()-self.claim_started > self.settings.leny_rag_job_seconds:
                raise RagError('RAG_JOB_TIMEOUT')
            self.service.check(self.claim['id'], self.claim['token'])

    def heartbeat_loop(self):
        while not self.stop.wait(self.settings.leny_rag_heartbeat_seconds):
            claim = self.claim
            try:
                with self.mutex:
                    self.lease.check()
                self.write(self.service.heartbeat, self.id, claim['id'] if claim else None, claim['token'] if claim else None)
            except DocumentError as error:
                # Backup and a short library mutation can temporarily own the gate.
                if error.code in {'DOCUMENT_BUSY','BACKUP_IN_PROGRESS','RAG_CANCELLED','RAG_INVALIDATED','RAG_NOT_FOUND'}:
                    continue
                self.heartbeat_error = error.code
            except Exception:
                self.heartbeat_error = 'RAG_LOCK_LOST'

    def working_root(self):
        root = self.service.documents.storage.root / 'processing'
        _check_path(root)
        root.mkdir(exist_ok=True)
        protect_directory(root)
        return root

    def run(self, *, once=False, stop_file=None, shutdown_file=None):
        self.stop_file = Path(stop_file) if stop_file else None
        self.shutdown_file = Path(shutdown_file) if shutdown_file else None
        self.service.require_enabled()
        self.acquire()
        try:
            self.write(self.service.register, self.id, hashlib.sha256(str(self.service.documents.storage.root).encode()).hexdigest()[:32], os.getpid())
            root = self.working_root()
            # Exclusive worker ownership and closed previous Job Objects allow
            # removing only our own temporary UUID directories after a restart.
            for item in root.iterdir():
                if item.is_dir() and len(item.name) == 32 and all(c in '0123456789abcdef' for c in item.name):
                    _check_path(item)
                    shutil.rmtree(item)
            self.thread = threading.Thread(target=self.heartbeat_loop, daemon=True)
            self.thread.start()
            while not self.stop.is_set():
                if stop_file and Path(stop_file).exists():
                    break
                try:
                    self.check()
                except RagError as error:
                    if error.code in {'RAG_WORKER_SHUTDOWN','RAG_CANCELLED'}:
                        break
                    raise
                try:
                    self.claim = self.write(self.service.claim, self.id)
                    if self.claim:
                        self.claim_started = time.monotonic()
                        self.process(self.claim, root)
                    elif not once:
                        self.stop.wait(self.settings.leny_rag_poll_seconds)
                except DocumentError as error:
                    if error.code not in {'DOCUMENT_BUSY','BACKUP_IN_PROGRESS'}:
                        raise
                    self.stop.wait(1)
                finally:
                    self.claim = None
                if once:
                    break
        finally:
            self.stop.set()
            if self.thread:
                # No lease is closed underneath a heartbeat still finishing a
                # metadata transaction. The owning backend has a bounded outer
                # shutdown and contains the whole worker tree in a Windows Job.
                self.thread.join()
            try:
                self.write(self.service.stopped, self.id)
            except Exception:
                self.logger.warning('LENY_RAG_WORKER_STOP_DEFERRED')
            finally:
                if self.lease:
                    self.lease.close()
                self.service.documents.engine.dispose()
                self.coordinator.engine.dispose()

    def progress(self, stage, values):
        self.check()
        self.write(self.service.progress, self.claim['id'], self.claim['token'], stage, values)

    def process(self, claim, root):
        from app.services.leny_rag_extraction import extract_document
        from app.services.leny_rag_chunking import fragment_units
        directory = root / uuid4().hex
        directory.mkdir()
        _check_path(directory)
        provider = self.provider_factory()
        ai_lease = None
        inflight = False
        uncertain = False
        try:
            if available_ram() < self.settings.leny_rag_min_ram_bytes or shutil.disk_usage(root).free < self.settings.leny_rag_min_free_bytes:
                raise RagError('RAG_MEMORY')
            extension = {'application/pdf':'.pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document':'.docx',
                         'image/jpeg':'.jpg','image/png':'.png'}[claim['media_type']]
            copy = directory / ('input' + extension)
            with self.service.documents.lock():
                self.check()
                digest, size = hashlib.sha256(), 0
                with self.service.documents.storage.open(claim['storage_key']) as source, copy.open('xb') as destination:
                    while block := source.read(1024**2):
                        size += len(block)
                        if size > self.settings.leny_documents_max_file_bytes:
                            raise RagError('RAG_INTEGRITY')
                        digest.update(block)
                        destination.write(block)
                if size != claim['size_bytes'] or digest.hexdigest() != claim['sha256']:
                    raise RagError('RAG_INTEGRITY')

            def extracted(event):
                if event['stage'] == 'ocr':
                    self.progress('ocr', {'ocr_pages_done':event['current'],'ocr_pages_total':event['total']})
                else:
                    self.progress('extracting', {'pages_done':event['current'],'pages_total':event['total']})
            extracted_result = extract_document(copy, directory, self.settings, self.check, extracted)
            self.progress('chunking', {})
            fragments = fragment_units(extracted_result['units'], self.settings)
            self.write(self.service.fragments, claim, fragments, extracted_result['coverage'])
            self.progress('waiting_resources', {'chunks_total':len(fragments), 'warnings':extracted_result['coverage'].get('warnings', [])})
            while ai_lease is None:
                self.check()
                try:
                    ai_lease = self.coordinator.acquire()
                except LenyError as error:
                    if error.code != 'LENY_BUSY':
                        raise RagError('RAG_INFERENCE_UNCERTAIN' if error.code == 'LENY_INFERENCE_UNCERTAIN' else 'RAG_LOCK_LOST')
                    self.stop.wait(1)
            self.progress('loading_model', {})
            rows = self.service.pending_fragments(claim['indexation_id'])
            # Includes a real synthetic dimensionality/CPU probe even when all
            # persistent vector batches were checkpointed before a restart.
            batches = [[(None, 'Verificación técnica local de BELLAARTE BOUTIQUE.')]]
            batches += [rows[i:i+self.settings.leny_rag_batch_size] for i in range(0,len(rows),self.settings.leny_rag_batch_size)]
            for batch in batches:
                self.check()
                ai_lease.check()
                memory_floor = (self.settings.leny_rag_min_resident_ram_bytes if provider.owned_model
                                else self.settings.leny_rag_min_ram_bytes)
                available_bytes=available_ram()
                if available_bytes < memory_floor:
                    self.logger.warning('LENY_RAG_RESOURCE_REJECTED available_bytes=%s floor_bytes=%s',available_bytes,memory_floor)
                    raise RagError('RAG_MEMORY')
                for attempt in range(3):
                    self.write(self.service.heartbeat, self.id, claim['id'], claim['token'], provider_inflight=True)
                    inflight = True
                    try:
                        vectors = asyncio.run(provider.embed([item[1] for item in batch]))
                    except RagError as error:
                        if error.uncertain:
                            uncertain = True
                            raise
                        self.write(self.service.heartbeat, self.id, claim['id'], claim['token'], provider_inflight=False)
                        inflight = False
                        if error.code not in {'RAG_PROVIDER_UNAVAILABLE','RAG_PROVIDER_TIMEOUT'} or attempt == 2:
                            raise
                        self.stop.wait(2 if attempt == 0 else 5)
                        continue
                    self.write(self.service.heartbeat, self.id, claim['id'], claim['token'], provider_inflight=False)
                    inflight = False
                    break
                self.check()
                ai_lease.check()
                if batch[0][0] is not None:
                    self.write(self.service.save_vectors, claim, batch, vectors)
            asyncio.run(provider.verify(allow_owned=True))
            self.progress('verifying', {'seconds':round(time.monotonic()-self.claim_started, 3)})
            self.write(self.service.finish, claim)
        except BaseException as error:
            uncertain = uncertain or getattr(error, 'uncertain', False) or inflight
            code = error.code if isinstance(error, DocumentError) else 'RAG_CANCELLED' if isinstance(error, KeyboardInterrupt) else 'RAG_OPERATION_FAILED'
            try:
                if uncertain:
                    self.write(self.service.heartbeat, self.id, provider_inflight=True, unsafe_reason='RAG_INFERENCE_UNCERTAIN')
                if not uncertain and code in {'RAG_MODEL_MISSING','RAG_PROVIDER_UNAVAILABLE','RAG_EXTERNAL_MODEL','RAG_WORKER_SHUTDOWN'}:
                    self.write(self.service.defer, claim, code)
                    if code!='RAG_WORKER_SHUTDOWN':
                        self.stop.wait(10)
                else:
                    self.write(self.service.fail, claim, code)
            except Exception:
                self.logger.warning('LENY_RAG_FAILURE_RECONCILIATION_REQUIRED')
                self.stop.set()
            self.logger.warning('LENY_RAG_JOB_TERMINATED reason=%s', code)
            if uncertain:
                self.stop.set()
        finally:
            if ai_lease:
                try:
                    if not uncertain:
                        asyncio.run(provider.release())
                except Exception:
                    self.logger.warning('LENY_RAG_MODEL_RELEASE_DEFERRED')
                finally:
                    ai_lease.close()
            _check_path(directory)
            shutil.rmtree(directory)
