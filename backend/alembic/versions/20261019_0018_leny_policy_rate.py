"""LENY-only policy metadata and per-person rolling admission quota."""
from alembic import op
import sqlalchemy as sa

revision = "20261019_0018"
down_revision = "20261019_0017"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("mensajes", sa.Column("category", sa.String(64)), schema="leny")
    op.add_column("mensajes", sa.Column("reason", sa.String(120)), schema="leny")
    op.add_column("mensajes", sa.Column("policy_version", sa.String(32)), schema="leny")
    # Existing turns have not been checked by the new policy: fail closed.
    op.add_column("mensajes", sa.Column("context_eligible", sa.Boolean(), server_default=sa.false(), nullable=False), schema="leny")
    op.create_table(
        "rate_users", sa.Column("user_id", sa.Integer(), primary_key=True),
        sa.Column("last_quota_audit_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"], ondelete="RESTRICT"), schema="leny",
    )
    op.create_table(
        "admissions", sa.Column("user_id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.Uuid(), primary_key=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("admitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"], ondelete="RESTRICT"), schema="leny",
    )
    op.create_index("ix_leny_admission_user_time", "admissions", ["user_id", "admitted_at"], schema="leny")


def downgrade():
    op.drop_table("admissions", schema="leny")
    op.drop_table("rate_users", schema="leny")
    for name in ("context_eligible", "policy_version", "reason", "category"):
        op.drop_column("mensajes", name, schema="leny")
