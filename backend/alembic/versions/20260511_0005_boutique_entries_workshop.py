"""boutique entries and workshop inventory

Revision ID: 20260511_0005
Revises: 20260427_0004
Create Date: 2026-05-11 00:30:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260511_0005"
down_revision = "20260427_0004"
branch_labels = None
depends_on = None


motivo_entrada_item_enum = postgresql.ENUM(
    "entrada_stock",
    "produccion_interna",
    "devolucion",
    "ajuste_positivo",
    "registro_inicial",
    "otro",
    name="motivo_entrada_item",
    create_type=False,
)
unidad_medida_enum = postgresql.ENUM(
    "metro",
    "centimetro",
    "rollo",
    "caja",
    "kilogramo",
    "gramo",
    "yarda",
    "randa",
    "unidad",
    "otro",
    name="unidad_medida",
    create_type=False,
)
motivo_entrada_taller_enum = postgresql.ENUM(
    "entrada_stock",
    "devolucion",
    "ajuste_positivo",
    "registro_inicial",
    "otro",
    name="motivo_entrada_taller",
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


def upgrade() -> None:
    bind = op.get_bind()
    motivo_entrada_item_enum.create(bind, checkfirst=True)
    unidad_medida_enum.create(bind, checkfirst=True)
    motivo_entrada_taller_enum.create(bind, checkfirst=True)
    copa_talla_enum.create(bind, checkfirst=True)

    op.create_table(
        "detalle_brassier_boutique",
        sa.Column("dbb_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("itb_id", sa.BigInteger(), nullable=False),
        sa.Column("dbb_copa_tall", copa_talla_enum, nullable=False),
        sa.Column("dbb_tiene_encaje", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("dbb_marca", sa.String(length=50), nullable=True),
        sa.Column("dbb_obs", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["itb_id"], ["item_boutique.itb_id"], name="fk_dbb_itb", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.UniqueConstraint("itb_id", name="uq_dbb_itb_id"),
    )

    op.create_table(
        "entrada_item_boutique",
        sa.Column("eib_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("itb_id", sa.BigInteger(), nullable=False),
        sa.Column("usu_id", sa.Integer(), nullable=False),
        sa.Column("pro_id", sa.BigInteger(), nullable=True),
        sa.Column("eib_fec", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("eib_cant", sa.Integer(), nullable=False),
        sa.Column("eib_costo_unitario", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("eib_motivo", motivo_entrada_item_enum, nullable=False, server_default="entrada_stock"),
        sa.Column("eib_doc_ref", sa.String(length=80), nullable=True),
        sa.Column("eib_obs", sa.Text(), nullable=True),
        sa.Column("eib_estado", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["itb_id"], ["item_boutique.itb_id"], name="fk_eib_itb", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["usu_id"], ["usuarios.id"], name="fk_eib_usu", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pro_id"], ["proveedor.pro_id"], name="fk_eib_pro", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.CheckConstraint("eib_cant > 0", name="ck_eib_cant"),
        sa.CheckConstraint("eib_costo_unitario >= 0", name="ck_eib_costo_unitario"),
    )
    op.create_index("ix_eib_itb_id", "entrada_item_boutique", ["itb_id"], unique=False)
    op.create_index("ix_eib_fec", "entrada_item_boutique", ["eib_fec"], unique=False)

    op.create_table(
        "tipo_inventario_taller",
        sa.Column("tit_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("tit_nom", sa.String(length=100), nullable=False),
        sa.Column("tit_des", sa.String(length=200), nullable=True),
        sa.Column("tit_hab", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("tit_fec_reg", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("tit_nom", name="uq_tit_nom"),
    )

    op.create_table(
        "inventario_taller",
        sa.Column("int_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("tit_id", sa.BigInteger(), nullable=False),
        sa.Column("pro_id", sa.BigInteger(), nullable=True),
        sa.Column("int_cod", sa.String(length=40), nullable=False),
        sa.Column("int_nom", sa.String(length=100), nullable=False),
        sa.Column("int_color", sa.String(length=50), nullable=False),
        sa.Column("int_largo", sa.Numeric(6, 2), nullable=True),
        sa.Column("int_ancho", sa.Numeric(6, 2), nullable=True),
        sa.Column("int_material", sa.String(length=80), nullable=True),
        sa.Column("int_des", sa.Text(), nullable=True),
        sa.Column("int_costo_ref", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("int_stock", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("int_uni_med", unidad_medida_enum, nullable=False),
        sa.Column("int_stock_min", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("int_estado", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("int_obs", sa.Text(), nullable=True),
        sa.Column("int_fec_reg", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["pro_id"], ["proveedor.pro_id"], name="fk_int_pro", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tit_id"], ["tipo_inventario_taller.tit_id"], name="fk_int_tit", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.UniqueConstraint("int_cod", name="uq_int_cod"),
        sa.CheckConstraint("int_costo_ref >= 0", name="ck_int_costo_ref"),
        sa.CheckConstraint("int_stock >= 0", name="ck_int_stock"),
        sa.CheckConstraint("int_stock_min >= 0", name="ck_int_stock_min"),
        sa.CheckConstraint("int_largo is null or int_largo >= 0", name="ck_int_largo"),
        sa.CheckConstraint("int_ancho is null or int_ancho >= 0", name="ck_int_ancho"),
    )

    op.create_table(
        "entrada_inventario_taller",
        sa.Column("emt_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("int_id", sa.BigInteger(), nullable=False),
        sa.Column("usu_id", sa.Integer(), nullable=False),
        sa.Column("pro_id", sa.BigInteger(), nullable=True),
        sa.Column("emt_fec", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("emt_can", sa.Numeric(12, 2), nullable=False),
        sa.Column("emt_uni_med", unidad_medida_enum, nullable=False),
        sa.Column("emt_costo_unitario", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("emt_motivo", motivo_entrada_taller_enum, nullable=False, server_default="entrada_stock"),
        sa.Column("emt_doc_ref", sa.String(length=80), nullable=True),
        sa.Column("emt_obs", sa.Text(), nullable=True),
        sa.Column("emt_estado", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["int_id"], ["inventario_taller.int_id"], name="fk_emt_int", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["usu_id"], ["usuarios.id"], name="fk_emt_usu", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pro_id"], ["proveedor.pro_id"], name="fk_emt_pro", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.CheckConstraint("emt_can > 0", name="ck_emt_can"),
        sa.CheckConstraint("emt_costo_unitario >= 0", name="ck_emt_costo_unitario"),
    )
    op.create_index("ix_emt_int_id", "entrada_inventario_taller", ["int_id"], unique=False)
    op.create_index("ix_emt_fec", "entrada_inventario_taller", ["emt_fec"], unique=False)

    op.create_table(
        "salida_material_taller",
        sa.Column("smt_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("int_id", sa.BigInteger(), nullable=False),
        sa.Column("usu_id", sa.Integer(), nullable=True),
        sa.Column("smt_fec", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("smt_can", sa.Numeric(12, 2), nullable=False),
        sa.Column("smt_uni_med", unidad_medida_enum, nullable=False),
        sa.Column("smt_destino", sa.String(length=50), nullable=False),
        sa.Column("smt_obs1", sa.Text(), nullable=True),
        sa.Column("smt_obs2", sa.Text(), nullable=True),
        sa.Column("smt_estado", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["int_id"], ["inventario_taller.int_id"], name="fk_smt_int", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["usu_id"], ["usuarios.id"], name="fk_smt_usu", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.CheckConstraint("smt_can > 0", name="ck_smt_can"),
    )
    op.create_index("ix_smt_int_id", "salida_material_taller", ["int_id"], unique=False)
    op.create_index("ix_smt_fec", "salida_material_taller", ["smt_fec"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_smt_fec", table_name="salida_material_taller")
    op.drop_index("ix_smt_int_id", table_name="salida_material_taller")
    op.drop_table("salida_material_taller")
    op.drop_index("ix_emt_fec", table_name="entrada_inventario_taller")
    op.drop_index("ix_emt_int_id", table_name="entrada_inventario_taller")
    op.drop_table("entrada_inventario_taller")
    op.drop_table("inventario_taller")
    op.drop_table("tipo_inventario_taller")
    op.drop_index("ix_eib_fec", table_name="entrada_item_boutique")
    op.drop_index("ix_eib_itb_id", table_name="entrada_item_boutique")
    op.drop_table("entrada_item_boutique")
    op.drop_table("detalle_brassier_boutique")

    bind = op.get_bind()
    motivo_entrada_taller_enum.drop(bind, checkfirst=True)
    unidad_medida_enum.drop(bind, checkfirst=True)
    motivo_entrada_item_enum.drop(bind, checkfirst=True)
