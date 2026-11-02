"""Release open-cut custody after an externally funded ADMIN return.

0015 already validated/applied in the dedicated test database; this incremental
revision preserves its history and all immutable financial evidence.
"""
from alembic import op

revision = "20261018_0016"
down_revision = "20261018_0015"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
CREATE OR REPLACE FUNCTION economic_movement_cut_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
                        coalesce(sum(monto_bob) FILTER (WHERE evento='garantia_recibida' AND metodo_pago='efectivo' AND corte_id=NEW.corte_id),0) cash_in,
                        coalesce(sum(monto_bob) FILTER (WHERE evento='garantia_devuelta'),0) returned
                    FROM movimiento_economico WHERE salida_flete_id IN (SELECT salida_flete_id FROM movimiento_economico WHERE corte_id=NEW.corte_id AND evento='garantia_recibida') AND evento LIKE 'garantia_%'
                    GROUP BY salida_flete_id
                ) custody;
                released:=0;
                IF NEW.evento='garantia_devuelta' THEN
                    SELECT least(NEW.monto_bob,greatest(0,
                        coalesce(sum(monto_bob) FILTER (WHERE evento='garantia_recibida' AND metodo_pago='efectivo' AND corte_id=NEW.corte_id),0)
                        -coalesce(sum(monto_bob) FILTER (WHERE evento='garantia_devuelta'),0))) INTO released
                    FROM movimiento_economico WHERE salida_flete_id=NEW.salida_flete_id;
                END IF;
                IF NEW.monto_bob>physical-reserved+released THEN
                    RAISE EXCEPTION 'Insufficient unreserved BOB cash in the controlled cut' USING ERRCODE='23514';
                END IF;
            END IF;
            RETURN NEW;
        END $$;
    """)


def downgrade():
    op.execute("""
CREATE OR REPLACE FUNCTION economic_movement_cut_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
    """)
