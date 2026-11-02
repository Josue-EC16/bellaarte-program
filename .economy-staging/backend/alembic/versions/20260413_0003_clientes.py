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
        "cliente",
        sa.Column("cli_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("cli_cod", sa.String(length=20), nullable=False),
        sa.Column("cli_nom", sa.String(length=100), nullable=False),
        sa.Column("cli_ape_pat", sa.String(length=100), nullable=False),
        sa.Column("cli_ape_mat", sa.String(length=100), nullable=True),
        sa.Column("cli_cel", sa.String(length=30), nullable=False),
        sa.Column("cli_cel_ref", sa.String(length=30), nullable=True),
        sa.Column("cli_nom_cel_ref", sa.String(length=120), nullable=True),
        sa.Column("cli_cor", sa.String(length=100), nullable=True),
        sa.Column("cli_ci", sa.String(length=30), nullable=True),
        sa.Column("cli_fecha_nac", sa.Date(), nullable=True),
        sa.Column("cli_pais", sa.String(length=100), nullable=True),
        sa.Column("cli_ciudad", sa.String(length=100), nullable=True),
        sa.Column("cli_zona", sa.String(length=100), nullable=True),
        sa.Column("cli_calle", sa.String(length=100), nullable=True),
        sa.Column("cli_obs", sa.Text(), nullable=True),
        sa.Column("cli_hab", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("cli_fec_reg", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("cli_cod", name="uq_cliente_cod"),
        sa.UniqueConstraint("cli_cor", name="uq_cliente_cor"),
        sa.UniqueConstraint("cli_ci", name="uq_cliente_ci"),
    )


def downgrade() -> None:
    op.drop_table("cliente")
