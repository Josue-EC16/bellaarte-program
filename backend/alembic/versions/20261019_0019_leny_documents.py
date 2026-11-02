"""Add the private LENY document library, without changing existing tables.

Revision ID: 20261019_0019
Revises: 20261019_0018
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261019_0019"
down_revision = "20261019_0018"
branch_labels = None
depends_on = None


def _timestamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade():
    # The schema belongs to 0017; fail rather than silently creating another one.
    op.create_table(
        "carpetas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid()),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("name_key", sa.String(480), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_by", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["parent_id"], ["leny.carpetas.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("parent_id IS NULL OR parent_id <> id", name="ck_leny_folder_not_self"),
        sa.CheckConstraint("length(trim(name)) BETWEEN 1 AND 120", name="ck_leny_folder_name"),
        sa.CheckConstraint("length(name_key) BETWEEN 1 AND 480", name="ck_leny_folder_name_key"),
        schema="leny",
    )
    op.create_index("uq_leny_folder_root_name", "carpetas", ["name_key"], unique=True, schema="leny", postgresql_where=sa.text("parent_id IS NULL"))
    op.create_index("uq_leny_folder_sibling_name", "carpetas", ["parent_id", "name_key"], unique=True, schema="leny", postgresql_where=sa.text("parent_id IS NOT NULL"))
    op.create_table(
        "carpeta_roles_lectura",
        sa.Column("folder_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("folder_id", "role_id"),
        sa.ForeignKeyConstraint(["folder_id"], ["leny.carpetas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="RESTRICT"),
        schema="leny",
    )
    op.create_table(
        "documentos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("folder_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.Integer()),
        sa.Column("state", sa.String(16), server_default="active", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("purge_after", sa.DateTime(timezone=True)),
        sa.Column("deleted_by", sa.Integer()),
        sa.Column("published_version_id", sa.Uuid()),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["folder_id"], ["leny.carpetas.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["deleted_by"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("length(trim(title)) BETWEEN 1 AND 200", name="ck_leny_document_title"),
        sa.CheckConstraint("state IN ('active', 'trash', 'purging')", name="ck_leny_document_state"),
        sa.CheckConstraint("revision > 0", name="ck_leny_document_revision"),
        sa.CheckConstraint("published_version_id IS NULL", name="ck_leny_document_unpublished_stage01"),
        sa.CheckConstraint(
            "(state = 'active' AND deleted_at IS NULL AND purge_after IS NULL AND deleted_by IS NULL) OR "
            "(state IN ('trash', 'purging') AND deleted_at IS NOT NULL AND purge_after IS NOT NULL "
            "AND deleted_by IS NOT NULL AND purge_after >= deleted_at)",
            name="ck_leny_document_trash_dates",
        ),
        schema="leny",
    )
    op.create_index("ix_leny_document_folder_state_updated", "documentos", ["folder_id", "state", "updated_at", "id"], schema="leny")
    op.create_index("ix_leny_document_state_updated", "documentos", ["state", "updated_at", "id"], schema="leny")
    op.create_index("ix_leny_document_expiry", "documentos", ["purge_after", "id"], schema="leny", postgresql_where=sa.text("state IN ('trash', 'purging')"))
    op.create_table(
        "documento_roles_lectura",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("document_id", "role_id"),
        sa.ForeignKeyConstraint(["document_id"], ["leny.documentos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="RESTRICT"),
        schema="leny",
    )
    op.create_table(
        "documento_versiones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(180), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("media_type", sa.String(100), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("preview_key", sa.String(180)),
        sa.Column("preview_type", sa.String(100)),
        sa.Column("preview_size_bytes", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("status", sa.String(32), server_default="pending_contextualization", nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["document_id"], ["leny.documentos.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("document_id", "number", name="uq_leny_document_version_number"),
        sa.UniqueConstraint("document_id", "id", name="uq_leny_document_version_owner"),
        sa.UniqueConstraint("storage_key", name="uq_leny_document_storage_key"),
        sa.UniqueConstraint("preview_key", name="uq_leny_document_preview_key"),
        sa.CheckConstraint("number > 0", name="ck_leny_document_version_number"),
        sa.CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="ck_leny_document_sha256"),
        sa.CheckConstraint("size_bytes > 0 AND size_bytes <= 10485760", name="ck_leny_document_size"),
        sa.CheckConstraint(
            "media_type IN ('application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'image/jpeg', 'image/png')",
            name="ck_leny_document_media_type",
        ),
        sa.CheckConstraint("media_type NOT IN ('image/jpeg', 'image/png') OR size_bytes <= 5242880", name="ck_leny_document_image_size"),
        sa.CheckConstraint("status = 'pending_contextualization'", name="ck_leny_document_pending_stage01"),
        sa.CheckConstraint(
            "(preview_key IS NULL AND preview_type IS NULL AND preview_size_bytes = 0) OR "
            "(preview_key IS NOT NULL AND preview_type IS NOT NULL AND preview_size_bytes > 0)",
            name="ck_leny_document_preview_metadata",
        ),
        schema="leny",
    )
    op.create_foreign_key(
        "fk_leny_document_published_owner", "documentos", "documento_versiones",
        ["id", "published_version_id"], ["document_id", "id"],
        source_schema="leny", referent_schema="leny", ondelete="RESTRICT",
    )
    op.create_table(
        "documento_operaciones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("document_id", sa.Uuid()),
        sa.Column("version_id", sa.Uuid()),
        sa.Column("payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("error_code", sa.String(64)),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["account_id"], ["cuentas.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("length(trim(kind)) BETWEEN 1 AND 40", name="ck_leny_document_operation_kind"),
        sa.CheckConstraint("fingerprint ~ '^[0-9a-f]{64}$'", name="ck_leny_document_operation_fingerprint"),
        sa.CheckConstraint("status IN ('receiving', 'staged', 'completed', 'failed', 'purging')", name="ck_leny_document_operation_status"),
        sa.CheckConstraint("jsonb_typeof(payload) = 'object'", name="ck_leny_document_operation_payload"),
        schema="leny",
    )
    op.create_index("ix_leny_document_operation_reconcile", "documento_operaciones", ["updated_at", "id"], schema="leny", postgresql_where=sa.text("status IN ('receiving', 'staged', 'purging')"))
    op.create_index("ix_leny_document_operation_user_created", "documento_operaciones", ["user_id", "created_at"], schema="leny")


def downgrade():
    # Explicit order; never drop the schema or existing conversational objects.
    op.drop_table("documento_operaciones", schema="leny")
    op.drop_constraint("fk_leny_document_published_owner", "documentos", schema="leny", type_="foreignkey")
    op.drop_table("documento_versiones", schema="leny")
    op.drop_table("documento_roles_lectura", schema="leny")
    op.drop_table("documentos", schema="leny")
    op.drop_table("carpeta_roles_lectura", schema="leny")
    op.drop_table("carpetas", schema="leny")
