"""economy module

Revision ID: 20260604_0010
Revises: 20260529_0009
Create Date: 2026-06-04 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260604_0010"
down_revision = "20260529_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tipo_egreso = sa.Enum(
        "almuerzo",
        "merienda",
        "alquiler",
        "alimentos_en_general",
        "costura",
        "decorado",
        "devolucion",
        "inventario_boutique",
        "inventario_taller",
        "mantenimiento",
        "marketing",
        "servicio_basico",
        "sueldo",
        "tecnologia",
        "otro",
        name="tipo_egreso",
    )
    estado_egreso = sa.Enum("registrado", "anulado", name="estado_egreso")
    estado_corte_caja = sa.Enum("abierto", "cerrado", "cerrado_observado", name="estado_corte_caja")
    tipo_egreso.create(op.get_bind(), checkfirst=True)
    estado_egreso.create(op.get_bind(), checkfirst=True)
    estado_corte_caja.create(op.get_bind(), checkfirst=True)

    tipo_egreso_column = postgresql.ENUM(
        "almuerzo",
        "merienda",
        "alquiler",
        "alimentos_en_general",
        "costura",
        "decorado",
        "devolucion",
        "inventario_boutique",
        "inventario_taller",
        "mantenimiento",
        "marketing",
        "servicio_basico",
        "sueldo",
        "tecnologia",
        "otro",
        name="tipo_egreso",
        create_type=False,
    )
    estado_egreso_column = postgresql.ENUM(
        "registrado",
        "anulado",
        name="estado_egreso",
        create_type=False,
    )
    estado_corte_caja_column = postgresql.ENUM(
        "abierto",
        "cerrado",
        "cerrado_observado",
        name="estado_corte_caja",
        create_type=False,
    )

    op.create_table(
        "corte_caja",
        sa.Column("cco_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("usu_id_cajero", sa.BigInteger(), sa.ForeignKey("usuarios.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False),
        sa.Column("usu_id_admin", sa.BigInteger(), sa.ForeignKey("usuarios.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False),
        sa.Column("cco_fec_apertura", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("cco_fec_cierre", sa.DateTime(timezone=True)),
        sa.Column("cco_fondo_asignado", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("cco_obs_apertura", sa.Text()),
        sa.Column("cco_obs_cierre", sa.Text()),
        sa.Column("cco_estado", estado_corte_caja_column, nullable=False, server_default="abierto"),
        sa.CheckConstraint("cco_fondo_asignado >= 0", name="ck_cco_fondo"),
        sa.CheckConstraint(
            "((cco_estado = 'abierto' and cco_fec_cierre is null) or "
            "(cco_estado in ('cerrado', 'cerrado_observado') and cco_fec_cierre is not null))",
            name="ck_cco_cierre",
        ),
    )
    op.create_index("ix_cco_cajero_estado", "corte_caja", ["usu_id_cajero", "cco_estado"], unique=False)
    op.create_index("ix_cco_apertura_cierre", "corte_caja", ["cco_fec_apertura", "cco_fec_cierre"], unique=False)
    op.execute(
        sa.text(
            "create unique index if not exists uq_corte_abierto_cajero on corte_caja (usu_id_cajero) where cco_estado = 'abierto'"
        )
    )

    op.create_table(
        "egreso",
        sa.Column("egr_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("usu_id", sa.BigInteger(), sa.ForeignKey("usuarios.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True),
        sa.Column("cco_id", sa.BigInteger(), sa.ForeignKey("corte_caja.cco_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True),
        sa.Column("egr_fec", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("egr_tipo", tipo_egreso_column, nullable=False),
        sa.Column("egr_concepto", sa.String(length=150), nullable=False),
        sa.Column("egr_cantidad", sa.Numeric(12, 2), nullable=False),
        sa.Column("egr_precio_unidad", sa.Numeric(12, 2), nullable=False),
        sa.Column("egr_beneficiario", sa.String(length=120)),
        sa.Column(
            "egr_monto",
            sa.Numeric(12, 2),
            sa.Computed("round(egr_cantidad * egr_precio_unidad, 2)", persisted=True),
            nullable=False,
        ),
        sa.Column("egr_obs1", sa.Text()),
        sa.Column("egr_obs2", sa.Text()),
        sa.Column("egr_estado", estado_egreso_column, nullable=False, server_default="registrado"),
        sa.Column("egr_fec_camb_est", sa.DateTime(timezone=True)),
        sa.Column("egr_motivo_camb_est", sa.Text()),
        sa.Column("egr_tabla_ref", sa.String(length=50)),
        sa.Column("egr_id_ref", sa.BigInteger()),
        sa.CheckConstraint(
            "((egr_estado = 'registrado' and egr_fec_camb_est is null and egr_motivo_camb_est is null) or "
            "(egr_estado = 'anulado' and egr_fec_camb_est is not null and egr_motivo_camb_est is not null))",
            name="ck_egr_cambio_estado",
        ),
        sa.CheckConstraint("egr_cantidad > 0", name="ck_egr_cantidad"),
        sa.CheckConstraint("egr_precio_unidad > 0", name="ck_egr_precio_unidad"),
        sa.CheckConstraint(
            "((egr_tipo <> 'devolucion' and egr_tabla_ref is null and egr_id_ref is null) or "
            "(egr_tipo = 'devolucion' and egr_tabla_ref in ('venta_boutique', 'pago_pedido', 'salida_flete') and egr_id_ref is not null))",
            name="ck_egr_ref_devolucion",
        ),
    )
    op.create_index("ix_egr_fec_estado", "egreso", ["egr_fec", "egr_estado"], unique=False)
    op.create_index("ix_egr_cco_id", "egreso", ["cco_id"], unique=False)
    op.create_index("ix_egr_usu_fec", "egreso", ["usu_id", "egr_fec"], unique=False)
    op.create_index("ix_egr_tipo_fec", "egreso", ["egr_tipo", "egr_fec"], unique=False)
    op.create_index("ix_egr_ref", "egreso", ["egr_tabla_ref", "egr_id_ref"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_egr_ref", table_name="egreso")
    op.drop_index("ix_egr_tipo_fec", table_name="egreso")
    op.drop_index("ix_egr_usu_fec", table_name="egreso")
    op.drop_index("ix_egr_cco_id", table_name="egreso")
    op.drop_index("ix_egr_fec_estado", table_name="egreso")
    op.drop_table("egreso")

    op.execute("drop index if exists uq_corte_abierto_cajero")
    op.drop_index("ix_cco_apertura_cierre", table_name="corte_caja")
    op.drop_index("ix_cco_cajero_estado", table_name="corte_caja")
    op.drop_table("corte_caja")

    sa.Enum(name="estado_corte_caja").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="estado_egreso").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="tipo_egreso").drop(op.get_bind(), checkfirst=True)
