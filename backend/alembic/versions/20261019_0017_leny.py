"""Isolated LENY conversation storage; no alterations to business tables.

Revision ID: 20261019_0017
Revises: 20261018_0016
"""
from alembic import op
import sqlalchemy as sa

revision = "20261019_0017"
down_revision = "20261018_0016"
branch_labels = None
depends_on = None


def upgrade():
    # Fail if an unrelated schema already exists rather than taking ownership.
    op.execute(sa.schema.CreateSchema("leny"))
    op.create_table(
        "conversaciones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["account_id"], ["cuentas.id"], ondelete="RESTRICT"),
        schema="leny",
    )
    op.create_index("ix_leny_conversation_owner_updated", "conversaciones", ["user_id", "updated_at"], schema="leny")
    op.create_table(
        "mensajes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("model", sa.String(120)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["conversation_id"], ["leny.conversaciones.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("conversation_id", "sequence", name="uq_leny_message_sequence"),
        sa.UniqueConstraint("request_id", "role", name="uq_leny_request_role"),
        sa.CheckConstraint("sequence > 0", name="ck_leny_sequence_positive"),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_leny_message_role"),
        sa.CheckConstraint("status IN ('generating', 'completed', 'interrupted', 'failed')", name="ck_leny_message_status"),
        schema="leny",
    )
    op.create_index("ix_leny_message_conversation_created", "mensajes", ["conversation_id", "created_at"], schema="leny")


def downgrade():
    op.drop_table("mensajes", schema="leny")
    op.drop_table("conversaciones", schema="leny")
    # RESTRICT is deliberate: unknown objects must not be silently removed.
    op.execute(sa.schema.DropSchema("leny"))
