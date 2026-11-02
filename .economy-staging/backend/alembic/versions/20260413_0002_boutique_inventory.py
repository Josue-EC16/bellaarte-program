"""boutique inventory schema

Revision ID: 20260413_0002
Revises: 20260408_0001
Create Date: 2026-04-13 01:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260413_0002"
down_revision = "20260408_0001"
branch_labels = None
depends_on = None


tipo_vestido_enum = postgresql.ENUM(
    "vestido_de_novia",
    "vestido_de_civil",
    "vestido_de_15_años",
    "vestido_de_fiesta_o_evento",
    "vestido_de_niña",
    "damas",
    "otro",
    name="tipo_vestido",
    create_type=False,
)
copa_talla_enum = postgresql.ENUM(
    "copa_aa",
    "copa_a",
    "copa_b",
    "copa_c",
    "copa_d",
    "copa_dd",
    "copa_e",
    "copa_f",
    "copa_g",
    name="copa_talla_vestido_boutique",
    create_type=False,
)
talla_vestido_enum = postgresql.ENUM(
    "talla_xxs",
    "talla_xs",
    "talla_s",
    "talla_m",
    "talla_l",
    "talla_xl",
    "talla_xxl",
    "talla_xxxl",
    name="talla_vestido_boutique",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    tipo_vestido_enum.create(bind, checkfirst=True)
    copa_talla_enum.create(bind, checkfirst=True)
    talla_vestido_enum.create(bind, checkfirst=True)

    op.create_table(
        "proveedor",
        sa.Column("pro_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("pro_nom", sa.String(length=100), nullable=False),
        sa.Column("pro_ape_pat", sa.String(length=50), nullable=True),
        sa.Column("pro_ape_mat", sa.String(length=50), nullable=True),
        sa.Column("pro_nom_comercial", sa.String(length=120), nullable=True),
        sa.Column("pro_cel", sa.String(length=30), nullable=True),
        sa.Column("pro_cel_sec", sa.String(length=30), nullable=True),
        sa.Column("pro_cor", sa.String(length=120), nullable=True),
        sa.Column("pro_pais", sa.String(length=50), nullable=True),
        sa.Column("pro_ciudad", sa.String(length=70), nullable=True),
        sa.Column("pro_dir", sa.String(length=150), nullable=True),
        sa.Column("pro_obs", sa.Text(), nullable=True),
        sa.Column("pro_hab", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("pro_fec_reg", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("pro_cel", name="uq_proveedor_cel"),
        sa.UniqueConstraint("pro_cor", name="uq_proveedor_cor"),
    )

    op.create_table(
        "tipo_item_boutique",
        sa.Column("tib_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("tib_nom", sa.String(length=100), nullable=False),
        sa.Column("tib_des", sa.String(length=200), nullable=True),
        sa.Column("tib_hab", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("tib_fec_reg", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("tib_nom", name="uq_tipo_item_boutique_nom"),
    )

    op.create_table(
        "item_boutique",
        sa.Column("itb_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("tib_id", sa.BigInteger(), nullable=False),
        sa.Column("pro_id", sa.BigInteger(), nullable=True),
        sa.Column("itb_cod", sa.String(length=40), nullable=False),
        sa.Column("itb_nom", sa.String(length=150), nullable=False),
        sa.Column("itb_color_prim", sa.String(length=60), nullable=False),
        sa.Column("itb_color_secun", sa.String(length=60), nullable=True),
        sa.Column("itb_material", sa.String(length=100), nullable=False),
        sa.Column("itb_largo", sa.Numeric(6, 2), nullable=True),
        sa.Column("itb_ancho", sa.Numeric(6, 2), nullable=True),
        sa.Column("itb_precio_compra", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("itb_precio_venta", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("itb_stock", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("itb_stock_min", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("itb_detalle", sa.Text(), nullable=True),
        sa.Column("itb_estado", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("itb_fec_reg", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["tib_id"], ["tipo_item_boutique.tib_id"], name="fk_itb_tib", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pro_id"], ["proveedor.pro_id"], name="fk_itb_pro", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.CheckConstraint("itb_largo IS NULL OR itb_largo >= 0", name="ck_itb_largo"),
        sa.CheckConstraint("itb_ancho IS NULL OR itb_ancho >= 0", name="ck_itb_ancho"),
        sa.CheckConstraint("itb_precio_compra >= 0", name="ck_itb_precio_compra"),
        sa.CheckConstraint("itb_precio_venta >= 0", name="ck_itb_precio_venta"),
        sa.CheckConstraint("itb_stock >= 0", name="ck_itb_stock"),
        sa.CheckConstraint("itb_stock_min >= 0", name="ck_itb_stock_min"),
        sa.UniqueConstraint("itb_cod", name="uq_item_boutique_cod"),
    )

    op.create_table(
        "detalle_vestido_boutique",
        sa.Column("dvb_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("itb_id", sa.BigInteger(), nullable=False),
        sa.Column("dvb_tipo_vestido", tipo_vestido_enum, nullable=False),
        sa.Column("dvb_corte_falda", sa.String(length=100), nullable=True),
        sa.Column("dvb_tipo_escote", sa.String(length=100), nullable=True),
        sa.Column("dvb_tiene_cola", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("dvb_tiene_manga", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("dvb_tiene_pedreria", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("dvb_copa_talla", copa_talla_enum, nullable=True),
        sa.Column("dvb_talla", talla_vestido_enum, nullable=False),
        sa.Column("dvb_largo_falda", sa.Numeric(6, 2), nullable=True),
        sa.Column("dvb_obs", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["itb_id"], ["item_boutique.itb_id"], name="fk_dvb_itb", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.CheckConstraint("dvb_largo_falda IS NULL OR dvb_largo_falda >= 0", name="ck_dvb_largo_falda"),
        sa.UniqueConstraint("itb_id", name="uq_dvb_itb_id"),
    )

    op.create_table(
        "detalle_velo_boutique",
        sa.Column("dve_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("itb_id", sa.BigInteger(), nullable=False),
        sa.Column("dve_tipo_velo", sa.String(length=50), nullable=False),
        sa.Column("dve_capas", sa.SmallInteger(), nullable=True),
        sa.Column("dve_borde", sa.String(length=100), nullable=True),
        sa.Column("dve_decoracion", sa.Text(), nullable=True),
        sa.Column("dve_obs", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["itb_id"], ["item_boutique.itb_id"], name="fk_dve_itb", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.CheckConstraint("dve_capas IS NULL OR dve_capas > 0", name="ck_dve_capas"),
        sa.UniqueConstraint("itb_id", name="uq_dve_itb_id"),
    )

    op.create_table(
        "detalle_bouquet_boutique",
        sa.Column("dbo_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("itb_id", sa.BigInteger(), nullable=False),
        sa.Column("dbo_tipo_bouquet", sa.String(length=100), nullable=True),
        sa.Column("dbo_forma", sa.String(length=50), nullable=True),
        sa.Column("dbo_tipo_flor", sa.String(length=50), nullable=True),
        sa.Column("dbo_decoracion", sa.Text(), nullable=True),
        sa.Column("dbo_obs", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["itb_id"], ["item_boutique.itb_id"], name="fk_dbo_itb", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.UniqueConstraint("itb_id", name="uq_dbo_itb_id"),
    )


def downgrade() -> None:
    op.drop_table("detalle_bouquet_boutique")
    op.drop_table("detalle_velo_boutique")
    op.drop_table("detalle_vestido_boutique")
    op.drop_table("item_boutique")
    op.drop_table("tipo_item_boutique")
    op.drop_table("proveedor")

    bind = op.get_bind()
    talla_vestido_enum.drop(bind, checkfirst=True)
    copa_talla_enum.drop(bind, checkfirst=True)
    tipo_vestido_enum.drop(bind, checkfirst=True)
