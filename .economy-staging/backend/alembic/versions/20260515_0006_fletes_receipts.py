"""fletes and internal receipts

Revision ID: 20260515_0006
Revises: 20260511_0005
Create Date: 2026-05-15 12:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260515_0006"
down_revision = "20260511_0005"
branch_labels = None
depends_on = None


estado_flete_enum = postgresql.ENUM(
    "disponible",
    "en_flete",
    "en_revision",
    "agotado",
    "pasado_para_venta",
    "retirado",
    name="estado_flete",
    create_type=False,
)
motivo_desc_flete_enum = postgresql.ENUM(
    "rebaja",
    "promocion",
    "bonificacion",
    "administrativo",
    name="motivo_desc_flete",
    create_type=False,
)
estado_salida_flete_enum = postgresql.ENUM(
    "reservado",
    "en_flete",
    "devuelto",
    "devuelto_con_observacion",
    "devuelto_con_arreglo",
    "anulado",
    name="estado_salida_flete",
    create_type=False,
)
estado_flete_entrega_enum = postgresql.ENUM(
    "bueno",
    "regular",
    "con_observacion",
    name="estado_flete_entrega",
    create_type=False,
)
estado_flete_devolucion_enum = postgresql.ENUM(
    "bueno",
    "regular",
    "dañado",
    "incompleto",
    name="estado_flete_devolucion",
    create_type=False,
)
estado_comprobante_enum = postgresql.ENUM(
    "emitido",
    "anulado",
    name="estado_comprobante",
    create_type=False,
)
metodo_pago_enum = postgresql.ENUM(
    "efectivo",
    "qr",
    "transaccion",
    "tarjeta",
    "ticket_o_vale",
    name="metodo_pago",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    estado_flete_enum.create(bind, checkfirst=True)
    motivo_desc_flete_enum.create(bind, checkfirst=True)
    estado_salida_flete_enum.create(bind, checkfirst=True)
    estado_flete_entrega_enum.create(bind, checkfirst=True)
    estado_flete_devolucion_enum.create(bind, checkfirst=True)
    estado_comprobante_enum.create(bind, checkfirst=True)
    metodo_pago_enum.create(bind, checkfirst=True)

    op.create_table(
        "flete_vestido",
        sa.Column("fle_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("itb_id", sa.BigInteger(), nullable=False),
        sa.Column("usu_id", sa.Integer(), nullable=False),
        sa.Column("fle_precio_flete_ref", sa.Numeric(12, 2), nullable=False),
        sa.Column("fle_max_salidas", sa.SmallInteger(), nullable=False, server_default="3"),
        sa.Column("fle_salidas_actuales", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("fle_estado", estado_flete_enum, nullable=False, server_default="disponible"),
        sa.Column("fle_fec_hab_flete", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("fle_obs", sa.String(length=150), nullable=True),
        sa.Column("fle_hab", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["itb_id"], ["item_boutique.itb_id"], name="fk_flete_vestido_itb", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["usu_id"], ["usuarios.id"], name="fk_flete_vestido_usuario", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.UniqueConstraint("itb_id", name="uq_flete_vestido_itb_id"),
        sa.CheckConstraint("fle_salidas_actuales >= 0 and fle_salidas_actuales <= fle_max_salidas", name="ck_flete_salidas_actuales"),
        sa.CheckConstraint("fle_max_salidas between 1 and 4", name="ck_flete_max_salidas"),
        sa.CheckConstraint("fle_precio_flete_ref > 0", name="ck_precio_flete_ref"),
    )
    op.create_index("ix_flete_vestido_itb_id", "flete_vestido", ["itb_id"], unique=False)
    op.create_index("ix_flete_vestido_estado_hab", "flete_vestido", ["fle_estado", "fle_hab"], unique=False)

    op.create_table(
        "salida_flete",
        sa.Column("sfl_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("fle_id", sa.BigInteger(), nullable=False),
        sa.Column("cli_id", sa.BigInteger(), nullable=False),
        sa.Column("usu_id", sa.Integer(), nullable=False),
        sa.Column("mon_id", sa.BigInteger(), nullable=False),
        sa.Column("sfl_num", sa.SmallInteger(), nullable=False),
        sa.Column("sfl_fec_reg", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("sfl_fec_salida", sa.Date(), nullable=False),
        sa.Column("sfl_fec_devolucion_prevista", sa.Date(), nullable=False),
        sa.Column("sfl_fec_devolucion_real", sa.Date(), nullable=True),
        sa.Column("sfl_precio", sa.Numeric(10, 2), nullable=False),
        sa.Column("sfl_descuento", sa.Numeric(12, 2), nullable=True),
        sa.Column("sfl_motivo_desc", motivo_desc_flete_enum, nullable=True),
        sa.Column("sfl_metodo_pago", metodo_pago_enum, nullable=False),
        sa.Column("sfl_tipo_cambio_usado", sa.Numeric(12, 4), nullable=False, server_default="1"),
        sa.Column(
            "sfl_total_flete",
            sa.Numeric(12, 2),
            sa.Computed("round((sfl_precio - coalesce(sfl_descuento, 0)), 2)", persisted=True),
            nullable=False,
        ),
        sa.Column("sfl_total_flete_moneda_orig", sa.Numeric(12, 2), nullable=False),
        sa.Column("sfl_garantia", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("sfl_garantia_devuelta", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("sfl_estado_salida", estado_salida_flete_enum, nullable=False, server_default="reservado"),
        sa.Column("sfl_fec_camb_est", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sfl_motivo_camb_est", sa.Text(), nullable=True),
        sa.Column("sfl_estado_entrega", estado_flete_entrega_enum, nullable=False),
        sa.Column("sfl_estado_devolucion", estado_flete_devolucion_enum, nullable=True),
        sa.Column("sfl_requiere_arreglo", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sfl_monto_arreglo", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("sfl_descripcion_arreglo", sa.String(length=150), nullable=True),
        sa.Column("sfl_obs_entrega", sa.Text(), nullable=True),
        sa.Column("sfl_obs_devolucion", sa.Text(), nullable=True),
        sa.Column("sfl_hab", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["fle_id"], ["flete_vestido.fle_id"], name="fk_salida_flete_flete", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cli_id"], ["cliente.cli_id"], name="fk_salida_flete_cliente", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["usu_id"], ["usuarios.id"], name="fk_salida_flete_usuario", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["mon_id"], ["moneda.mon_id"], name="fk_sfl_moneda", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.CheckConstraint(
            "((sfl_estado_salida in ('reservado', 'en_flete', 'devuelto', 'devuelto_con_observacion', 'devuelto_con_arreglo') "
            "and sfl_fec_camb_est is null and sfl_motivo_camb_est is null) "
            "or (sfl_estado_salida = 'anulado' and sfl_fec_camb_est is not null and sfl_motivo_camb_est is not null))",
            name="ck_sfl_cambio_estado_salida",
        ),
        sa.CheckConstraint("sfl_precio > 0", name="ck_salida_flete_precio"),
        sa.CheckConstraint("sfl_garantia >= 0", name="ck_salida_flete_garantia"),
        sa.CheckConstraint("sfl_total_flete_moneda_orig > 0", name="ck_sfl_total_flete_moneda_orig"),
        sa.CheckConstraint("sfl_garantia_devuelta >= 0 and sfl_garantia_devuelta <= sfl_garantia", name="ck_salida_flete_garantia_devuelta"),
        sa.CheckConstraint("sfl_monto_arreglo >= 0", name="ck_salida_flete_monto_arreglo"),
        sa.CheckConstraint("sfl_tipo_cambio_usado > 0", name="ck_sfl_tipo_cambio"),
        sa.CheckConstraint("sfl_fec_devolucion_prevista >= sfl_fec_salida", name="ck_salida_flete_fechas"),
        sa.CheckConstraint("sfl_num between 1 and 4", name="ck_salida_flete_num"),
        sa.CheckConstraint(
            "((sfl_requiere_arreglo = false and sfl_monto_arreglo = 0 and sfl_descripcion_arreglo is null) "
            "or (sfl_requiere_arreglo = true and sfl_monto_arreglo >= 0 and sfl_descripcion_arreglo is not null))",
            name="ck_sfl_arreglo",
        ),
        sa.CheckConstraint("sfl_fec_devolucion_real is null or sfl_fec_devolucion_real >= sfl_fec_salida", name="ck_salida_flete_fecha_real"),
        sa.CheckConstraint("sfl_descuento is null or (sfl_descuento >= 0 and sfl_descuento <= sfl_precio)", name="ck_sfl_descuento"),
        sa.CheckConstraint(
            "(sfl_descuento is null and sfl_motivo_desc is null) or (sfl_descuento is not null and sfl_motivo_desc is not null)",
            name="ck_sfl_desc_motivo",
        ),
        sa.UniqueConstraint("fle_id", "sfl_num", name="uq_salida_flete_num"),
    )
    op.create_index("ix_salida_flete_fle_id_sfl_num", "salida_flete", ["fle_id", "sfl_num"], unique=False)
    op.create_index("ix_salida_flete_estado_fechas", "salida_flete", ["sfl_estado_salida", "sfl_fec_salida", "sfl_fec_devolucion_prevista"], unique=False)

    op.create_table(
        "tipo_comprobante",
        sa.Column("tco_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("tco_nom", sa.String(length=50), nullable=False),
        sa.Column("tco_des", sa.String(length=100), nullable=True),
        sa.Column("tco_es_fiscal", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tco_hab", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("tco_fec_reg", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("tco_nom", name="uq_tipo_comprobante_nom"),
    )

    op.create_table(
        "comprobante_interno",
        sa.Column("coi_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("tco_id", sa.BigInteger(), nullable=False),
        sa.Column("cli_id", sa.BigInteger(), nullable=True),
        sa.Column("usu_id", sa.Integer(), nullable=False),
        sa.Column("veb_id", sa.BigInteger(), nullable=True),
        sa.Column("ppd_id", sa.BigInteger(), nullable=True),
        sa.Column("sfl_id", sa.BigInteger(), nullable=True),
        sa.Column("mon_id", sa.BigInteger(), nullable=True),
        sa.Column("coi_cod", sa.String(length=30), nullable=False),
        sa.Column("coi_fec", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("coi_nom_cliente", sa.String(length=150), nullable=True),
        sa.Column("coi_ci_nit_cliente", sa.String(length=30), nullable=True),
        sa.Column("coi_cel_cliente", sa.String(length=30), nullable=True),
        sa.Column("coi_subtotal", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("coi_descuento", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("coi_total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("coi_total_moneda_orig", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("coi_saldo_posterior", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("coi_garantia", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("coi_tipo_cambio_usado", sa.Numeric(12, 4), nullable=False, server_default="1"),
        sa.Column("coi_metodo_pago", metodo_pago_enum, nullable=True),
        sa.Column("coi_estado", estado_comprobante_enum, nullable=False, server_default="emitido"),
        sa.Column("coi_fec_camb_est", sa.DateTime(timezone=True), nullable=True),
        sa.Column("coi_motivo_camb_est", sa.Text(), nullable=True),
        sa.Column("coi_hab", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["tco_id"], ["tipo_comprobante.tco_id"], name="fk_comprobante_tipo", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cli_id"], ["cliente.cli_id"], name="fk_comprobante_cliente", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["usu_id"], ["usuarios.id"], name="fk_comprobante_usuario", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["mon_id"], ["moneda.mon_id"], name="fk_comprobante_moneda", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["veb_id"], ["venta_boutique.veb_id"], name="fk_comprobante_venta", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sfl_id"], ["salida_flete.sfl_id"], name="fk_comprobante_salida_flete", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.UniqueConstraint("coi_cod", name="uq_comprobante_cod"),
        sa.CheckConstraint(
            "((coi_estado = 'emitido' and coi_fec_camb_est is null and coi_motivo_camb_est is null) "
            "or (coi_estado = 'anulado' and coi_fec_camb_est is not null and coi_motivo_camb_est is not null))",
            name="ck_coi_cambio_estado",
        ),
        sa.CheckConstraint("coi_descuento <= coi_subtotal", name="ck_comprobante_descuento"),
        sa.CheckConstraint(
            "((case when veb_id is not null then 1 else 0 end + case when ppd_id is not null then 1 else 0 end + case when sfl_id is not null then 1 else 0 end) = 1)",
            name="ck_comprobante_un_origen",
        ),
        sa.CheckConstraint("coi_total = round(coi_subtotal - coi_descuento, 2)", name="ck_comprobante_totales"),
        sa.CheckConstraint(
            "coi_subtotal >= 0 and coi_descuento >= 0 and coi_total >= 0 and coi_total_moneda_orig >= 0 and "
            "coi_saldo_posterior >= 0 and coi_garantia >= 0 and coi_tipo_cambio_usado > 0",
            name="ck_comprobante_montos",
        ),
    )
    op.create_index("ix_comprobante_estado_fec", "comprobante_interno", ["coi_estado", "coi_fec"], unique=False)
    op.create_index("ix_comprobante_sfl_id", "comprobante_interno", ["sfl_id"], unique=False)

    op.create_table(
        "detalle_comprobante",
        sa.Column("dco_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("coi_id", sa.BigInteger(), nullable=False),
        sa.Column("dco_concepto", sa.String(length=150), nullable=False),
        sa.Column("dco_cantidad", sa.Numeric(10, 2), nullable=False, server_default="1"),
        sa.Column("dco_precio_unidad", sa.Numeric(10, 2), nullable=False),
        sa.Column("dco_descuento", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("dco_subtotal", sa.Numeric(10, 2), nullable=False),
        sa.Column("dco_obs", sa.String(length=150), nullable=True),
        sa.ForeignKeyConstraint(["coi_id"], ["comprobante_interno.coi_id"], name="fk_detalle_comprobante", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.CheckConstraint("dco_descuento <= (dco_cantidad * dco_precio_unidad)", name="ck_detalle_comprobante_descuento"),
        sa.CheckConstraint("dco_subtotal = round(dco_cantidad * dco_precio_unidad - dco_descuento, 2)", name="ck_detalle_comprobante_subtotal"),
        sa.CheckConstraint(
            "dco_cantidad > 0 and dco_precio_unidad >= 0 and dco_descuento >= 0 and dco_subtotal >= 0",
            name="ck_detalle_comprobante_montos",
        ),
    )
    op.create_index("ix_detalle_comprobante_coi_id", "detalle_comprobante", ["coi_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_detalle_comprobante_coi_id", table_name="detalle_comprobante")
    op.drop_table("detalle_comprobante")
    op.drop_index("ix_comprobante_sfl_id", table_name="comprobante_interno")
    op.drop_index("ix_comprobante_estado_fec", table_name="comprobante_interno")
    op.drop_table("comprobante_interno")
    op.drop_table("tipo_comprobante")
    op.drop_index("ix_salida_flete_estado_fechas", table_name="salida_flete")
    op.drop_index("ix_salida_flete_fle_id_sfl_num", table_name="salida_flete")
    op.drop_table("salida_flete")
    op.drop_index("ix_flete_vestido_estado_hab", table_name="flete_vestido")
    op.drop_index("ix_flete_vestido_itb_id", table_name="flete_vestido")
    op.drop_table("flete_vestido")

    bind = op.get_bind()
    estado_comprobante_enum.drop(bind, checkfirst=True)
    estado_flete_devolucion_enum.drop(bind, checkfirst=True)
    estado_flete_entrega_enum.drop(bind, checkfirst=True)
    estado_salida_flete_enum.drop(bind, checkfirst=True)
    motivo_desc_flete_enum.drop(bind, checkfirst=True)
    estado_flete_enum.drop(bind, checkfirst=True)
