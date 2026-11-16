"""Explicit ADMIN approval of a fixed version/index pair; no Ollama calls."""
from contextlib import nullcontext
import hashlib
import math
from uuid import UUID

from sqlalchemy import func, select, text

from app.models.leny_documents import LenyDocument as Doc, LenyDocumentOperation as Operation, LenyDocumentVersion as Version
from app.models.leny_rag import LenyRagIndexation as Indexation, LenyRagFragment as Fragment, LenyRagEmbedding as Embedding, LenyRagJob as Job
from app.services.leny_document_service import CURRENT_LEASE, fingerprint, now
from app.services.leny_document_storage import DocumentError
from app.services.leny_rag_common import PIPELINE_VERSION, CHUNKING_VERSION, OCR_VERSION, QUERY_POLICY
from app.services.leny_rag_service import RagService


def publication_schema_ready(db):
    """Read-only, compatible with the still-running 0020 application."""
    return bool(db.scalar(text("SELECT to_regclass('leny.inferencia_estado') IS NOT NULL")))


def indexation_compatible(index, settings):
    config = index.config or {}
    return bool(index.status == 'validated' and index.chunk_count > 0 and index.validated_at
        and index.model == settings.leny_rag_model and index.model_digest == settings.leny_rag_model_digest
        and index.dimension == 1024 and index.pipeline_version == PIPELINE_VERSION
        and index.chunking_version == CHUNKING_VERSION and index.ocr_version == OCR_VERSION
        and config.get('model') == settings.leny_rag_model and config.get('model_digest') == settings.leny_rag_model_digest
        and config.get('dimension') == 1024 and config.get('document_policy') == 'raw-structured-text-v1'
        and config.get('query_policy') == QUERY_POLICY and config.get('cpu_only') is True)


def validate_indexation(db, version, indexation_id, settings, *, integrity=True):
    index = db.get(Indexation, indexation_id)
    if not index or index.version_id != version.id or not indexation_compatible(index, settings):
        raise DocumentError('DOCUMENT_INDEX_INCOMPATIBLE', 'La indexación no está validada o no es compatible.', 409)
    if integrity:
        fragments = list(db.scalars(select(Fragment).where(Fragment.indexation_id == index.id)))
        vectors = dict(db.execute(select(Embedding.fragment_id, Embedding.embedding).where(Embedding.indexation_id == index.id)).all())
        if not 0 < len(fragments) == len(vectors) == index.chunk_count <= settings.leny_rag_max_chunks:
            raise DocumentError('DOCUMENT_INDEX_INCOMPLETE', 'La indexación no tiene todos sus fragmentos y vectores.', 409)
        for fragment in fragments:
            vector = vectors.get(fragment.id)
            if (hashlib.sha256(fragment.text.encode('utf-8')).hexdigest() != fragment.sha256
                    or vector is None or len(vector) != 1024
                    or not all(math.isfinite(float(value)) for value in vector)
                    or not any(float(value) != 0 for value in vector)):
                raise DocumentError('DOCUMENT_INDEX_INTEGRITY', 'No se pudo comprobar la integridad de la indexación.', 409)
    return index


