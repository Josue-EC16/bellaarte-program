"""Add durable local contextualization, without changing commercial tables.

Revision ID: 20261019_0020
Revises: 20261019_0019

Operational prerequisite: pgvector 0.8.7 already provisioned in schema leny.
This migration never installs native binaries or creates/drops the extension.
Downgrade removes derived contextualization only; originals remain intact.
"""
from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.compiler import compiles

revision = "20261019_0020"
down_revision = "20261019_0019"
branch_labels = None
depends_on = None


class _LenyVector(Vector):
    cache_ok = True


@compiles(_LenyVector, "postgresql")
def _vector_type(type_, compiler, **kwargs):
    return "leny.vector(1024)"


def _timestamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade():
    op.execute("""
        DO $leny_vector_precondition$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace
            WHERE e.extname='vector' AND e.extversion='0.8.7' AND n.nspname='leny'
          ) THEN
            RAISE EXCEPTION 'LENY requires reviewed pgvector 0.8.7 in schema leny';
          END IF;
        END $leny_vector_precondition$;
    """)
    op.create_table(
        "rag_indexaciones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("model_digest", sa.String(64), nullable=False),
        sa.Column("dimension", sa.Integer(), server_default="1024", nullable=False),
        sa.Column("pipeline_version", sa.String(64), nullable=False),
        sa.Column("chunking_version", sa.String(64), nullable=False),
        sa.Column("ocr_version", sa.String(64), nullable=False),
        sa.Column("config", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("coverage", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("status", sa.String(16), server_default="staging", nullable=False),
        sa.Column("chunk_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["version_id"], ["leny.documento_versiones.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("version_id", "id", name="uq_leny_rag_indexation_owner"),
        sa.CheckConstraint("model_digest ~ '^[0-9a-f]{64}$'", name="ck_leny_rag_indexation_digest"),
        sa.CheckConstraint("dimension = 1024", name="ck_leny_rag_indexation_dimension"),
        sa.CheckConstraint("status IN ('staging','validated','failed','cancelled','invalidated')", name="ck_leny_rag_indexation_status"),
        sa.CheckConstraint("chunk_count >= 0", name="ck_leny_rag_indexation_count"),
        sa.CheckConstraint("jsonb_typeof(config) = 'object' AND jsonb_typeof(coverage) = 'object'", name="ck_leny_rag_indexation_json"),
        sa.CheckConstraint("status <> 'validated' OR (validated_at IS NOT NULL AND chunk_count > 0)", name="ck_leny_rag_indexation_validated"),
        schema="leny",
    )
    op.create_index("ix_leny_rag_indexation_version_created", "rag_indexaciones", ["version_id", "created_at", "id"], schema="leny")
    op.create_table(
        "rag_trabajos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Uuid()),
        sa.Column("version_id", sa.Uuid()),
        sa.Column("source_document_id", sa.Uuid(), nullable=False),
        sa.Column("source_version_id", sa.Uuid(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("action", sa.String(24), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("pipeline_fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), server_default="queued", nullable=False),
        sa.Column("stage", sa.String(40), server_default="queued", nullable=False),
        sa.Column("progress", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cancel_requested", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("worker_id", sa.Uuid()),
        sa.Column("run_token", sa.Uuid()),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column("indexation_id", sa.Uuid()),
        sa.Column("retry_of_id", sa.Uuid()),
        sa.Column("error_code", sa.String(64)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["account_id"], ["cuentas.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["document_id"], ["leny.documentos.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["version_id"], ["leny.documento_versiones.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["indexation_id"], ["leny.rag_indexaciones.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["retry_of_id"], ["leny.rag_trabajos.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="ck_leny_rag_job_hash"),
        sa.CheckConstraint("fingerprint ~ '^[0-9a-f]{64}$' AND pipeline_fingerprint ~ '^[0-9a-f]{64}$'", name="ck_leny_rag_job_fingerprints"),
        sa.CheckConstraint("action IN ('contextualize','recontextualize','retry')", name="ck_leny_rag_job_action"),
        sa.CheckConstraint("status IN ('queued','running','completed','failed','cancelled','invalidated')", name="ck_leny_rag_job_status"),
        sa.CheckConstraint("attempts >= 0", name="ck_leny_rag_job_attempts"),
        sa.CheckConstraint("jsonb_typeof(progress) = 'object'", name="ck_leny_rag_job_progress"),
        sa.CheckConstraint("status <> 'running' OR (worker_id IS NOT NULL AND run_token IS NOT NULL AND lease_until IS NOT NULL)", name="ck_leny_rag_job_lease"),
        schema="leny",
    )
    op.create_index("uq_leny_rag_job_active", "rag_trabajos", ["source_version_id", "pipeline_fingerprint"], unique=True, schema="leny", postgresql_where=sa.text("status IN ('queued','running')"))
    op.create_index("ix_leny_rag_job_queue", "rag_trabajos", ["created_at", "id"], schema="leny", postgresql_where=sa.text("status = 'queued'"))
    op.create_index("ix_leny_rag_job_lease", "rag_trabajos", ["lease_until", "id"], schema="leny", postgresql_where=sa.text("status = 'running'"))
    op.create_index("ix_leny_rag_job_account_created", "rag_trabajos", ["account_id", "created_at", "id"], schema="leny")
    op.create_index("ix_leny_rag_job_version_created", "rag_trabajos", ["version_id", "created_at", "id"], schema="leny")
    op.create_table(
        "rag_fragmentos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("indexation_id", sa.Uuid(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("source_type", sa.String(24), nullable=False),
        sa.Column("locator", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("byte_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["indexation_id"], ["leny.rag_indexaciones.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("indexation_id", "ordinal", name="uq_leny_rag_fragment_ordinal"),
        sa.UniqueConstraint("id", "indexation_id", name="uq_leny_rag_fragment_owner"),
        sa.CheckConstraint("ordinal >= 0", name="ck_leny_rag_fragment_ordinal"),
        sa.CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="ck_leny_rag_fragment_hash"),
        sa.CheckConstraint("source_type IN ('PDF_TEXT','PDF_OCR','DOCX_PARAGRAPH','DOCX_TABLE','IMAGE_OCR')", name="ck_leny_rag_fragment_source"),
        sa.CheckConstraint("jsonb_typeof(locator) = 'object'", name="ck_leny_rag_fragment_locator"),
        sa.CheckConstraint("char_count > 0 AND char_count = length(text) AND byte_count = octet_length(text)", name="ck_leny_rag_fragment_lengths"),
        schema="leny",
    )
    op.create_table(
        "rag_embeddings",
        sa.Column("fragment_id", sa.Uuid(), nullable=False),
        sa.Column("indexation_id", sa.Uuid(), nullable=False),
        sa.Column("embedding", _LenyVector(1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("fragment_id"),
        sa.ForeignKeyConstraint(["fragment_id", "indexation_id"], ["leny.rag_fragmentos.id", "leny.rag_fragmentos.indexation_id"], name="fk_leny_rag_embedding_fragment_owner", ondelete="CASCADE"),
        schema="leny",
    )
    op.create_index("ix_leny_rag_embedding_indexation", "rag_embeddings", ["indexation_id"], schema="leny")
    op.create_table(
        "rag_workers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_instance", sa.String(100), nullable=False),
        sa.Column("pid", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("stopped_at", sa.DateTime(timezone=True)),
        sa.Column("current_job_id", sa.Uuid()),
        sa.Column("provider_inflight", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("provider_digest", sa.String(64)),
        sa.Column("unsafe_reason", sa.String(64)),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("pid > 0", name="ck_leny_rag_worker_pid"),
        sa.CheckConstraint("length(trim(host_instance)) BETWEEN 1 AND 100", name="ck_leny_rag_worker_host"),
        sa.CheckConstraint("provider_digest IS NULL OR provider_digest ~ '^[0-9a-f]{64}$'", name="ck_leny_rag_worker_digest"),
        schema="leny",
    )
    op.create_index("ix_leny_rag_worker_active", "rag_workers", ["heartbeat_at"], schema="leny", postgresql_where=sa.text("stopped_at IS NULL"))
    op.add_column("documento_versiones", sa.Column("validated_indexation_id", sa.Uuid()), schema="leny")
    op.drop_constraint("ck_leny_document_pending_stage01", "documento_versiones", type_="check", schema="leny")
    op.create_check_constraint("ck_leny_document_contextualization_status", "documento_versiones", "status IN ('pending_contextualization','contextualizing','contextualization_error','pending_publication')", schema="leny")
    op.create_check_constraint("ck_leny_document_validated_pointer", "documento_versiones", "status <> 'pending_publication' OR validated_indexation_id IS NOT NULL", schema="leny")
    op.create_foreign_key("fk_leny_document_validated_indexation", "documento_versiones", "rag_indexaciones", ["id", "validated_indexation_id"], ["version_id", "id"], source_schema="leny", referent_schema="leny", ondelete="RESTRICT")


def downgrade():
    # This intentionally discards only derived RAG data. Never use a business
    # downgrade as a rehearsal; disable the feature to retain its audit history.
    op.drop_constraint("fk_leny_document_validated_indexation", "documento_versiones", type_="foreignkey", schema="leny")
    op.drop_constraint("ck_leny_document_validated_pointer", "documento_versiones", type_="check", schema="leny")
    op.drop_constraint("ck_leny_document_contextualization_status", "documento_versiones", type_="check", schema="leny")
    op.execute("UPDATE leny.documento_versiones SET status='pending_contextualization'")
    op.drop_column("documento_versiones", "validated_indexation_id", schema="leny")
    op.create_check_constraint("ck_leny_document_pending_stage01", "documento_versiones", "status = 'pending_contextualization'", schema="leny")
    op.drop_table("rag_workers", schema="leny")
    op.drop_table("rag_trabajos", schema="leny")
    op.drop_table("rag_embeddings", schema="leny")
    op.drop_table("rag_fragmentos", schema="leny")
    op.drop_table("rag_indexaciones", schema="leny")
