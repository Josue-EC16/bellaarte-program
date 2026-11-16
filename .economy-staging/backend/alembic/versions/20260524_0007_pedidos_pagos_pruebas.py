"""pedidos pagos y pruebas

Revision ID: 20260524_0007
Revises: 20260515_0006
Create Date: 2026-05-24 10:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260524_0007"
down_revision = "20260515_0006"
branch_labels = None
depends_on = None


tipo_pedido_enum = postgresql.ENUM("vestido", "velo", "cola", "manga", "bouquet", "otro", name="tipo_pedido", create_type=False)
motivo_descuento_pedido_enum = postgresql.ENUM(
    "rebaja",
    "promocion",
    "bonificacion",
    "administrativo",
    name="motivo_descuento_pedido",
    create_type=False,
)
estado_pedido_general_enum = postgresql.ENUM("activo", "inactivo", "entregado", "cancelado", name="estado_pedido_general", create_type=False)
estado_pago_pedido_enum = postgresql.ENUM("registrado", "anulado", name="estado_pago_pedido", create_type=False)
prueba_estado_pedido_enum = postgresql.ENUM(
    "listo",
    "costurero_taller",
    "decoracion",
    "costurero_externo",
    "otro",
    name="prueba_estado_pedido",
    create_type=False,
)
tipo_vestido_enum = postgresql.ENUM(
    "vestido_de_novia",
    "vestido_de_civil",
    "vestido_de_15",
    "vestido_de_fiesta",
    "vestido_de_nina",
    "damas",
    "otro",
    name="tipo_vestido",
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
    tipo_pedido_enum.create(bind, checkfirst=True)
    motivo_descuento_pedido_enum.create(bind, checkfirst=True)
    estado_pedido_general_enum.create(bind, checkfirst=True)
    estado_pago_pedido_enum.create(bind, checkfirst=True)
    prueba_estado_pedido_enum.create(bind, checkfirst=True)
    tipo_vestido_enum.create(bind, checkfirst=True)
    metodo_pago_enum.create(bind, checkfirst=True)

    op.create_table(
        "pedido",
        sa.Column("ped_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("cli_id", sa.BigInteger(), nullable=False),
        sa.Column("ped_cod", sa.String(length=40), nullable=False),
        sa.Column("ped_tipo", tipo_pedido_enum, nullable=False),
        sa.Column("ped_fec_reg_contrato", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("ped_usu_encargado", sa.Integer(), nullable=False),
        sa.Column("ped_fec_de_entrega", sa.Date(), nullable=False),
        sa.Column("ped_fec_entrega_final", sa.Date(), nullable=True),
        sa.Column("ped_viaje", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ped_pais_destino", sa.String(length=50), nullable=True),
        sa.Column("ped_ciudad_destino", sa.String(length=50), nullable=True),
        sa.Column("ped_precio", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("ped_descuento", sa.Numeric(12, 2), nullable=True),
        sa.Column("ped_motivo_descuento", motivo_descuento_pedido_enum, nullable=True),
        sa.Column("ped_pre_tot", sa.Numeric(12, 2), sa.Computed("round(ped_precio - coalesce(ped_descuento, 0), 2)", persisted=True), nullable=False),
        sa.Column("ped_total_pagado", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("ped_saldo", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("ped_obs", sa.Text(), nullable=True),
        sa.Column("ped_estado_general", estado_pedido_general_enum, nullable=False, server_default="activo"),
        sa.Column("ped_fec_camb_est", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ped_motivo_camb_est", sa.Text(), nullable=True),
        sa.Column("ped_hab", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["cli_id"], ["cliente.cli_id"], name="fk_ped_cli", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ped_usu_encargado"], ["usuarios.id"], name="fk_ped_usu", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.UniqueConstraint("ped_cod", name="uq_pedido_cod"),
        sa.CheckConstraint(
            "((ped_estado_general = 'activo' and ped_fec_camb_est is null and ped_motivo_camb_est is null) "
            "or (ped_estado_general = 'entregado') "
            "or (ped_estado_general in ('cancelado', 'inactivo') and ped_fec_camb_est is not null and ped_motivo_camb_est is not null))",
            name="ck_ped_cambio_estado",
        ),
        sa.CheckConstraint("ped_precio >= 0", name="ck_ped_precio"),
        sa.CheckConstraint("ped_total_pagado >= 0", name="ck_ped_total_pagado"),
        sa.CheckConstraint("ped_saldo >= 0", name="ck_ped_saldo"),
        sa.CheckConstraint("ped_descuento is null or (ped_descuento >= 0 and ped_descuento <= ped_precio)", name="ck_ped_descuento"),
        sa.CheckConstraint(
            "(ped_descuento is null and ped_motivo_descuento is null) or (ped_descuento is not null and ped_motivo_descuento is not null)",
            name="ck_ped_motivo_descuento",
        ),
        sa.CheckConstraint("(ped_viaje = false) or (ped_pais_destino is not null or ped_ciudad_destino is not null)", name="ck_ped_destino_viaje"),
    )
    op.create_index("ix_pedido_cliente_estado", "pedido", ["cli_id", "ped_estado_general", "ped_hab"], unique=False)
    op.create_index("ix_pedido_entrega", "pedido", ["ped_fec_de_entrega"], unique=False)

    op.create_table(
        "pedido_vestido",
        sa.Column("pdv_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("ped_id", sa.BigInteger(), nullable=False),
        sa.Column("pdv_tipo_vestido", tipo_vestido_enum, nullable=False),
        sa.Column("pdv_color_prin", sa.String(length=50), nullable=False),
        sa.Column("pdv_color_secu", sa.String(length=50), nullable=True),
        sa.Column("pdv_descr_material", sa.Text(), nullable=False),
        sa.Column("pdv_descr_diseno", sa.Text(), nullable=False),
        sa.Column("pdv_descripcion_2", sa.Text(), nullable=True),
        sa.Column("pdv_ane_esp", sa.Numeric(6, 2), nullable=True),
        sa.Column("pdv_tal_esp", sa.Numeric(6, 2), nullable=True),
        sa.Column("pdv_tal_del", sa.Numeric(6, 2), nullable=True),
        sa.Column("pdv_con_cin", sa.Numeric(6, 2), nullable=True),
        sa.Column("pdv_con_cad", sa.Numeric(6, 2), nullable=True),
        sa.Column("pdv_lar_fal", sa.Numeric(6, 2), nullable=True),
        sa.Column("pdv_sisa", sa.Numeric(6, 2), nullable=True),
        sa.Column("pdv_anb_bus", sa.Numeric(6, 2), nullable=True),
        sa.Column("pdv_sep_bus", sa.Numeric(6, 2), nullable=True),
        sa.Column("pdv_tal_bus", sa.Numeric(6, 2), nullable=True),
        sa.Column("pdv_tal_cos", sa.Numeric(6, 2), nullable=True),
        sa.Column("pdv_obs", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["ped_id"], ["pedido.ped_id"], name="fk_pdv_ped", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.UniqueConstraint("ped_id", name="uq_pdv_ped_id"),
        *[
            sa.CheckConstraint(f"{column} is null or {column} >= 0", name=f"ck_{column}")
            for column in ("pdv_ane_esp", "pdv_tal_esp", "pdv_tal_del", "pdv_con_cin", "pdv_con_cad", "pdv_lar_fal", "pdv_sisa", "pdv_anb_bus", "pdv_sep_bus", "pdv_tal_bus", "pdv_tal_cos")
        ],
    )

    op.create_table(
        "pedido_velo",
        sa.Column("pdve_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("ped_id", sa.BigInteger(), nullable=False),
        sa.Column("pdve_tipo_velo", sa.String(length=100), nullable=True),
        sa.Column("pdve_color_prin", sa.String(length=50), nullable=False),
        sa.Column("pdve_color_secu", sa.String(length=50), nullable=True),
        sa.Column("pdve_largo", sa.Numeric(6, 2), nullable=False),
        sa.Column("pdve_ancho", sa.Numeric(6, 2), nullable=True),
        sa.Column("pdve_capas", sa.SmallInteger(), nullable=True),
        sa.Column("pdve_borde", sa.String(length=100), nullable=True),
        sa.Column("pdve_decoracion", sa.Text(), nullable=True),
        sa.Column("pdve_material", sa.String(length=100), nullable=True),
        sa.Column("pdve_obs", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["ped_id"], ["pedido.ped_id"], name="fk_pdve_ped", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.UniqueConstraint("ped_id", name="uq_pdve_ped_id"),
        sa.CheckConstraint("pdve_largo > 0", name="ck_pdve_largo"),
        sa.CheckConstraint("pdve_ancho is null or pdve_ancho >= 0", name="ck_pdve_ancho"),
        sa.CheckConstraint("pdve_capas is null or pdve_capas > 0", name="ck_pdve_capas"),
    )

    op.create_table(
        "pedido_cola",
        sa.Column("pdco_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("ped_id", sa.BigInteger(), nullable=False),
        sa.Column("pdco_tipo_cola", sa.String(length=100), nullable=True),
        sa.Column("pdco_color_prin", sa.String(length=50), nullable=False),
        sa.Column("pdco_color_secun", sa.String(length=50), nullable=True),
        sa.Column("pdco_largo", sa.Numeric(6, 2), nullable=False),
        sa.Column("pdco_ancho", sa.Numeric(6, 2), nullable=True),
        sa.Column("pdco_material", sa.String(length=100), nullable=True),
        sa.Column("pdco_decoracion", sa.Text(), nullable=True),
        sa.Column("pdco_obs", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["ped_id"], ["pedido.ped_id"], name="fk_pdco_ped", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.UniqueConstraint("ped_id", name="uq_pdco_ped_id"),
        sa.CheckConstraint("pdco_largo > 0", name="ck_pdco_largo"),
        sa.CheckConstraint("pdco_ancho is null or pdco_ancho >= 0", name="ck_pdco_ancho"),
    )

    op.create_table(
        "pedido_manga",
        sa.Column("pdma_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("ped_id", sa.BigInteger(), nullable=False),
        sa.Column("pdma_tipo_manga", sa.String(length=100), nullable=True),
        sa.Column("pdma_color_prin", sa.String(length=50), nullable=False),
        sa.Column("pdma_color_secun", sa.String(length=50), nullable=True),
        sa.Column("pdma_lar_man", sa.Numeric(6, 2), nullable=False),
        sa.Column("pdma_bra", sa.Numeric(6, 2), nullable=False),
        sa.Column("pdma_pun", sa.Numeric(6, 2), nullable=False),
        sa.Column("pdma_material", sa.String(length=100), nullable=True),
        sa.Column("pdma_decoracion", sa.Text(), nullable=True),
        sa.Column("pdma_obs", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["ped_id"], ["pedido.ped_id"], name="fk_pdma_ped", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.UniqueConstraint("ped_id", name="uq_pdma_ped_id"),
        sa.CheckConstraint("pdma_lar_man > 0", name="ck_pdma_lar_man"),
        sa.CheckConstraint("pdma_bra >= 0", name="ck_pdma_bra"),
        sa.CheckConstraint("pdma_pun >= 0", name="ck_pdma_pun"),
    )

    op.create_table(
        "pedido_bouquet",
        sa.Column("pdb_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("ped_id", sa.BigInteger(), nullable=False),
        sa.Column("pdb_tipo_bouquet", sa.String(length=100), nullable=False),
        sa.Column("pdb_color_prin", sa.String(length=50), nullable=False),
        sa.Column("pdb_color_secun", sa.String(length=50), nullable=True),
        sa.Column("pdb_largo", sa.Numeric(6, 2), nullable=False),
        sa.Column("pdb_ancho", sa.Numeric(6, 2), nullable=True),
        sa.Column("pdb_tipo_flor", sa.String(length=100), nullable=True),
        sa.Column("pdb_decoracion", sa.Text(), nullable=True),
        sa.Column("pdb_obs", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["ped_id"], ["pedido.ped_id"], name="fk_pdb_ped", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.UniqueConstraint("ped_id", name="uq_pdb_ped_id"),
        sa.CheckConstraint("pdb_largo >= 0", name="ck_pdb_largo"),
        sa.CheckConstraint("pdb_ancho is null or pdb_ancho >= 0", name="ck_pdb_ancho"),
    )

    op.create_table(
        "pedido_otro",
        sa.Column("pdot_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("ped_id", sa.BigInteger(), nullable=False),
        sa.Column("pdot_nom", sa.String(length=80), nullable=False),
        sa.Column("pdot_color_prin", sa.String(length=50), nullable=False),
        sa.Column("pdot_color_secun", sa.String(length=50), nullable=True),
        sa.Column("pdot_largo", sa.Numeric(6, 2), nullable=True),
        sa.Column("pdot_ancho", sa.Numeric(6, 2), nullable=True),
        sa.Column("pdot_descripcion", sa.Text(), nullable=True),
        sa.Column("pdot_obs", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["ped_id"], ["pedido.ped_id"], name="fk_pdot_ped", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.UniqueConstraint("ped_id", name="uq_pdot_ped_id"),
        sa.CheckConstraint("pdot_largo is null or pdot_largo >= 0", name="ck_pdot_largo"),
        sa.CheckConstraint("pdot_ancho is null or pdot_ancho >= 0", name="ck_pdot_ancho"),
    )

    op.create_table(
        "prueba_pedido",
        sa.Column("prp_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("ped_id", sa.BigInteger(), nullable=False),
        sa.Column("prp_num", sa.SmallInteger(), nullable=False),
        sa.Column("prp_fec", sa.Date(), nullable=False),
        sa.Column("prp_hor", sa.Time(), nullable=True),
        sa.Column("prp_estado", prueba_estado_pedido_enum, nullable=False),
        sa.Column("prp_obs", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["ped_id"], ["pedido.ped_id"], name="fk_prp_ped", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.UniqueConstraint("ped_id", "prp_num", name="uq_prueba_pedido_num"),
        sa.CheckConstraint("prp_num > 0", name="ck_prp_num"),
    )
    op.create_index("ix_prp_fec_estado", "prueba_pedido", ["prp_fec", "prp_estado"], unique=False)

    op.create_table(
        "pago_pedido",
        sa.Column("ppd_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("ped_id", sa.BigInteger(), nullable=False),
        sa.Column("usu_id", sa.Integer(), nullable=False),
        sa.Column("mon_id", sa.BigInteger(), nullable=False),
        sa.Column("ppd_fec", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("ppd_monto", sa.Numeric(12, 2), nullable=False),
        sa.Column("ppd_tipo_cambio_usado", sa.Numeric(12, 4), nullable=False, server_default="1"),
        sa.Column("ppd_monto_bob", sa.Numeric(12, 2), sa.Computed("round(ppd_monto * ppd_tipo_cambio_usado, 2)", persisted=True), nullable=False),
        sa.Column("ppd_metodo", metodo_pago_enum, nullable=False),
        sa.Column("ppd_obs1", sa.Text(), nullable=True),
        sa.Column("ppd_estado", estado_pago_pedido_enum, nullable=False, server_default="registrado"),
        sa.Column("ppd_fec_camb_est", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ppd_motivo_camb_est", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["ped_id"], ["pedido.ped_id"], name="fk_ppd_ped", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["usu_id"], ["usuarios.id"], name="fk_ppd_usu", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["mon_id"], ["moneda.mon_id"], name="fk_ppd_moneda", onupdate="CASCADE", ondelete="RESTRICT"),
        sa.CheckConstraint(
            "((ppd_estado = 'registrado' and ppd_fec_camb_est is null and ppd_motivo_camb_est is null) "
            "or (ppd_estado = 'anulado' and ppd_fec_camb_est is not null and ppd_motivo_camb_est is not null))",
            name="ck_ppd_cambio_estado",
        ),
        sa.CheckConstraint("ppd_monto > 0", name="ck_ppd_monto"),
        sa.CheckConstraint("ppd_tipo_cambio_usado > 0", name="ck_ppd_tipo_cambio"),
    )
    op.create_index("ix_ppd_pedido_estado_fec", "pago_pedido", ["ped_id", "ppd_estado", "ppd_fec"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ppd_pedido_estado_fec", table_name="pago_pedido")
    op.drop_table("pago_pedido")
    op.drop_index("ix_prp_fec_estado", table_name="prueba_pedido")
    op.drop_table("prueba_pedido")
    op.drop_table("pedido_otro")
    op.drop_table("pedido_bouquet")
    op.drop_table("pedido_manga")
    op.drop_table("pedido_cola")
    op.drop_table("pedido_velo")
    op.drop_table("pedido_vestido")
    op.drop_index("ix_pedido_entrega", table_name="pedido")
    op.drop_index("ix_pedido_cliente_estado", table_name="pedido")
    op.drop_table("pedido")

    bind = op.get_bind()
    prueba_estado_pedido_enum.drop(bind, checkfirst=True)
    estado_pago_pedido_enum.drop(bind, checkfirst=True)
    estado_pedido_general_enum.drop(bind, checkfirst=True)
    motivo_descuento_pedido_enum.drop(bind, checkfirst=True)
    tipo_pedido_enum.drop(bind, checkfirst=True)
