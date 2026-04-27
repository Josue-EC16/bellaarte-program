"""boutique sales schema

Revision ID: 20260427_0004
Revises: 20260413_0003
Create Date: 2026-04-27 01:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260427_0004"
down_revision = "20260413_0003"
branch_labels = None
depends_on = None


metodo_pago_enum = postgresql.ENUM(
    "EFECTIVO",
    "QR",
    "MIXTO",
    "TRANSACCION",
    "TARJETA",
    "TICKET_O_VALE",
    name="METODO_PAGO",
    create_type=False,
)
motivo_desc_venta_enum = postgresql.ENUM(
    "REBAJA",
    "PROMOCION",
    name="MOTIVO_DESC_VENTA_BOUTIQUE",
    create_type=False,
)
estado_venta_enum = postgresql.ENUM(
    "ACTIVA",
    "CANCELADA",
    "ANULADA",
    name="ESTADO_VENTA_BOUTIQUE",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(
        "EFECTIVO",
        "QR",
        "MIXTO",
        "TRANSACCION",
        "TARJETA",
        "TICKET_O_VALE",
        name="METODO_PAGO",
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "REBAJA",
        "PROMOCION",
        name="MOTIVO_DESC_VENTA_BOUTIQUE",
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "ACTIVA",
        "CANCELADA",
        "ANULADA",
        name="ESTADO_VENTA_BOUTIQUE",
    ).create(bind, checkfirst=True)

    op.create_table(
        "VENTA_BOUTIQUE",
        sa.Column("VEB_ID", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("ITB_ID", sa.BigInteger(), nullable=False),
        sa.Column("USU_ID", sa.Integer(), nullable=False),
        sa.Column("CLI_ID", sa.BigInteger(), nullable=True),
        sa.Column("VEB_FEC", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("VEB_CANT", sa.Numeric(12, 2), nullable=False),
        sa.Column("VEB_PRE_UNI", sa.Numeric(12, 2), nullable=False),
        sa.Column("VEB_DESCUENTO", sa.Numeric(12, 2), nullable=True),
        sa.Column("VEB_MOTIVO_DESC", motivo_desc_venta_enum, nullable=True),
        sa.Column(
            "VEB_TOT",
            sa.Numeric(12, 2),
            sa.Computed('ROUND("VEB_CANT" * "VEB_PRE_UNI" - COALESCE("VEB_DESCUENTO", 0), 2)', persisted=True),
            nullable=False,
        ),
        sa.Column("VEB_METODO_PAGO", metodo_pago_enum, nullable=False),
        sa.Column("VEB_OBS", sa.Text(), nullable=True),
        sa.Column("VEB_ESTADO", estado_venta_enum, nullable=False, server_default="ACTIVA"),
        sa.ForeignKeyConstraint(
            ["ITB_ID"],
            ["ITEM_BOUTIQUE.ITB_ID"],
            name="FK_VEB_ITB",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["USU_ID"],
            ["usuarios.id"],
            name="FK_VEB_USU",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["CLI_ID"],
            ["CLIENTE.CLI_ID"],
            name="FK_VEB_CLI",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint('"VEB_CANT" > 0', name="CK_VEB_CANT"),
        sa.CheckConstraint('"VEB_PRE_UNI" >= 0', name="CK_VEB_PRE_UNI"),
        sa.CheckConstraint(
            '"VEB_DESCUENTO" IS NULL OR ("VEB_DESCUENTO" >= 0 AND "VEB_DESCUENTO" <= ("VEB_CANT" * "VEB_PRE_UNI"))',
            name="CK_VEB_DESCUENTO",
        ),
        sa.CheckConstraint(
            '("VEB_DESCUENTO" IS NULL AND "VEB_MOTIVO_DESC" IS NULL) OR ("VEB_DESCUENTO" IS NOT NULL AND "VEB_MOTIVO_DESC" IS NOT NULL)',
            name="CK_VEB_DESC_MOTIVO",
        ),
    )
    op.create_index("IX_VEB_FEC", "VENTA_BOUTIQUE", ["VEB_FEC"], unique=False)
    op.create_index("IX_VEB_ESTADO", "VENTA_BOUTIQUE", ["VEB_ESTADO"], unique=False)
    op.create_index("IX_VEB_METODO_PAGO", "VENTA_BOUTIQUE", ["VEB_METODO_PAGO"], unique=False)
    op.create_index("IX_VEB_ITB_ID", "VENTA_BOUTIQUE", ["ITB_ID"], unique=False)
    op.create_index("IX_VEB_CLI_ID", "VENTA_BOUTIQUE", ["CLI_ID"], unique=False)
    op.create_index("IX_VEB_USU_ID", "VENTA_BOUTIQUE", ["USU_ID"], unique=False)


def downgrade() -> None:
    op.drop_index("IX_VEB_USU_ID", table_name="VENTA_BOUTIQUE")
    op.drop_index("IX_VEB_CLI_ID", table_name="VENTA_BOUTIQUE")
    op.drop_index("IX_VEB_ITB_ID", table_name="VENTA_BOUTIQUE")
    op.drop_index("IX_VEB_METODO_PAGO", table_name="VENTA_BOUTIQUE")
    op.drop_index("IX_VEB_ESTADO", table_name="VENTA_BOUTIQUE")
    op.drop_index("IX_VEB_FEC", table_name="VENTA_BOUTIQUE")
    op.drop_table("VENTA_BOUTIQUE")

    bind = op.get_bind()
    postgresql.ENUM(name="ESTADO_VENTA_BOUTIQUE").drop(bind, checkfirst=True)
    postgresql.ENUM(name="MOTIVO_DESC_VENTA_BOUTIQUE").drop(bind, checkfirst=True)
    postgresql.ENUM(name="METODO_PAGO").drop(bind, checkfirst=True)
