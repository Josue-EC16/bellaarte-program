"""Add provenance and ten-column attempt history without rewriting old rates.

The owner approved nullable automatic authors and exclusion of all future
exchange-rate operations from general audit. Existing audit records are retained.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261104_0023"
down_revision = "20261103_0022"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM tipo_cambio_moneda WHERE tcm_activo GROUP BY mon_id HAVING count(*)>1)")):
        raise RuntimeError("Duplicate active rates require an explicit reviewed data correction.")
    # DEFAULT classifies old rows without UPDATE or inventing source timestamps.
    op.add_column("tipo_cambio_moneda", sa.Column("tcm_origen", sa.String(12), server_default="MANUAL", nullable=False))
    op.add_column("tipo_cambio_moneda", sa.Column("tcm_fuente", sa.String(64), nullable=True))
    op.add_column("tipo_cambio_moneda", sa.Column("tcm_fec_consulta", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("tipo_cambio_moneda", "usu_id", existing_type=sa.Integer(), nullable=True)
    # PostgreSQL orders numeric NaN above ordinary numbers: the old >0 CHECK
    # alone does not exclude it. This complements, rather than duplicates, it.
    op.create_check_constraint("ck_tcm_valor_finito", "tipo_cambio_moneda", "tcm_valor_bob <> 'NaN'::numeric")
    op.create_check_constraint("ck_tcm_origen", "tipo_cambio_moneda", "tcm_origen IN ('MANUAL','AUTOMATICO')")
    op.create_check_constraint("ck_tcm_autoria", "tipo_cambio_moneda", "(tcm_origen='MANUAL' AND usu_id IS NOT NULL) OR (tcm_origen='AUTOMATICO' AND usu_id IS NULL)")
    op.create_check_constraint("ck_tcm_fuente_automatica", "tipo_cambio_moneda", "tcm_origen<>'AUTOMATICO' OR (tcm_fuente IS NOT NULL AND length(btrim(tcm_fuente))>0)")
    op.create_unique_constraint("uq_tcm_moneda_id", "tipo_cambio_moneda", ["mon_id", "tcm_id"])
    op.create_index("ix_tcm_historial_moneda", "tipo_cambio_moneda", ["mon_id", sa.text("tcm_fec_reg DESC")])
    op.create_table("tipo_cambio_registros",
        sa.Column("tcs_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("mon_id", sa.BigInteger(), nullable=False),
        sa.Column("tcm_id", sa.BigInteger(), nullable=True),
        sa.Column("tcs_fecha_objetivo", sa.Date(), nullable=False),
        sa.Column("tcs_num_intento", sa.SmallInteger(), nullable=False),
        sa.Column("tcs_fec_intento", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tcs_estado", sa.String(32), nullable=False),
        sa.Column("tcs_codigo_http", sa.SmallInteger(), nullable=True),
        sa.Column("tcs_proximo_intento", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tcs_proveedor", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(["mon_id"], ["moneda.mon_id"], name="fk_tcs_moneda", ondelete="RESTRICT", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["mon_id", "tcm_id"], ["tipo_cambio_moneda.mon_id", "tipo_cambio_moneda.tcm_id"], name="fk_tcs_cotizacion_moneda", ondelete="RESTRICT", onupdate="CASCADE"),
        sa.CheckConstraint("tcs_estado IN ('INICIADO','EXITOSO','ERROR_CONEXION','ERROR_API','ERROR_DATOS','ERROR_VIGENCIA','ERROR_EJECUCION','CARGA_HISTORICA')", name="ck_tcs_estado"),
        sa.CheckConstraint("(tcs_estado='CARGA_HISTORICA' AND tcs_num_intento=0) OR (tcs_estado<>'CARGA_HISTORICA' AND tcs_num_intento BETWEEN 1 AND 10)", name="ck_tcs_intento"),
        sa.CheckConstraint("(tcs_estado IN ('EXITOSO','CARGA_HISTORICA')) = (tcm_id IS NOT NULL)", name="ck_tcs_cotizacion_resultado"),
        sa.CheckConstraint("tcs_codigo_http IS NULL OR tcs_codigo_http BETWEEN 100 AND 599", name="ck_tcs_http"),
        sa.CheckConstraint("tcs_estado<>'EXITOSO' OR (tcs_codigo_http IS NOT NULL AND tcs_codigo_http BETWEEN 200 AND 299)", name="ck_tcs_http_exitoso"),
        sa.CheckConstraint("tcs_estado NOT IN ('INICIADO','CARGA_HISTORICA','ERROR_CONEXION') OR tcs_codigo_http IS NULL", name="ck_tcs_http_estado"),
        sa.CheckConstraint("tcs_proximo_intento IS NULL OR (tcs_estado LIKE 'ERROR_%' AND tcs_proximo_intento>tcs_fec_intento)", name="ck_tcs_proximo_intento"),
        sa.CheckConstraint("length(btrim(tcs_proveedor))>0", name="ck_tcs_proveedor"))
    op.create_index("ix_tcs_historial_moneda", "tipo_cambio_registros", ["mon_id", sa.text("tcs_fecha_objetivo DESC"), sa.text("tcs_fec_intento DESC")])
    op.create_index("ix_tcs_proximos", "tipo_cambio_registros", ["tcs_proximo_intento", "mon_id"], postgresql_where=sa.text("tcs_proximo_intento IS NOT NULL"))
    op.create_index("uq_tcs_ordinal_dia", "tipo_cambio_registros", ["mon_id", "tcs_proveedor", sa.text("((tcs_fec_intento AT TIME ZONE 'America/La_Paz')::date)"), "tcs_num_intento"], unique=True, postgresql_where=sa.text("tcs_num_intento>0"))
    op.create_index("uq_tcs_exitoso_fecha", "tipo_cambio_registros", ["mon_id", "tcs_proveedor", "tcs_fecha_objetivo"], unique=True, postgresql_where=sa.text("tcs_estado='EXITOSO'"))
    op.create_index("uq_tcs_historico_fecha", "tipo_cambio_registros", ["mon_id", "tcs_proveedor", "tcs_fecha_objetivo"], unique=True, postgresql_where=sa.text("tcs_estado='CARGA_HISTORICA'"))
    op.execute("DROP TRIGGER IF EXISTS trg_auditoria_tipo_cambio_moneda ON tipo_cambio_moneda")


def downgrade():
    connection = op.get_bind()
    if connection.scalar(sa.text("""SELECT EXISTS(SELECT 1 FROM tipo_cambio_registros)
        OR EXISTS(SELECT 1 FROM tipo_cambio_moneda WHERE usu_id IS NULL OR tcm_origen<>'MANUAL'
                  OR tcm_fuente IS NOT NULL OR tcm_fec_consulta IS NOT NULL)""")):
        raise RuntimeError("Downgrade would discard exchange-rate history/provenance; preserve it in an approved procedure first.")
    op.drop_table("tipo_cambio_registros")
    op.drop_index("ix_tcm_historial_moneda", table_name="tipo_cambio_moneda")
    op.drop_constraint("uq_tcm_moneda_id", "tipo_cambio_moneda", type_="unique")
    for name in ("ck_tcm_fuente_automatica", "ck_tcm_autoria", "ck_tcm_origen", "ck_tcm_valor_finito"):
        op.drop_constraint(name, "tipo_cambio_moneda", type_="check")
    op.alter_column("tipo_cambio_moneda", "usu_id", existing_type=sa.Integer(), nullable=False)
    for name in ("tcm_fec_consulta", "tcm_fuente", "tcm_origen"):
        op.drop_column("tipo_cambio_moneda", name)
    op.execute("CREATE TRIGGER trg_auditoria_tipo_cambio_moneda AFTER INSERT OR UPDATE OR DELETE ON tipo_cambio_moneda FOR EACH ROW EXECUTE FUNCTION fn_auditoria_trazabilidad()")
