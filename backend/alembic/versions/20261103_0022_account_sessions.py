"""Add revocable sessions and durable login throttling without rewriting accounts.

Revision ID: 20261103_0022
Revises: 20261020_0021
Existing tokens intentionally require a new login after deployment.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261103_0022"
down_revision = "20261020_0021"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("cuentas", sa.Column("auth_version", sa.Integer(), server_default="0", nullable=False))
    op.add_column("cuentas", sa.Column("security_version", sa.Integer(), server_default="0", nullable=False))
    op.create_check_constraint("ck_cuentas_auth_version", "cuentas", "auth_version >= 0")
    op.create_check_constraint("ck_cuentas_security_version", "cuentas", "security_version >= 0")
    op.create_table("sesion_cuenta",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("cuenta_id", sa.Integer(), sa.ForeignKey("cuentas.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("auth_version", sa.Integer(), nullable=False),
        sa.Column("refresh_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revocation_reason", sa.String(40)),
        sa.CheckConstraint("auth_version >= 0", name="ck_sesion_cuenta_auth_version"),
        sa.CheckConstraint("expires_at > created_at", name="ck_sesion_cuenta_expiration"))
    op.create_index("ix_sesion_cuenta_account", "sesion_cuenta", ["cuenta_id", "revoked_at"])
    op.create_index("ix_sesion_cuenta_expiry", "sesion_cuenta", ["expires_at"])
    op.create_table("auth_login_bucket",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("failures", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("failures >= 0", name="ck_auth_login_bucket_failures"))
    op.create_index("ix_auth_login_bucket_expires", "auth_login_bucket", ["expires_at"])


def downgrade():
    # A rollback discards session metadata, never business records or passwords.
    op.drop_table("auth_login_bucket")
    op.drop_table("sesion_cuenta")
    op.drop_constraint("ck_cuentas_security_version", "cuentas", type_="check")
    op.drop_constraint("ck_cuentas_auth_version", "cuentas", type_="check")
    op.drop_column("cuentas", "security_version")
    op.drop_column("cuentas", "auth_version")
