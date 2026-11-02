"""phase 1 report indexes

Revision ID: 20260615_0012
Revises: 20260605_0011
Create Date: 2026-06-15 11:20:00.000000
"""

from alembic import op


revision = "20260615_0012"
down_revision = "20260605_0011"
branch_labels = None
depends_on = None


VENTA_BOUTIQUE_INDEXES = (
    ("idx_veb_estado_fec", "venta_boutique", ["veb_estado", "veb_fec"]),
    ("idx_veb_estado_cambio_fec", "venta_boutique", ["veb_estado", "veb_fec_camb_est"]),
    ("idx_veb_itb_fec", "venta_boutique", ["itb_id", "veb_fec"]),
    ("idx_veb_usu_fec", "venta_boutique", ["usu_id", "veb_fec"]),
    ("idx_veb_cli_fec", "venta_boutique", ["cli_id", "veb_fec"]),
    ("idx_veb_mon_fec", "venta_boutique", ["mon_id", "veb_fec"]),
    ("idx_veb_metodo_fec", "venta_boutique", ["veb_metodo_pago", "veb_fec"]),
)

PAGO_PEDIDO_INDEXES = (
    ("idx_ppd_fec", "pago_pedido", ["ppd_fec"]),
    ("idx_ppd_estado_fec", "pago_pedido", ["ppd_estado", "ppd_fec"]),
    ("idx_ppd_estado_cambio_fec", "pago_pedido", ["ppd_estado", "ppd_fec_camb_est"]),
    ("idx_ppd_ped_fec", "pago_pedido", ["ped_id", "ppd_fec"]),
    ("idx_ppd_usu_fec", "pago_pedido", ["usu_id", "ppd_fec"]),
    ("idx_ppd_mon_fec", "pago_pedido", ["mon_id", "ppd_fec"]),
    ("idx_ppd_metodo_fec", "pago_pedido", ["ppd_metodo", "ppd_fec"]),
)

SALIDA_FLETE_INDEXES = (
    ("idx_sfl_fec_reg", "salida_flete", ["sfl_fec_reg"]),
    ("idx_sfl_estado_fec_reg", "salida_flete", ["sfl_estado_salida", "sfl_fec_reg"]),
    ("idx_sfl_estado_cambio_fec", "salida_flete", ["sfl_estado_salida", "sfl_fec_camb_est"]),
    ("idx_sfl_fec_salida", "salida_flete", ["sfl_fec_salida"]),
    ("idx_sfl_fec_devol_prev", "salida_flete", ["sfl_fec_devolucion_prevista"]),
    ("idx_sfl_cli_fec_reg", "salida_flete", ["cli_id", "sfl_fec_reg"]),
    ("idx_sfl_fle_fec_reg", "salida_flete", ["fle_id", "sfl_fec_reg"]),
    ("idx_sfl_usu_fec_reg", "salida_flete", ["usu_id", "sfl_fec_reg"]),
    ("idx_sfl_mon_fec_reg", "salida_flete", ["mon_id", "sfl_fec_reg"]),
    ("idx_sfl_metodo_fec_reg", "salida_flete", ["sfl_metodo_pago", "sfl_fec_reg"]),
)

PEDIDO_INDEXES = (
    ("idx_ped_fec_reg", "pedido", ["ped_fec_reg_contrato"]),
    ("idx_ped_estado_fec_reg", "pedido", ["ped_estado_general", "ped_fec_reg_contrato"]),
    ("idx_ped_estado_entrega", "pedido", ["ped_estado_general", "ped_fec_de_entrega"]),
    ("idx_ped_estado_cambio_fec", "pedido", ["ped_estado_general", "ped_fec_camb_est"]),
    ("idx_ped_tipo_fec_reg", "pedido", ["ped_tipo", "ped_fec_reg_contrato"]),
    ("idx_ped_usu_estado", "pedido", ["ped_usu_encargado", "ped_estado_general"]),
    ("idx_ped_viaje_estado", "pedido", ["ped_viaje", "ped_estado_general"]),
)

PRUEBA_PEDIDO_INDEXES = (
    ("idx_prp_estado_fec", "prueba_pedido", ["prp_estado", "prp_fec"]),
    ("idx_prp_ped_fec", "prueba_pedido", ["ped_id", "prp_fec"]),
)

COMPROBANTE_INDEXES = (
    ("idx_coi_tco_fec", "comprobante_interno", ["tco_id", "coi_fec"]),
    ("idx_coi_cli_fec", "comprobante_interno", ["cli_id", "coi_fec"]),
    ("idx_coi_usu_fec", "comprobante_interno", ["usu_id", "coi_fec"]),
    ("idx_coi_mon_fec", "comprobante_interno", ["mon_id", "coi_fec"]),
    ("idx_coi_metodo_fec", "comprobante_interno", ["coi_metodo_pago", "coi_fec"]),
)

EGRESO_INDEXES = (
    ("idx_egr_estado_fec", "egreso", ["egr_estado", "egr_fec"]),
    ("idx_egr_cco_fec", "egreso", ["cco_id", "egr_fec"]),
)

CORTE_CAJA_INDEXES = (
    ("idx_cco_estado_apertura", "corte_caja", ["cco_estado", "cco_fec_apertura"]),
    ("idx_cco_cajero_apertura", "corte_caja", ["usu_id_cajero", "cco_fec_apertura"]),
    ("idx_cco_admin_apertura", "corte_caja", ["usu_id_admin", "cco_fec_apertura"]),
)

ALL_INDEXES = (
    VENTA_BOUTIQUE_INDEXES
    + PAGO_PEDIDO_INDEXES
    + SALIDA_FLETE_INDEXES
    + PEDIDO_INDEXES
    + PRUEBA_PEDIDO_INDEXES
    + COMPROBANTE_INDEXES
    + EGRESO_INDEXES
    + CORTE_CAJA_INDEXES
)


def upgrade() -> None:
    for index_name, table_name, columns in ALL_INDEXES:
        op.create_index(index_name, table_name, columns, unique=False)


def downgrade() -> None:
    for index_name, table_name, _columns in reversed(ALL_INDEXES):
        op.drop_index(index_name, table_name=table_name)
