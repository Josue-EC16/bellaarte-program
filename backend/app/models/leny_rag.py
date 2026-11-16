"""Durable local contextualization metadata; no retrieval or chat integration."""
from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint,
    Index, Integer, String, Text, UniqueConstraint, Uuid, func, text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class LenyVector(Vector):
    """Use the provisioned extension schema even with search_path=public."""
    cache_ok = True


@compiles(LenyVector, "postgresql")
def _compile_leny_vector(type_, compiler, **kwargs):
    return "leny.vector" if type_.dim is None else f"leny.vector({int(type_.dim)})"


class LenyRagIndexation(TimestampMixin, Base):
    __tablename__ = "rag_indexaciones"
    __table_args__ = (
        UniqueConstraint("version_id", "id", name="uq_leny_rag_indexation_owner"),
        UniqueConstraint("version_id", "id", "status", name="uq_leny_rag_indexation_publication_state"),
        CheckConstraint("model_digest ~ '^[0-9a-f]{64}$'", name="ck_leny_rag_indexation_digest"),
        CheckConstraint("dimension = 1024", name="ck_leny_rag_indexation_dimension"),
        CheckConstraint("status IN ('staging','validated','failed','cancelled','invalidated')", name="ck_leny_rag_indexation_status"),
        CheckConstraint("chunk_count >= 0", name="ck_leny_rag_indexation_count"),
        CheckConstraint("jsonb_typeof(config) = 'object' AND jsonb_typeof(coverage) = 'object'", name="ck_leny_rag_indexation_json"),
        CheckConstraint("status <> 'validated' OR (validated_at IS NOT NULL AND chunk_count > 0)", name="ck_leny_rag_indexation_validated"),
        Index("ix_leny_rag_indexation_version_created", "version_id", "created_at", "id"),
        {"schema": "leny"},
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    version_id: Mapped[UUID] = mapped_column(ForeignKey("leny.documento_versiones.id", ondelete="RESTRICT"), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    model_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, default=1024, server_default="1024", nullable=False)
    pipeline_version: Mapped[str] = mapped_column(String(64), nullable=False)
    chunking_version: Mapped[str] = mapped_column(String(64), nullable=False)
    ocr_version: Mapped[str] = mapped_column(String(64), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False)
    coverage: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="staging", server_default="staging", nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LenyRagJob(TimestampMixin, Base):
    __tablename__ = "rag_trabajos"
    __table_args__ = (
        CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="ck_leny_rag_job_hash"),
        CheckConstraint("fingerprint ~ '^[0-9a-f]{64}$' AND pipeline_fingerprint ~ '^[0-9a-f]{64}$'", name="ck_leny_rag_job_fingerprints"),
        CheckConstraint("action IN ('contextualize','recontextualize','retry')", name="ck_leny_rag_job_action"),
        CheckConstraint("status IN ('queued','running','completed','failed','cancelled','invalidated')", name="ck_leny_rag_job_status"),
        CheckConstraint("attempts >= 0", name="ck_leny_rag_job_attempts"),
        CheckConstraint("jsonb_typeof(progress) = 'object'", name="ck_leny_rag_job_progress"),
        CheckConstraint("status <> 'running' OR (worker_id IS NOT NULL AND run_token IS NOT NULL AND lease_until IS NOT NULL)", name="ck_leny_rag_job_lease"),
        Index("uq_leny_rag_job_active", "source_version_id", "pipeline_fingerprint", unique=True,
              postgresql_where=text("status IN ('queued','running')")),
        Index("ix_leny_rag_job_queue", "created_at", "id", postgresql_where=text("status = 'queued'")),
        Index("ix_leny_rag_job_lease", "lease_until", "id", postgresql_where=text("status = 'running'")),
        Index("ix_leny_rag_job_account_created", "account_id", "created_at", "id"),
        Index("ix_leny_rag_job_version_created", "version_id", "created_at", "id"),
        {"schema": "leny"},
    )

    # The request UUID remains reserved even after purge or a failed execution.
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="RESTRICT"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    document_id: Mapped[UUID | None] = mapped_column(ForeignKey("leny.documentos.id", ondelete="SET NULL"))
    version_id: Mapped[UUID | None] = mapped_column(ForeignKey("leny.documento_versiones.id", ondelete="SET NULL"))
    source_document_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    source_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(24), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    pipeline_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="queued", server_default="queued", nullable=False)
    stage: Mapped[str] = mapped_column(String(40), default="queued", server_default="queued", nullable=False)
    progress: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    worker_id: Mapped[UUID | None] = mapped_column(Uuid)
    run_token: Mapped[UUID | None] = mapped_column(Uuid)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    indexation_id: Mapped[UUID | None] = mapped_column(ForeignKey("leny.rag_indexaciones.id", ondelete="SET NULL"))
    retry_of_id: Mapped[UUID | None] = mapped_column(ForeignKey("leny.rag_trabajos.id", ondelete="RESTRICT"))
    error_code: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LenyRagFragment(Base):
    __tablename__ = "rag_fragmentos"
    __table_args__ = (
        UniqueConstraint("indexation_id", "ordinal", name="uq_leny_rag_fragment_ordinal"),
        UniqueConstraint("id", "indexation_id", name="uq_leny_rag_fragment_owner"),
        CheckConstraint("ordinal >= 0", name="ck_leny_rag_fragment_ordinal"),
        CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="ck_leny_rag_fragment_hash"),
        CheckConstraint("source_type IN ('PDF_TEXT','PDF_OCR','DOCX_PARAGRAPH','DOCX_TABLE','IMAGE_OCR')", name="ck_leny_rag_fragment_source"),
        CheckConstraint("jsonb_typeof(locator) = 'object'", name="ck_leny_rag_fragment_locator"),
        CheckConstraint("char_count > 0 AND char_count = length(text) AND byte_count = octet_length(text)", name="ck_leny_rag_fragment_lengths"),
        {"schema": "leny"},
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    indexation_id: Mapped[UUID] = mapped_column(ForeignKey("leny.rag_indexaciones.id", ondelete="CASCADE"), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[str] = mapped_column(String(24), nullable=False)
    locator: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    byte_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LenyRagEmbedding(Base):
    __tablename__ = "rag_embeddings"
    __table_args__ = (
        ForeignKeyConstraint(["fragment_id", "indexation_id"], ["leny.rag_fragmentos.id", "leny.rag_fragmentos.indexation_id"],
                             name="fk_leny_rag_embedding_fragment_owner", ondelete="CASCADE"),
        Index("ix_leny_rag_embedding_indexation", "indexation_id"),
        {"schema": "leny"},
    )

    fragment_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    indexation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(LenyVector(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LenyRagWorker(Base):
    __tablename__ = "rag_workers"
    __table_args__ = (
        CheckConstraint("pid > 0", name="ck_leny_rag_worker_pid"),
        CheckConstraint("length(trim(host_instance)) BETWEEN 1 AND 100", name="ck_leny_rag_worker_host"),
        CheckConstraint("provider_digest IS NULL OR provider_digest ~ '^[0-9a-f]{64}$'", name="ck_leny_rag_worker_digest"),
        Index("ix_leny_rag_worker_active", "heartbeat_at", postgresql_where=text("stopped_at IS NULL")),
        {"schema": "leny"},
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    host_instance: Mapped[str] = mapped_column(String(100), nullable=False)
    pid: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_job_id: Mapped[UUID | None] = mapped_column(Uuid)
    provider_inflight: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    provider_digest: Mapped[str | None] = mapped_column(String(64))
    unsafe_reason: Mapped[str | None] = mapped_column(String(64))
