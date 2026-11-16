"""Private document-library metadata; no retrieval or model context access."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger, CheckConstraint, Computed, DateTime, ForeignKey, ForeignKeyConstraint,
    Index, Integer, String, Text, UniqueConstraint, Uuid, func, text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class LenyDocumentFolder(TimestampMixin, Base):
    __tablename__ = "carpetas"
    __table_args__ = (
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="ck_leny_folder_not_self"),
        CheckConstraint("length(trim(name)) BETWEEN 1 AND 120", name="ck_leny_folder_name"),
        CheckConstraint("length(name_key) BETWEEN 1 AND 480", name="ck_leny_folder_name_key"),
        Index("uq_leny_folder_root_name", "name_key", unique=True, postgresql_where=text("parent_id IS NULL")),
        Index("uq_leny_folder_sibling_name", "parent_id", "name_key", unique=True, postgresql_where=text("parent_id IS NOT NULL")),
        {"schema": "leny"},
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("leny.carpetas.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    name_key: Mapped[str] = mapped_column(String(480), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)


class LenyFolderReadRole(Base):
    __tablename__ = "carpeta_roles_lectura"
    __table_args__ = {"schema": "leny"}

    folder_id: Mapped[UUID] = mapped_column(ForeignKey("leny.carpetas.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True)


class LenyDocument(TimestampMixin, Base):
    __tablename__ = "documentos"
    # Rolling deployment: do not RETURN server defaults of deferred 0021
    # columns while the currently enabled library still runs on schema0020.
    __mapper_args__ = {'eager_defaults': False}
    # Uploads remain usable before the separately approved 0021 migration.
    __mapper_args__ = {'eager_defaults': False}
    __table_args__ = (
        CheckConstraint("length(trim(title)) BETWEEN 1 AND 200", name="ck_leny_document_title"),
        CheckConstraint("state IN ('active', 'trash', 'purging')", name="ck_leny_document_state"),
        CheckConstraint("revision > 0", name="ck_leny_document_revision"),
        CheckConstraint("(published_version_id IS NULL AND published_indexation_id IS NULL AND published_at IS NULL AND published_by IS NULL) OR "
                        "(published_version_id IS NOT NULL AND published_indexation_id IS NOT NULL AND published_at IS NOT NULL AND published_by IS NOT NULL)",
                        name="ck_leny_document_publication_metadata"),
        CheckConstraint("published_version_id IS NULL OR state = 'active'", name="ck_leny_document_publication_active"),
        CheckConstraint(
            "(state = 'active' AND deleted_at IS NULL AND purge_after IS NULL AND deleted_by IS NULL) OR "
            "(state IN ('trash', 'purging') AND deleted_at IS NOT NULL AND purge_after IS NOT NULL "
            "AND deleted_by IS NOT NULL AND purge_after >= deleted_at)",
            name="ck_leny_document_trash_dates",
        ),
        ForeignKeyConstraint(
            ["id", "published_version_id"], ["leny.documento_versiones.document_id", "leny.documento_versiones.id"],
            name="fk_leny_document_published_owner", use_alter=True, ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["published_version_id", "published_indexation_id", "published_indexation_status"],
            ["leny.rag_indexaciones.version_id", "leny.rag_indexaciones.id", "leny.rag_indexaciones.status"],
            name="fk_leny_document_published_indexation", use_alter=True, ondelete="RESTRICT",
        ),
        Index("ix_leny_document_folder_state_updated", "folder_id", "state", "updated_at", "id"),
        Index("ix_leny_document_state_updated", "state", "updated_at", "id"),
        Index("ix_leny_document_expiry", "purge_after", "id", postgresql_where=text("state IN ('trash', 'purging')")),
        {"schema": "leny"},
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    folder_id: Mapped[UUID] = mapped_column(ForeignKey("leny.carpetas.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"))
    state: Mapped[str] = mapped_column(String(16), default="active", server_default="active", nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    purge_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"))
    published_version_id: Mapped[UUID | None] = mapped_column(Uuid)
    published_indexation_id: Mapped[UUID | None] = mapped_column(Uuid, deferred=True, server_default=text('NULL'))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), deferred=True, server_default=text('NULL'))
    published_by: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), deferred=True, server_default=text('NULL'))
    published_indexation_status: Mapped[str | None] = mapped_column(String(16), Computed(
        "CASE WHEN published_indexation_id IS NOT NULL THEN 'validated'::varchar(16) END", persisted=True), deferred=True)
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)


class LenyDocumentReadRole(Base):
    __tablename__ = "documento_roles_lectura"
    __table_args__ = {"schema": "leny"}

    document_id: Mapped[UUID] = mapped_column(ForeignKey("leny.documentos.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True)


class LenyDocumentVersion(Base):
    __tablename__ = "documento_versiones"
    __table_args__ = (
        UniqueConstraint("document_id", "number", name="uq_leny_document_version_number"),
        UniqueConstraint("document_id", "id", name="uq_leny_document_version_owner"),
        UniqueConstraint("storage_key", name="uq_leny_document_storage_key"),
        UniqueConstraint("preview_key", name="uq_leny_document_preview_key"),
        CheckConstraint("number > 0", name="ck_leny_document_version_number"),
        CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="ck_leny_document_sha256"),
        CheckConstraint("size_bytes > 0 AND size_bytes <= 10485760", name="ck_leny_document_size"),
        CheckConstraint(
            "media_type IN ('application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'image/jpeg', 'image/png')",
            name="ck_leny_document_media_type",
        ),
        CheckConstraint("media_type NOT IN ('image/jpeg', 'image/png') OR size_bytes <= 5242880", name="ck_leny_document_image_size"),
        CheckConstraint("status IN ('pending_contextualization','contextualizing','contextualization_error','pending_publication')", name="ck_leny_document_contextualization_status"),
        CheckConstraint("status <> 'pending_publication' OR validated_indexation_id IS NOT NULL", name="ck_leny_document_validated_pointer"),
        ForeignKeyConstraint(
            ["id", "validated_indexation_id"], ["leny.rag_indexaciones.version_id", "leny.rag_indexaciones.id"],
            name="fk_leny_document_validated_indexation", use_alter=True, ondelete="RESTRICT",
        ),
        CheckConstraint(
            "(preview_key IS NULL AND preview_type IS NULL AND preview_size_bytes = 0) OR "
            "(preview_key IS NOT NULL AND preview_type IS NOT NULL AND preview_size_bytes > 0)",
            name="ck_leny_document_preview_metadata",
        ),
        {"schema": "leny"},
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("leny.documentos.id", ondelete="RESTRICT"), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(180), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    preview_key: Mapped[str | None] = mapped_column(String(180))
    preview_type: Mapped[str | None] = mapped_column(String(100))
    preview_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending_contextualization", server_default="pending_contextualization", nullable=False)
    # Keep legacy library reads compatible while 0020 is being prepared; the
    # contextualization feature loads this only after its migration check.
    validated_indexation_id: Mapped[UUID | None] = mapped_column(Uuid, deferred=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LenyDocumentOperation(TimestampMixin, Base):
    __tablename__ = "documento_operaciones"
    __table_args__ = (
        CheckConstraint("length(trim(kind)) BETWEEN 1 AND 40", name="ck_leny_document_operation_kind"),
        CheckConstraint("fingerprint ~ '^[0-9a-f]{64}$'", name="ck_leny_document_operation_fingerprint"),
        CheckConstraint("status IN ('receiving', 'staged', 'completed', 'failed', 'purging')", name="ck_leny_document_operation_status"),
        CheckConstraint("jsonb_typeof(payload) = 'object'", name="ck_leny_document_operation_payload"),
        Index("ix_leny_document_operation_reconcile", "updated_at", "id", postgresql_where=text("status IN ('receiving', 'staged', 'purging')")),
        Index("ix_leny_document_operation_user_created", "user_id", "created_at"),
        {"schema": "leny"},
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="RESTRICT"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    # Deliberately not FKs: completed/purged request tombstones outlive documents.
    document_id: Mapped[UUID | None] = mapped_column(Uuid)
    version_id: Mapped[UUID | None] = mapped_column(Uuid)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
