"""audit system module

Revision ID: 20260605_0011
Revises: 20260604_0010
Create Date: 2026-06-05 12:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260605_0011"
down_revision = "20260604_0010"
branch_labels = None
depends_on = None


TRIGGER_TABLES = (
    "venta_boutique",
    "pago_pedido",
    "pedido",
    "prueba_pedido",
    "comprobante_interno",
    "salida_flete",
    "flete_vestido",
    "item_boutique",
    "entrada_item_boutique",
    "inventario_taller",
    "entrada_inventario_taller",
    "salida_material_taller",
    "egreso",
    "moneda",
    "tipo_cambio_moneda",
    "usuarios",
    "cuentas",
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tipo_accion_auditoria') THEN
                CREATE TYPE tipo_accion_auditoria AS ENUM (
                    'insert',
                    'update',
                    'delete',
                    'login',
                    'logout',
                    'cancelacion',
                    'anulacion',
                    'cambio_estado',
                    'otro'
                );
            END IF;
        END$$;
        """
    )

    op.rename_table("auditoria_sistema", "auditoria_sistema_legacy")
    op.drop_index("ix_auditoria_sistema_accion", table_name="auditoria_sistema_legacy")
    op.drop_index("ix_auditoria_sistema_id", table_name="auditoria_sistema_legacy")

    tipo_accion_enum = postgresql.ENUM(
        "insert",
        "update",
        "delete",
        "login",
        "logout",
        "cancelacion",
        "anulacion",
        "cambio_estado",
        "otro",
        name="tipo_accion_auditoria",
        create_type=False,
    )

    op.create_table(
        "auditoria_sistema",
        sa.Column("aud_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("usu_id", sa.Integer(), sa.ForeignKey("usuarios.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True),
        sa.Column("aud_fec", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("aud_modulo", sa.String(length=100), nullable=False),
        sa.Column("aud_submodulo", sa.String(length=100), nullable=True),
        sa.Column("aud_tabla", sa.String(length=200), nullable=False),
        sa.Column("aud_id_registro", sa.String(length=200), nullable=False),
        sa.Column("aud_accion", tipo_accion_enum, nullable=False),
        sa.Column("aud_accion_funcional", sa.String(length=150), nullable=True),
        sa.Column("aud_descripcion", sa.Text(), nullable=True),
        sa.Column("aud_campo", sa.String(length=200), nullable=True),
        sa.Column("aud_valor_anterior", sa.Text(), nullable=True),
        sa.Column("aud_valor_nuevo", sa.Text(), nullable=True),
        sa.Column("aud_metodo_http", sa.String(length=10), nullable=True),
        sa.Column("aud_ip", sa.String(length=100), nullable=True),
        sa.Column("aud_user_agent", sa.Text(), nullable=True),
        sa.Column("aud_dispositivo", sa.String(length=200), nullable=True),
        sa.Column("aud_navegador", sa.String(length=100), nullable=True),
        sa.Column("aud_sistema_operativo", sa.String(length=100), nullable=True),
        sa.Column("aud_id_evento", postgresql.UUID(as_uuid=False), nullable=True),
    )

    op.execute(
        """
        INSERT INTO auditoria_sistema (
            usu_id,
            aud_fec,
            aud_modulo,
            aud_submodulo,
            aud_tabla,
            aud_id_registro,
            aud_accion,
            aud_accion_funcional,
            aud_descripcion,
            aud_metodo_http,
            aud_ip,
            aud_user_agent
        )
        SELECT
            usuario_id,
            created_at,
            CASE
                WHEN upper(accion) LIKE 'LOGIN%' OR upper(accion) IN ('LOGOUT', 'PASSWORD_CHANGED', 'PASSWORD_RESET', 'ROLE_CREATED', 'ROLE_UPDATED', 'ROLE_STATUS_CHANGED', 'USER_CREATED', 'USER_UPDATED', 'ACCOUNT_STATUS_CHANGED')
                    THEN 'SEGURIDAD'
                WHEN upper(accion) LIKE 'CLIENT%' THEN 'CLIENTES'
                WHEN upper(accion) LIKE 'BOUTIQUE_PROVIDER%' THEN 'PROVEEDORES'
                WHEN upper(accion) LIKE 'CURRENCY%' THEN 'MONEDAS'
                WHEN upper(accion) LIKE 'EXCHANGE_RATE%' THEN 'TIPO_CAMBIO'
                WHEN upper(accion) LIKE 'BOUTIQUE_SALE%' THEN 'VENTAS_BOUTIQUE'
                WHEN upper(accion) LIKE 'BOUTIQUE_%' THEN 'INVENTARIO_BOUTIQUE'
                WHEN upper(accion) LIKE 'FLETE_%' THEN 'FLETES'
                WHEN upper(accion) LIKE 'WORKSHOP_%' THEN 'INVENTARIO_TALLER'
                WHEN upper(accion) LIKE 'ORDER_PAYMENT%' THEN 'PAGOS_PEDIDO'
                WHEN upper(accion) LIKE 'ORDER_TEST%' THEN 'PRUEBAS_PEDIDO'
                WHEN upper(accion) LIKE 'ORDER_%' THEN 'PEDIDOS'
                WHEN upper(accion) LIKE 'RECEIPT%' THEN 'COMPROBANTES'
                WHEN upper(accion) LIKE 'ECONOMY_EXPENSE%' OR upper(accion) LIKE 'ECONOMY_REFUND%' THEN 'EGRESOS'
                WHEN upper(accion) LIKE 'CASH_CUT%' THEN 'CORTE_CAJA'
                WHEN upper(accion) LIKE 'NOTIFICATION%' THEN 'NOTIFICACIONES'
                ELSE 'SISTEMA'
            END,
            regexp_replace(upper(accion), '_', ' ', 'g'),
            CASE
                WHEN upper(accion) LIKE 'ROLE_%' THEN 'roles'
                WHEN upper(accion) LIKE 'USER_%' OR upper(accion) LIKE 'ACCOUNT_%' OR upper(accion) LIKE 'LOGIN%' OR upper(accion) IN ('LOGOUT', 'PASSWORD_CHANGED', 'PASSWORD_RESET') THEN 'cuentas'
                WHEN upper(accion) LIKE 'CLIENT_%' THEN 'cliente'
                WHEN upper(accion) LIKE 'BOUTIQUE_PROVIDER_%' THEN 'proveedor'
                WHEN upper(accion) LIKE 'BOUTIQUE_TYPE_%' THEN 'tipo_item_boutique'
                WHEN upper(accion) LIKE 'BOUTIQUE_ITEM_%' THEN 'item_boutique'
                WHEN upper(accion) LIKE 'BOUTIQUE_ENTRY_%' THEN 'entrada_item_boutique'
                WHEN upper(accion) LIKE 'BOUTIQUE_SALE_%' THEN 'venta_boutique'
                WHEN upper(accion) LIKE 'CURRENCY_%' THEN 'moneda'
                WHEN upper(accion) LIKE 'EXCHANGE_RATE_%' THEN 'tipo_cambio_moneda'
                WHEN upper(accion) LIKE 'FLETE_OUTPUT_%' THEN 'salida_flete'
                WHEN upper(accion) LIKE 'FLETE_RECEIPT_%' THEN 'comprobante_interno'
                WHEN upper(accion) LIKE 'FLETE_%' THEN 'flete_vestido'
                WHEN upper(accion) LIKE 'WORKSHOP_TYPE_%' THEN 'tipo_inventario_taller'
                WHEN upper(accion) LIKE 'WORKSHOP_ITEM_%' THEN 'inventario_taller'
                WHEN upper(accion) LIKE 'WORKSHOP_ENTRY_%' THEN 'entrada_inventario_taller'
                WHEN upper(accion) LIKE 'WORKSHOP_OUTPUT_%' THEN 'salida_material_taller'
                WHEN upper(accion) LIKE 'ORDER_PAYMENT_%' THEN 'pago_pedido'
                WHEN upper(accion) LIKE 'ORDER_TEST_%' THEN 'prueba_pedido'
                WHEN upper(accion) LIKE 'ORDER_%' THEN 'pedido'
                WHEN upper(accion) LIKE 'RECEIPT_TYPE_%' THEN 'tipo_comprobante'
                WHEN upper(accion) LIKE 'ECONOMY_EXPENSE_%' OR upper(accion) LIKE 'ECONOMY_REFUND_%' THEN 'egreso'
                WHEN upper(accion) LIKE 'CASH_CUT_%' THEN 'corte_caja'
                WHEN upper(accion) LIKE 'NOTIFICATION_%' THEN 'notificacion'
                ELSE 'sistema'
            END,
            COALESCE(NULLIF(trim(referencia), ''), id::text),
            CASE
                WHEN upper(accion) = 'LOGOUT' THEN 'logout'::tipo_accion_auditoria
                WHEN upper(accion) LIKE 'LOGIN%' THEN 'login'::tipo_accion_auditoria
                WHEN upper(accion) LIKE '%ANNUL%' THEN 'anulacion'::tipo_accion_auditoria
                WHEN upper(accion) LIKE '%CANCEL%' THEN 'cancelacion'::tipo_accion_auditoria
                WHEN upper(accion) LIKE '%STATUS_CHANGED%' OR upper(accion) LIKE '%DELIVERED%' OR upper(accion) LIKE '%RETURNED%' OR upper(accion) LIKE '%RETIRED%' OR upper(accion) LIKE '%PASSED_TO_SALE%'
                    THEN 'cambio_estado'::tipo_accion_auditoria
                WHEN upper(accion) LIKE '%CREATED%' THEN 'insert'::tipo_accion_auditoria
                WHEN upper(accion) LIKE '%UPDATED%' THEN 'update'::tipo_accion_auditoria
                ELSE 'otro'::tipo_accion_auditoria
            END,
            regexp_replace(upper(accion), '_', ' ', 'g'),
            upper(descripcion),
            NULL,
            ip_address,
            user_agent
        FROM auditoria_sistema_legacy;
        """
    )

    op.drop_table("auditoria_sistema_legacy")

    op.create_index("ix_auditoria_sistema_fec", "auditoria_sistema", ["aud_fec"], unique=False)
    op.create_index("ix_auditoria_sistema_usu_fec", "auditoria_sistema", ["usu_id", "aud_fec"], unique=False)
    op.create_index("ix_auditoria_sistema_modulo_fec", "auditoria_sistema", ["aud_modulo", "aud_fec"], unique=False)
    op.create_index("ix_auditoria_sistema_tabla_fec", "auditoria_sistema", ["aud_tabla", "aud_fec"], unique=False)
    op.create_index("ix_auditoria_sistema_accion_fec", "auditoria_sistema", ["aud_accion", "aud_fec"], unique=False)
    op.create_index("ix_auditoria_sistema_evento", "auditoria_sistema", ["aud_id_evento"], unique=False)
    op.create_index("ix_auditoria_sistema_ip", "auditoria_sistema", ["aud_ip"], unique=False)
    op.create_index("ix_auditoria_sistema_registro", "auditoria_sistema", ["aud_id_registro"], unique=False)

    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_auditoria_mask_value(p_field text, p_value text)
        RETURNS text
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF p_value IS NULL THEN
                RETURN NULL;
            END IF;
            IF upper(coalesce(p_field, '')) LIKE '%PASSWORD%'
               OR upper(coalesce(p_field, '')) LIKE '%HASH%'
               OR upper(coalesce(p_field, '')) LIKE '%TOKEN%'
               OR upper(coalesce(p_field, '')) LIKE '%SECRET%' THEN
                RETURN '[OCULTO]';
            END IF;
            RETURN nullif(trim(p_value), '');
        END;
        $$;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_auditoria_trazabilidad()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            current_event_id uuid;
            current_user_id bigint;
            current_module text;
            current_submodule text;
            current_action tipo_accion_auditoria;
            current_functional text;
            current_http_method text;
            current_ip text;
            current_user_agent text;
            pk_column text;
            target_id text;
            field_name text;
            old_value text;
            new_value text;
            effective_row jsonb;
            has_context boolean;
        BEGIN
            current_event_id := nullif(current_setting('app.audit_event_id', true), '')::uuid;
            current_user_id := nullif(current_setting('app.audit_user_id', true), '')::bigint;
            current_module := nullif(current_setting('app.audit_modulo', true), '');
            current_submodule := nullif(current_setting('app.audit_submodulo', true), '');
            current_action := nullif(current_setting('app.audit_action', true), '')::tipo_accion_auditoria;
            current_functional := nullif(current_setting('app.audit_functional', true), '');
            current_http_method := nullif(current_setting('app.audit_http_method', true), '');
            current_ip := nullif(current_setting('app.audit_ip', true), '');
            current_user_agent := nullif(current_setting('app.audit_user_agent', true), '');
            has_context := current_event_id IS NOT NULL;

            IF current_event_id IS NULL THEN
                current_event_id := gen_random_uuid();
            END IF;

            IF TG_OP = 'DELETE' THEN
                effective_row := to_jsonb(OLD);
            ELSE
                effective_row := to_jsonb(NEW);
            END IF;

            SELECT a.attname
            INTO pk_column
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = TG_RELID
              AND i.indisprimary
            ORDER BY array_position(i.indkey, a.attnum)
            LIMIT 1;

            target_id := COALESCE(effective_row ->> pk_column, 'SIN_ID');

            IF TG_OP = 'UPDATE' THEN
                FOR field_name IN SELECT jsonb_object_keys(to_jsonb(NEW))
                LOOP
                    old_value := to_jsonb(OLD) ->> field_name;
                    new_value := to_jsonb(NEW) ->> field_name;
                    IF coalesce(old_value, '') IS DISTINCT FROM coalesce(new_value, '') THEN
                        IF field_name IN ('created_at', 'updated_at') THEN
                            CONTINUE;
                        END IF;
                        INSERT INTO auditoria_sistema (
                            usu_id,
                            aud_modulo,
                            aud_submodulo,
                            aud_tabla,
                            aud_id_registro,
                            aud_accion,
                            aud_accion_funcional,
                            aud_descripcion,
                            aud_campo,
                            aud_valor_anterior,
                            aud_valor_nuevo,
                            aud_metodo_http,
                            aud_ip,
                            aud_user_agent,
                            aud_id_evento
                        )
                        VALUES (
                            current_user_id,
                            COALESCE(current_module, 'SISTEMA'),
                            COALESCE(current_submodule, 'TRIGGER_BD'),
                            TG_TABLE_NAME,
                            target_id,
                            COALESCE(current_action, 'update'::tipo_accion_auditoria),
                            COALESCE(current_functional, 'TRAZABILIDAD AUTOMATICA DE BD'),
                            CASE
                                WHEN has_context THEN 'CAMBIO DE CAMPO DETECTADO POR TRIGGER'
                                ELSE 'TRAZABILIDAD AUTOMATICA DE BD'
                            END,
                            field_name,
                            fn_auditoria_mask_value(field_name, old_value),
                            fn_auditoria_mask_value(field_name, new_value),
                            current_http_method,
                            current_ip,
                            current_user_agent,
                            current_event_id
                        );
                    END IF;
                END LOOP;
                RETURN NEW;
            END IF;

            IF has_context THEN
                IF TG_OP = 'INSERT' THEN
                    RETURN NEW;
                END IF;
                RETURN OLD;
            END IF;

            INSERT INTO auditoria_sistema (
                usu_id,
                aud_modulo,
                aud_submodulo,
                aud_tabla,
                aud_id_registro,
                aud_accion,
                aud_accion_funcional,
                aud_descripcion,
                aud_metodo_http,
                aud_ip,
                aud_user_agent,
                aud_id_evento
            )
            VALUES (
                current_user_id,
                'SISTEMA',
                'TRIGGER_BD',
                TG_TABLE_NAME,
                target_id,
                CASE
                    WHEN TG_OP = 'INSERT' THEN 'insert'::tipo_accion_auditoria
                    WHEN TG_OP = 'DELETE' THEN 'delete'::tipo_accion_auditoria
                    ELSE 'update'::tipo_accion_auditoria
                END,
                'TRAZABILIDAD AUTOMATICA DE BD',
                'CAMBIO DETECTADO DIRECTAMENTE EN BASE DE DATOS',
                current_http_method,
                current_ip,
                current_user_agent,
                current_event_id
            );

            IF TG_OP = 'INSERT' THEN
                RETURN NEW;
            END IF;
            RETURN OLD;
        END;
        $$;
        """
    )

    for table_name in TRIGGER_TABLES:
        op.execute(f'DROP TRIGGER IF EXISTS trg_auditoria_{table_name} ON "{table_name}"')
        op.execute(
            f'CREATE TRIGGER trg_auditoria_{table_name} '
            f'AFTER INSERT OR UPDATE OR DELETE ON "{table_name}" '
            "FOR EACH ROW EXECUTE FUNCTION fn_auditoria_trazabilidad()"
        )


def downgrade() -> None:
    for table_name in TRIGGER_TABLES:
        op.execute(f'DROP TRIGGER IF EXISTS trg_auditoria_{table_name} ON "{table_name}"')

    op.execute("DROP FUNCTION IF EXISTS fn_auditoria_trazabilidad()")
    op.execute("DROP FUNCTION IF EXISTS fn_auditoria_mask_value(text, text)")

    op.drop_index("ix_auditoria_sistema_registro", table_name="auditoria_sistema")
    op.drop_index("ix_auditoria_sistema_ip", table_name="auditoria_sistema")
    op.drop_index("ix_auditoria_sistema_evento", table_name="auditoria_sistema")
    op.drop_index("ix_auditoria_sistema_accion_fec", table_name="auditoria_sistema")
    op.drop_index("ix_auditoria_sistema_tabla_fec", table_name="auditoria_sistema")
    op.drop_index("ix_auditoria_sistema_modulo_fec", table_name="auditoria_sistema")
    op.drop_index("ix_auditoria_sistema_usu_fec", table_name="auditoria_sistema")
    op.drop_index("ix_auditoria_sistema_fec", table_name="auditoria_sistema")

    op.rename_table("auditoria_sistema", "auditoria_sistema_rich")
    op.create_table(
        "auditoria_sistema",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cuenta_id", sa.Integer(), sa.ForeignKey("cuentas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True),
        sa.Column("accion", sa.String(length=80), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("referencia", sa.String(length=120), nullable=True),
        sa.Column("ip_address", sa.String(length=60), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_auditoria_sistema_id", "auditoria_sistema", ["id"], unique=False)
    op.create_index("ix_auditoria_sistema_accion", "auditoria_sistema", ["accion"], unique=False)

    op.execute(
        """
        INSERT INTO auditoria_sistema (usuario_id, accion, descripcion, referencia, ip_address, user_agent, created_at)
        SELECT
            usu_id,
            upper(aud_accion_funcional),
            coalesce(aud_descripcion, 'REGISTRO MIGRADO DESDE AUDITORIA ENRIQUECIDA'),
            aud_id_registro,
            aud_ip,
            left(coalesce(aud_user_agent, ''), 255),
            aud_fec
        FROM auditoria_sistema_rich;
        """
    )

    op.drop_table("auditoria_sistema_rich")
    op.execute("DROP TYPE IF EXISTS tipo_accion_auditoria")