class PublicationService:
    def __init__(self, settings, session_factory):
        self.settings = settings
        self.rag = RagService(settings, session_factory)
        self.documents = self.rag.documents

    def readiness(self):
        """No inference, native parser checks, filesystem initialization or writes."""
        with self.documents.reading() as db:
            schema = publication_schema_ready(db)
        configured = bool(self.settings.leny_documents_enabled and self.settings.leny_rag_enabled
                          and self.settings.leny_rag_model == 'qwen3-embedding:0.6b'
                          and self.settings.leny_rag_model_digest and len(self.settings.leny_rag_model_digest) == 64)
        return dict(publication_ready=schema and configured, schema_ready=schema,
                    configuration_compatible=configured)

    def _require(self, db, actor):
        self.rag.require_enabled()
        self.rag.actor(db, actor)
        if not publication_schema_ready(db):
            raise DocumentError('DOCUMENT_PUBLICATION_UNAVAILABLE', 'La publicación documental requiere una actualización del almacenamiento.', 503)

    @staticmethod
    def clear(doc):
        doc.published_version_id = doc.published_indexation_id = None
        doc.published_at = doc.published_by = None

    def _previous(self, db, actor, identity, data, kind):
        intent = fingerprint(dict(kind=kind, document_id=str(identity), **data.model_dump(mode='json')))
        previous = db.get(Operation, data.request_id)
        if previous:
            if (previous.account_id != actor.account_id or previous.user_id != actor.user_id
                    or previous.kind != kind or previous.fingerprint != intent or previous.status != 'completed'):
                raise DocumentError('DOCUMENT_REQUEST_REUSED', 'El identificador ya fue utilizado para otra operación.', 409)
            return intent, dict(previous.payload['result'])
        return intent, None

    def _finish(self, db, actor, doc, data, kind, intent):
        doc.revision += 1
        doc.updated_by = actor.user_id
        result = dict(request_id=str(data.request_id), document_id=str(doc.id),
                      published_version_id=str(doc.published_version_id) if doc.published_version_id else None,
                      published_indexation_id=str(doc.published_indexation_id) if doc.published_indexation_id else None,
                      revision=doc.revision)
        db.add(Operation(id=data.request_id, account_id=actor.account_id, user_id=actor.user_id,
                         kind=kind, fingerprint=intent, status='completed', document_id=doc.id,
                         version_id=doc.published_version_id, payload={'result': result}))
        self.documents.audit(db, actor, 'LENY_DOCUMENT_PUBLISHED' if kind == 'publish' else 'LENY_DOCUMENT_UNPUBLISHED', doc.id)
        return result

    def publish(self, actor, doc_id, data):
        with (nullcontext() if CURRENT_LEASE.get() else self.documents.lock()):
            with self.documents.transaction() as db:
                self._require(db, actor)
                intent, previous = self._previous(db, actor, doc_id, data, 'publish')
                if previous is not None:
                    return previous
                doc = self.documents._doc(db, doc_id, data.expected_revision)
                if doc.state != 'active':
                    raise DocumentError('DOCUMENT_IN_TRASH', 'Restaura el documento antes de publicarlo.', 409)
                version = db.get(Version, data.version_id)
                if not version or version.document_id != doc.id:
                    raise DocumentError('DOCUMENT_NOT_FOUND', 'Versión no encontrada.', 404)
                if version.validated_indexation_id != data.indexation_id:
                    raise DocumentError('DOCUMENT_INDEX_CHANGED', 'La indexación cambió. Actualiza y vuelve a revisarla.', 409)
                if db.scalar(select(Job.id).where(Job.version_id == version.id, Job.status.in_(['queued', 'running'])).limit(1)):
                    raise DocumentError('DOCUMENT_CONTEXTUALIZATION_ACTIVE', 'Espera a que termine la contextualización.', 409)
                validate_indexation(db, version, data.indexation_id, self.settings)
                digest, size = hashlib.sha256(), 0
                with self.documents.storage.open(version.storage_key) as original:
                    for block in iter(lambda: original.read(65536), b''):
                        size += len(block)
                        if size > version.size_bytes:
                            raise DocumentError('DOCUMENT_ORIGINAL_INTEGRITY', 'No se pudo comprobar el archivo original.', 409)
                        digest.update(block)
                if size != version.size_bytes or digest.hexdigest() != version.sha256:
                    raise DocumentError('DOCUMENT_ORIGINAL_INTEGRITY', 'No se pudo comprobar el archivo original.', 409)
                doc.published_version_id, doc.published_indexation_id = version.id, data.indexation_id
                doc.published_at, doc.published_by = now(), actor.user_id
                return self._finish(db, actor, doc, data, 'publish', intent)

    def unpublish(self, actor, doc_id, data):
        with (nullcontext() if CURRENT_LEASE.get() else self.documents.lock()):
            with self.documents.transaction() as db:
                self._require(db, actor)
                intent, previous = self._previous(db, actor, doc_id, data, 'unpublish')
                if previous is not None:
                    return previous
                doc = self.documents._doc(db, doc_id, data.expected_revision)
                self.clear(doc)
                return self._finish(db, actor, doc, data, 'unpublish', intent)
