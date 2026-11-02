"""internal receipts module hardening

Revision ID: 20260525_0008
Revises: 20260524_0007
Create Date: 2026-05-25 10:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260525_0008"
down_revision = "20260524_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_comprobante_pago_pedido",
        "comprobante_interno",
        "pago_pedido",
        ["ppd_id"],
        ["ppd_id"],
        onupdate="CASCADE",
        ondelete="RESTRICT",
    )
    op.create_index("ix_coi_cod", "comprobante_interno", ["coi_cod"], unique=False)
    op.create_index("ix_coi_fec", "comprobante_interno", ["coi_fec"], unique=False)
    op.create_index("ix_coi_mon_id", "comprobante_interno", ["mon_id"], unique=False)
    op.create_index("ix_coi_cli_id", "comprobante_interno", ["cli_id"], unique=False)
    op.create_index("ix_coi_usu_id", "comprobante_interno", ["usu_id"], unique=False)
    op.execute(
        sa.text(
            "create unique index if not exists uq_comprobante_veb_id on comprobante_interno (veb_id) where veb_id is not null"
        )
    )
    op.execute(
        sa.text(
            "create unique index if not exists uq_comprobante_ppd_id on comprobante_interno (ppd_id) where ppd_id is not null"
        )
    )
    op.execute(
        sa.text(
            "create unique index if not exists uq_comprobante_sfl_id on comprobante_interno (sfl_id) where sfl_id is not null"
        )
    )


def downgrade() -> None:
    op.execute("drop index if exists uq_comprobante_sfl_id")
    op.execute("drop index if exists uq_comprobante_ppd_id")
    op.execute("drop index if exists uq_comprobante_veb_id")
    op.drop_index("ix_coi_usu_id", table_name="comprobante_interno")
    op.drop_index("ix_coi_cli_id", table_name="comprobante_interno")
    op.drop_index("ix_coi_mon_id", table_name="comprobante_interno")
    op.drop_index("ix_coi_fec", table_name="comprobante_interno")
    op.drop_index("ix_coi_cod", table_name="comprobante_interno")
    op.drop_constraint("fk_comprobante_pago_pedido", "comprobante_interno", type_="foreignkey")
