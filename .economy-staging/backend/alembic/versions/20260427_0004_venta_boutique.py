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
    "efectivo",
    "qr",
    "transaccion",
    "tarjeta",
    "ticket_o_vale",
    name="metodo_pago",
    create_type=False,
)
motivo_desc_venta_enum = postgresql.ENUM(
    "rebaja",
    "promocion",
    "bonificacion",
    "administrativo",
    name="motivo_desc_venta_boutique",
    create_type=False,
)
estado_venta_enum = postgresql.ENUM(
    "activa",
    "cancelada",
    "anulada",
    name="estado_venta_boutique",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    metodo_pago_enum.create(bind, checkfirst=True)
    motivo_desc_venta_enum.create(bind, checkfirst=True)
    estado_venta_enum.create(bind, checkfirst=True)

    op.create_table(
        "moneda",
        sa.Column("mon_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("mon_cod", sa.String(length=10), nullable=False),
        sa.Column("mon_nom", sa.String(length=80), nullable=False),
        sa.Column("mon_simbolo", sa.String(length=10), nullable=True),
        sa.Column("mon_es_base", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("mon_hab", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("mon_fec_reg", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("mon_cod", name="uq_moneda_cod"),
    )
    op.create_index("uq_moneda_base", "moneda", ["mon_es_base"], unique=True, postgresql_where=sa.text("mon_es_base = true"))

    op.create_table(
        "tipo_cambio_moneda",
        sa.Column("tcm_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("mon_id", sa.BigInteger(), nullable=False),
        sa.Column("usu_id", sa.Integer(), nullable=False),
        sa.Column("tcm_valor_bob", sa.Numeric(12, 4), nullable=False),
        sa.Column("tcm_fec_reg", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("tcm_obs", sa.Text(), nullable=True),
        sa.Column("tcm_activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["mon_id"], ["moneda.mon_id"], name="fk_tcm_moneda", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["usu_id"], ["usuarios.id"], name="fk_tcm_usuario", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.CheckConstraint("tcm_valor_bob > 0", name="ck_tcm_valor_bob"),
    )
    op.create_index(
        "uq_tipo_cambio_activo_moneda",
        "tipo_cambio_moneda",
        ["mon_id"],
        unique=True,
        postgresql_where=sa.text("tcm_activo = true"),
    )

    op.create_table(
        "venta_boutique",
        sa.Column("veb_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("itb_id", sa.BigInteger(), nullable=False),
        sa.Column("usu_id", sa.Integer(), nullable=False),
        sa.Column("cli_id", sa.BigInteger(), nullable=True),
        sa.Column("mon_id", sa.BigInteger(), nullable=False),
        sa.Column("veb_fec", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("veb_cant", sa.Integer(), nullable=False),
        sa.Column("veb_pre_uni", sa.Numeric(12, 2), nullable=False),
        sa.Column("veb_descuento", sa.Numeric(12, 2), nullable=True),
        sa.Column("veb_motivo_desc", motivo_desc_venta_enum, nullable=True),
        sa.Column(
            "veb_tot",
            sa.Numeric(12, 2),
            sa.Computed("round(veb_cant * veb_pre_uni - coalesce(veb_descuento, 0), 2)", persisted=True),
            nullable=False,
        ),
        sa.Column("veb_tipo_cambio_usado", sa.Numeric(12, 4), nullable=False, server_default="1"),
        sa.Column("veb_total_moneda_orig", sa.Numeric(12, 2), nullable=False),
        sa.Column("veb_metodo_pago", metodo_pago_enum, nullable=False),
        sa.Column("veb_obs", sa.Text(), nullable=True),
        sa.Column("veb_estado", estado_venta_enum, nullable=False, server_default="activa"),
        sa.Column("veb_fec_camb_est", sa.DateTime(timezone=True), nullable=True),
        sa.Column("veb_motivo_camb_est", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["itb_id"], ["item_boutique.itb_id"], name="fk_veb_itb", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["usu_id"], ["usuarios.id"], name="fk_veb_usu", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cli_id"], ["cliente.cli_id"], name="fk_veb_cli", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["mon_id"], ["moneda.mon_id"], name="fk_veb_moneda", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.CheckConstraint(
            "(veb_estado = 'activa' and veb_fec_camb_est IS NULL and veb_motivo_camb_est IS NULL) OR "
            "(veb_estado in ('cancelada', 'anulada') and veb_fec_camb_est IS NOT NULL and veb_motivo_camb_est IS NOT NULL)",
            name="ck_veb_cambio_estado",
        ),
        sa.CheckConstraint("veb_cant > 0", name="ck_veb_cant"),
        sa.CheckConstraint("veb_pre_uni > 0", name="ck_veb_pre_uni"),
        sa.CheckConstraint(
            "veb_descuento IS NULL OR (veb_descuento >= 0 AND veb_descuento <= (veb_cant * veb_pre_uni))",
            name="ck_veb_descuento",
        ),
        sa.CheckConstraint(
            "(veb_descuento IS NULL AND veb_motivo_desc IS NULL) OR (veb_descuento IS NOT NULL AND veb_motivo_desc IS NOT NULL)",
            name="ck_veb_desc_motivo",
        ),
        sa.CheckConstraint("veb_tipo_cambio_usado > 0", name="ck_veb_tipo_cambio"),
        sa.CheckConstraint("veb_total_moneda_orig > 0", name="ck_veb_total_moneda_orig"),
    )
    op.create_index("ix_veb_fec", "venta_boutique", ["veb_fec"], unique=False)
    op.create_index("ix_veb_estado", "venta_boutique", ["veb_estado"], unique=False)
    op.create_index("ix_veb_metodo_pago", "venta_boutique", ["veb_metodo_pago"], unique=False)
    op.create_index("ix_veb_itb_id", "venta_boutique", ["itb_id"], unique=False)
    op.create_index("ix_veb_cli_id", "venta_boutique", ["cli_id"], unique=False)
    op.create_index("ix_veb_usu_id", "venta_boutique", ["usu_id"], unique=False)
    op.create_index("ix_veb_mon_id", "venta_boutique", ["mon_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_veb_mon_id", table_name="venta_boutique")
    op.drop_index("ix_veb_usu_id", table_name="venta_boutique")
    op.drop_index("ix_veb_cli_id", table_name="venta_boutique")
    op.drop_index("ix_veb_itb_id", table_name="venta_boutique")
    op.drop_index("ix_veb_metodo_pago", table_name="venta_boutique")
    op.drop_index("ix_veb_estado", table_name="venta_boutique")
    op.drop_index("ix_veb_fec", table_name="venta_boutique")
    op.drop_table("venta_boutique")
    op.drop_index("uq_tipo_cambio_activo_moneda", table_name="tipo_cambio_moneda")
    op.drop_table("tipo_cambio_moneda")
    op.drop_index("uq_moneda_base", table_name="moneda")
    op.drop_table("moneda")

    bind = op.get_bind()
    estado_venta_enum.drop(bind, checkfirst=True)
    motivo_desc_venta_enum.drop(bind, checkfirst=True)
    metodo_pago_enum.drop(bind, checkfirst=True)
