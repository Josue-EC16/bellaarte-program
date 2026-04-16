"""clientes schema

Revision ID: 20260413_0003
Revises: 20260413_0002
Create Date: 2026-04-13 02:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260413_0003"
down_revision = "20260413_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "CLIENTE",
        sa.Column("CLI_ID", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("CLI_COD", sa.String(length=20), nullable=False),
        sa.Column("CLI_NOM", sa.String(length=100), nullable=False),
        sa.Column("CLI_APE_PAT", sa.String(length=100), nullable=False),
        sa.Column("CLI_APE_MAT", sa.String(length=100), nullable=True),
        sa.Column("CLI_CEL", sa.String(length=30), nullable=False),
        sa.Column("CLI_CEL_REF", sa.String(length=30), nullable=True),
        sa.Column("CLI_NOM_CEL_REF", sa.String(length=120), nullable=True),
        sa.Column("CLI_COR", sa.String(length=120), nullable=True),
        sa.Column("CLI_CI", sa.String(length=30), nullable=True),
        sa.Column("CLI_NAC", sa.String(length=100), nullable=True),
        sa.Column("CLI_ZONA", sa.String(length=100), nullable=True),
        sa.Column("CLI_CALLE", sa.String(length=100), nullable=True),
        sa.Column("CLI_OBS", sa.Text(), nullable=True),
        sa.Column("CLI_HAB", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("CLI_FEC_REG", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("CLI_COD", name="UQ_CLI_COD"),
    )


def downgrade() -> None:
    op.drop_table("CLIENTE")
