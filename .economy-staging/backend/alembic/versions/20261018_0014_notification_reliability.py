"""Notification episodes, atomic delivery and historical duplicate repair.

Revision ID: 20261018_0014
Revises: 20260620_0013

Requires PostgreSQL 17 and a maintenance window with all notification writers
paused. Prepare a backup and run the read-only diagnostic before authorization.
The repair preserves every row; downgrade never reopens repaired duplicates.
"""

from alembic import op
import sqlalchemy as sa


revision = "20261018_0014"
down_revision = "20260620_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A transactional index is deliberate: repair and enforcement must become
    # visible together. Fail promptly rather than wait indefinitely for writers.
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute("""
        DO $$ BEGIN
            IF current_setting('server_version_num')::integer < 170000 THEN
                RAISE EXCEPTION 'Notification reliability migration requires PostgreSQL 17 or newer';
            END IF;
        END $$;
    """)
    op.execute("LOCK TABLE notificacion IN ACCESS EXCLUSIVE MODE")
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM notificacion WHERE length(btrim(not_tipo)) = 0) THEN
                RAISE EXCEPTION 'Blank notification type requires reviewed repair before migrating';
            END IF;
        END $$;
    """)
    op.add_column("notificacion", sa.Column("not_revision", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("notificacion", sa.Column("not_revision_fecha", sa.DateTime(timezone=True), nullable=True))
    op.add_column("notificacion", sa.Column("not_stock_cero_detectado", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("notificacion", sa.Column("not_escritorio_revision_reclamada", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("notificacion", sa.Column("not_motivo_cierre", sa.String(50), nullable=True))
    op.add_column("notificacion", sa.Column("not_duplicada_de_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key("fk_notificacion_duplicada_de", "notificacion", "notificacion", ["not_duplicada_de_id"], ["not_id"], ondelete="RESTRICT")

    op.execute("""
        WITH normalized AS (
            UPDATE notificacion
            SET not_tipo = upper(btrim(not_tipo)),
                not_tabla_ref = nullif(upper(btrim(not_tabla_ref)), '')
            WHERE not_tipo IS DISTINCT FROM upper(btrim(not_tipo))
               OR not_tabla_ref IS DISTINCT FROM nullif(upper(btrim(not_tabla_ref)), '')
            RETURNING not_id
        )
        INSERT INTO auditoria_sistema (
            aud_modulo, aud_submodulo, aud_tabla, aud_id_registro, aud_accion,
            aud_accion_funcional, aud_descripcion, aud_id_evento
        )
        SELECT 'NOTIFICACIONES', 'MANTENIMIENTO', 'notificacion', '20261018_0014',
               'otro'::tipo_accion_auditoria, 'NORMALIZACION_CLAVES',
               'CLAVES NORMALIZADAS: ' || count(*)::text, gen_random_uuid()
        FROM normalized HAVING count(*) > 0;
    """)
    # Historical notifications must not become fresh desktop events. Current
    # stock at zero is remembered without manufacturing a new revision.
    op.execute("""
        UPDATE notificacion n
        SET not_revision_fecha = n.not_fec,
            not_escritorio_revision_reclamada = n.not_revision,
            not_stock_cero_detectado = (
                (n.not_tipo = 'STOCK_BAJO_BOUTIQUE' AND n.not_tabla_ref = 'ITEM_BOUTIQUE'
                 AND EXISTS (SELECT 1 FROM item_boutique i WHERE i.itb_id = n.not_id_ref AND i.itb_stock = 0))
                OR
                (n.not_tipo = 'STOCK_BAJO_TALLER' AND n.not_tabla_ref = 'INVENTARIO_TALLER'
                 AND EXISTS (SELECT 1 FROM inventario_taller i WHERE i.int_id = n.not_id_ref AND i.int_stock = 0))
            ) IS TRUE;
    """)
    op.alter_column("notificacion", "not_revision_fecha", nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"))
    op.execute("""
        WITH ranked AS (
            SELECT not_id,
                   first_value(not_id) OVER (
                       PARTITION BY usu_id, not_tipo, not_tabla_ref, not_id_ref
                       ORDER BY not_fec, not_id
                   ) AS canonical_id
            FROM notificacion WHERE not_resuelta = false
        ), repaired AS (
            UPDATE notificacion n
            SET not_resuelta = true, not_fec_resuelta = CURRENT_TIMESTAMP,
                not_motivo_cierre = 'DUPLICADA', not_duplicada_de_id = r.canonical_id
            FROM ranked r
            WHERE n.not_id = r.not_id AND r.not_id <> r.canonical_id
              AND n.not_resuelta = false
            RETURNING n.not_id, n.not_duplicada_de_id
        )
        INSERT INTO auditoria_sistema (
            aud_modulo, aud_submodulo, aud_tabla, aud_id_registro, aud_accion,
            aud_accion_funcional, aud_descripcion, aud_campo,
            aud_valor_anterior, aud_valor_nuevo, aud_id_evento
        )
        SELECT 'NOTIFICACIONES', 'MANTENIMIENTO', 'notificacion', not_id::text,
               'cambio_estado'::tipo_accion_auditoria, 'CIERRE_DUPLICADA',
               'CIERRE HISTORICO SIN BORRAR NI MODIFICAR LECTURA', 'not_duplicada_de_id',
               NULL, not_duplicada_de_id::text, gen_random_uuid()
        FROM repaired;
    """)
    op.create_check_constraint("ck_not_revision_positiva", "notificacion", "not_revision >= 1")
    op.create_check_constraint("ck_not_escritorio_revision", "notificacion", "not_escritorio_revision_reclamada >= 0 and not_escritorio_revision_reclamada <= not_revision")
    op.create_check_constraint(
        "ck_not_clave_normalizada", "notificacion",
        "not_tipo = upper(btrim(not_tipo)) and length(not_tipo) > 0 and "
        "(not_tabla_ref is null or (not_tabla_ref = upper(btrim(not_tabla_ref)) and length(not_tabla_ref) > 0))",
    )
    op.create_check_constraint(
        "ck_not_duplicada_cerrada", "notificacion",
        "not_duplicada_de_id is null or (not_duplicada_de_id <> not_id and not_resuelta = true and not_motivo_cierre is not null and not_motivo_cierre = 'DUPLICADA')",
    )
    op.create_index(
        "ux_notificacion_abierta", "notificacion", ["usu_id", "not_tipo", "not_tabla_ref", "not_id_ref"],
        unique=True, postgresql_where=sa.text("not_resuelta = false"), postgresql_nulls_not_distinct=True,
    )
    # Personal eligible desktop scans; historic unread/resolved rows are excluded.
    op.create_index(
        "idx_notificacion_escritorio", "notificacion", ["usu_id", "not_revision_fecha", "not_id"],
        postgresql_where=sa.text("not_resuelta = false and not_leida = false"),
    )
    op.create_table(
        "preferencia_notificacion",
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("escritorio_habilitado_desde", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "envio_notificacion_correo",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("cuenta_id", sa.Integer(), sa.ForeignKey("cuentas.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("destino", sa.String(320), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="BLOQUEADO"),
        sa.Column("intentos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("intento_id", sa.String(36), nullable=True),
        sa.Column("ultimo_intento", sa.DateTime(timezone=True), nullable=True),
        sa.Column("proximo_intento", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fecha_resultado", sa.DateTime(timezone=True), nullable=True),
        sa.Column("categoria_error", sa.String(50), nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("cuenta_id", "destino", name="uq_envio_notificacion_cuenta_destino"),
        sa.CheckConstraint("intentos >= 0", name="ck_envio_notificacion_intentos"),
        sa.CheckConstraint("estado in ('EN_CURSO', 'ENVIADO', 'FALLIDO', 'INCIERTO', 'BLOQUEADO')", name="ck_envio_notificacion_estado"),
        sa.CheckConstraint("destino = lower(btrim(destino)) and length(destino) > 0", name="ck_envio_notificacion_destino"),
    )
    op.create_index("idx_envio_notificacion_reintento", "envio_notificacion_correo", ["proximo_intento"], postgresql_where=sa.text("estado = 'FALLIDO'"))


def downgrade() -> None:
    """Remove new schema only; repaired rows stay closed and audits stay intact.

    Destructive to delivery/preferences metadata: restore a reviewed backup when
    that metadata is needed. This is not a data repair undo operation.
    """
    op.drop_index("idx_envio_notificacion_reintento", table_name="envio_notificacion_correo")
    op.drop_table("envio_notificacion_correo")
    op.drop_table("preferencia_notificacion")
    op.drop_index("idx_notificacion_escritorio", table_name="notificacion")
    op.drop_index("ux_notificacion_abierta", table_name="notificacion")
    for name in ("ck_not_duplicada_cerrada", "ck_not_clave_normalizada", "ck_not_escritorio_revision", "ck_not_revision_positiva"):
        op.drop_constraint(name, "notificacion", type_="check")
    op.drop_constraint("fk_notificacion_duplicada_de", "notificacion", type_="foreignkey")
    for column in ("not_duplicada_de_id", "not_motivo_cierre", "not_escritorio_revision_reclamada", "not_stock_cero_detectado", "not_revision_fecha", "not_revision"):
        op.drop_column("notificacion", column)
