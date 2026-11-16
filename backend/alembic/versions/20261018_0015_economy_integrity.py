"""Explicit economic cuts, immutable cash ledger, refund records and idempotency.

Revision ID: 20261018_0015
Revises: 20261018_0014

No reconstruction of historical methods, cuts, refunds or closures is attempted.
Existing cuts remain control_version=0; explicitly close any open legacy cut.
Deployment requires authorization and a maintenance window with writers stopped.
Downgrade refuses to discard controlled financial evidence.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261018_0015"
down_revision = "20261018_0014"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.add_column("corte_caja", sa.Column("control_version", sa.SmallInteger(), nullable=False, server_default="0"))
    op.add_column("corte_caja", sa.Column("cierre_snapshot", postgresql.JSONB(none_as_null=True), nullable=True))
    op.create_check_constraint("ck_cco_control_version", "corte_caja", "control_version in (0,1)")
    op.create_check_constraint("ck_cco_snapshot", "corte_caja", "control_version = 0 or cco_estado = 'abierto' or cierre_snapshot is not null")
    method = postgresql.ENUM(name="metodo_pago", create_type=False)
    op.add_column("egreso", sa.Column("metodo_pago", method, nullable=True))
    for table in ("venta_boutique", "pago_pedido", "salida_flete"):
        op.add_column(table, sa.Column("corte_id", sa.BigInteger(), nullable=True))
        op.create_foreign_key(f"fk_{table}_corte", table, "corte_caja", ["corte_id"], ["cco_id"], ondelete="RESTRICT")
        op.create_index(f"ix_{table}_corte_id", table, ["corte_id"])
    op.drop_constraint("ck_salida_flete_num", "salida_flete", type_="check")
    op.create_check_constraint("ck_salida_flete_num", "salida_flete", "sfl_num > 0")
    op.create_table(
        "movimiento_economico",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("corte_id", sa.BigInteger(), sa.ForeignKey("corte_caja.cco_id", ondelete="RESTRICT")),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("evento", sa.String(30), nullable=False),
        sa.Column("direccion", sa.SmallInteger(), nullable=False),
        sa.Column("monto_bob", sa.Numeric(12, 2), nullable=False),
        sa.Column("monto_original", sa.Numeric(12, 2), nullable=False),
        sa.Column("moneda_codigo", sa.String(10), nullable=False),
        sa.Column("metodo_pago", method, nullable=False),
        sa.Column("origen_tipo", sa.String(30)), sa.Column("origen_id", sa.BigInteger()),
        sa.Column("secuencia", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("egreso_id", sa.BigInteger(), sa.ForeignKey("egreso.egr_id", ondelete="RESTRICT")),
        sa.Column("salida_flete_id", sa.BigInteger(), sa.ForeignKey("salida_flete.sfl_id", ondelete="RESTRICT")),
        sa.Column("motivo", sa.Text()),
        sa.CheckConstraint("monto_bob > 0 and monto_original > 0", name="ck_mov_montos"),
        sa.CheckConstraint("direccion in (-1,0,1)", name="ck_mov_direccion"),
        sa.CheckConstraint("evento in ('fondo','ingreso','egreso','ajuste_egreso','garantia_recibida','garantia_devuelta','garantia_retenida')", name="ck_mov_evento"),
        sa.CheckConstraint("((evento in ('fondo','ingreso','ajuste_egreso','garantia_recibida') and direccion = 1) or (evento in ('egreso','garantia_devuelta') and direccion = -1) or (evento = 'garantia_retenida' and direccion = 0))", name="ck_mov_evento_direccion"),
        sa.CheckConstraint("(origen_tipo is null) = (origen_id is null)", name="ck_mov_origen"),
        sa.CheckConstraint("origen_tipo is null or origen_tipo in ('venta_boutique','pago_pedido','salida_flete','egreso','corte_caja')", name="ck_mov_origen_tipo"),
        sa.CheckConstraint("evento = 'ingreso' or moneda_codigo = 'BOB'", name="ck_mov_moneda"),
        sa.CheckConstraint("moneda_codigo <> 'BOB' or monto_original = monto_bob", name="ck_mov_bob_equivalencia"),
        sa.CheckConstraint("secuencia > 0", name="ck_mov_secuencia"),
        sa.UniqueConstraint("evento", "origen_tipo", "origen_id", "secuencia", name="uq_mov_evento_origen"),
    )
    op.create_index("ix_mov_corte_fecha", "movimiento_economico", ["corte_id", "fecha"])
    op.create_index("ix_mov_origen", "movimiento_economico", ["origen_tipo", "origen_id"])
    op.create_index("ix_mov_fecha_evento", "movimiento_economico", ["fecha", "evento"])
    op.create_index("uq_mov_evento_unico", "movimiento_economico", ["evento", "origen_tipo", "origen_id"], unique=True,
                    postgresql_where=sa.text("evento in ('fondo','ingreso','egreso','ajuste_egreso','garantia_recibida')"))
    op.create_table(
        "constancia_devolucion",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("egreso_id", sa.BigInteger(), sa.ForeignKey("egreso.egr_id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
    )
    op.create_table(
        "solicitud_economica",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("operacion", sa.String(80), nullable=False), sa.Column("clave", sa.String(120), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False), sa.Column("resultado", postgresql.JSONB(none_as_null=True)),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("actor_id", "operacion", "clave", name="uq_solicitud_actor_operacion_clave"),
        sa.CheckConstraint("length(payload_hash) = 64", name="ck_solicitud_hash"),
    )
    op.execute("""
        CREATE FUNCTION economic_immutable_record() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Economic evidence is append-only; use a linked current-dated adjustment' USING ERRCODE='23514';
        END $$;
        CREATE TRIGGER trg_movimiento_immutable BEFORE UPDATE OR DELETE ON movimiento_economico
            FOR EACH ROW EXECUTE FUNCTION economic_immutable_record();
        CREATE TRIGGER trg_constancia_immutable BEFORE UPDATE OR DELETE ON constancia_devolucion
            FOR EACH ROW EXECUTE FUNCTION economic_immutable_record();
        CREATE FUNCTION economic_cut_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.control_version=1 AND OLD.cco_estado <> 'abierto' THEN
                RAISE EXCEPTION 'A closed controlled cash cut is immutable' USING ERRCODE='23514';
            END IF;
            IF TG_OP='DELETE' THEN RETURN OLD; END IF;
            IF NEW.control_version IS DISTINCT FROM OLD.control_version THEN
                RAISE EXCEPTION 'The control version cannot be reclassified' USING ERRCODE='23514';
            END IF;
            IF OLD.control_version=1 AND (NEW.usu_id_cajero IS DISTINCT FROM OLD.usu_id_cajero
                OR NEW.cco_fondo_asignado IS DISTINCT FROM OLD.cco_fondo_asignado
                OR NEW.cco_fec_apertura IS DISTINCT FROM OLD.cco_fec_apertura) THEN
                RAISE EXCEPTION 'Controlled cut ownership, opening date and initial fund are immutable' USING ERRCODE='23514';
            END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER trg_corte_controlled BEFORE UPDATE OR DELETE ON corte_caja
            FOR EACH ROW EXECUTE FUNCTION economic_cut_guard();
        CREATE FUNCTION economic_movement_cut_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE cut corte_caja%ROWTYPE; rental salida_flete%ROWTYPE;
            received numeric; discharged numeric; physical numeric; reserved numeric; released numeric;
        BEGIN
            IF NEW.corte_id IS NOT NULL THEN
                SELECT * INTO STRICT cut FROM corte_caja WHERE cco_id=NEW.corte_id FOR UPDATE;
                IF cut.control_version<>1 OR cut.cco_estado<>'abierto' THEN
                    RAISE EXCEPTION 'Movements require an open controlled cash cut' USING ERRCODE='23514';
                END IF;
            END IF;
            IF NEW.evento='fondo' AND (NEW.corte_id IS NULL OR NEW.origen_tipo IS DISTINCT FROM 'corte_caja'
                OR NEW.origen_id IS DISTINCT FROM NEW.corte_id OR NEW.monto_bob IS DISTINCT FROM cut.cco_fondo_asignado OR NEW.metodo_pago<>'efectivo') THEN
                RAISE EXCEPTION 'Invalid initial fund movement' USING ERRCODE='23514';
            END IF;
            IF NEW.evento in ('egreso','ajuste_egreso') AND (NEW.egreso_id IS NULL OR NEW.origen_tipo IS DISTINCT FROM 'egreso' OR NEW.origen_id IS DISTINCT FROM NEW.egreso_id) THEN
                RAISE EXCEPTION 'Expense movement requires its linked expense' USING ERRCODE='23514';
            END IF;
            IF NEW.evento LIKE 'garantia_%' AND (NEW.salida_flete_id IS NULL OR NEW.origen_tipo IS DISTINCT FROM 'salida_flete' OR NEW.origen_id IS DISTINCT FROM NEW.salida_flete_id) THEN
                RAISE EXCEPTION 'Custody movement requires its linked rental output' USING ERRCODE='23514';
            END IF;
            IF NEW.evento LIKE 'garantia_%' THEN
                SELECT * INTO STRICT rental FROM salida_flete WHERE sfl_id=NEW.salida_flete_id FOR UPDATE;
                SELECT coalesce(sum(monto_bob) FILTER (WHERE evento='garantia_recibida'),0),
                       coalesce(sum(monto_bob) FILTER (WHERE evento in ('garantia_devuelta','garantia_retenida')),0)
                INTO received,discharged FROM movimiento_economico WHERE salida_flete_id=NEW.salida_flete_id;
                IF (NEW.evento='garantia_recibida' AND (received<>0 OR NEW.monto_bob<>rental.sfl_garantia))
                    OR (NEW.evento<>'garantia_recibida' AND NEW.monto_bob>received-discharged) THEN
                    RAISE EXCEPTION 'Custody movement exceeds the certified guarantee balance' USING ERRCODE='23514';
                END IF;
            END IF;
            IF NEW.corte_id IS NOT NULL AND NEW.metodo_pago='efectivo' AND NEW.direccion=-1 THEN
                SELECT coalesce(sum(monto_original*direccion),0) INTO physical
                FROM movimiento_economico WHERE corte_id=NEW.corte_id AND moneda_codigo='BOB' AND metodo_pago='efectivo';
                SELECT coalesce(sum(greatest(0,cash_in-returned)),0) INTO reserved FROM (
                    SELECT salida_flete_id,
                        coalesce(sum(monto_bob) FILTER (WHERE evento='garantia_recibida' AND metodo_pago='efectivo'),0) cash_in,
                        coalesce(sum(monto_bob) FILTER (WHERE evento='garantia_devuelta'),0) returned
                    FROM movimiento_economico WHERE corte_id=NEW.corte_id AND evento LIKE 'garantia_%'
                    GROUP BY salida_flete_id
                ) custody;
                released:=0;
                IF NEW.evento='garantia_devuelta' THEN
                    SELECT least(NEW.monto_bob,greatest(0,
                        coalesce(sum(monto_bob) FILTER (WHERE evento='garantia_recibida' AND metodo_pago='efectivo'),0)
                        -coalesce(sum(monto_bob) FILTER (WHERE evento='garantia_devuelta'),0))) INTO released
                    FROM movimiento_economico WHERE corte_id=NEW.corte_id AND salida_flete_id=NEW.salida_flete_id;
                END IF;
                IF NEW.monto_bob>physical-reserved+released THEN
                    RAISE EXCEPTION 'Insufficient unreserved BOB cash in the controlled cut' USING ERRCODE='23514';
                END IF;
            END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER trg_movimiento_cut BEFORE INSERT ON movimiento_economico
            FOR EACH ROW EXECUTE FUNCTION economic_movement_cut_guard();
        CREATE FUNCTION economic_request_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP='DELETE' OR OLD.resultado IS NOT NULL OR NEW.actor_id IS DISTINCT FROM OLD.actor_id
                OR NEW.operacion IS DISTINCT FROM OLD.operacion OR NEW.clave IS DISTINCT FROM OLD.clave
                OR NEW.payload_hash IS DISTINCT FROM OLD.payload_hash THEN
                RAISE EXCEPTION 'Idempotent economic evidence cannot be replaced' USING ERRCODE='23514';
            END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER trg_solicitud_immutable BEFORE UPDATE OR DELETE ON solicitud_economica
            FOR EACH ROW EXECUTE FUNCTION economic_request_guard();
    """)


def downgrade():
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM movimiento_economico) OR EXISTS (SELECT 1 FROM constancia_devolucion)
            OR EXISTS (SELECT 1 FROM solicitud_economica) OR EXISTS (SELECT 1 FROM corte_caja WHERE control_version=1)
        THEN RAISE EXCEPTION 'Downgrade would discard controlled economic evidence; reviewed recovery is required';
        END IF;
    END $$;""")
    for name in ("economic_request_guard", "economic_movement_cut_guard", "economic_cut_guard", "economic_immutable_record"):
        op.execute(f"DROP FUNCTION {name}() CASCADE")
    op.drop_table("solicitud_economica")
    op.drop_table("constancia_devolucion")
    op.drop_table("movimiento_economico")
    op.drop_constraint("ck_salida_flete_num", "salida_flete", type_="check")
    op.create_check_constraint("ck_salida_flete_num", "salida_flete", "sfl_num between 1 and 4")
    for table in ("venta_boutique", "pago_pedido", "salida_flete"):
        op.drop_index(f"ix_{table}_corte_id", table_name=table)
        op.drop_constraint(f"fk_{table}_corte", table, type_="foreignkey")
        op.drop_column(table, "corte_id")
    op.drop_column("egreso", "metodo_pago")
    op.drop_constraint("ck_cco_snapshot", "corte_caja", type_="check")
    op.drop_constraint("ck_cco_control_version", "corte_caja", type_="check")
    op.drop_column("corte_caja", "cierre_snapshot")
    op.drop_column("corte_caja", "control_version")
