"""notifications module

Revision ID: 20260529_0009
Revises: 20260525_0008
Create Date: 2026-05-29 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260529_0009"
down_revision = "20260525_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    prioridad_notificacion = sa.Enum("baja", "media", "alta", "urgente", name="prioridad_notificacion")
    prioridad_notificacion.create(op.get_bind(), checkfirst=True)
    prioridad_notificacion_column = postgresql.ENUM(
        "baja",
        "media",
        "alta",
        "urgente",
        name="prioridad_notificacion",
        create_type=False,
    )
    op.create_table(
        "notificacion",
        sa.Column("not_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("usu_id", sa.BigInteger(), sa.ForeignKey("usuarios.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False),
        sa.Column("not_tipo", sa.String(length=200), nullable=False),
        sa.Column("not_prioridad", prioridad_notificacion_column, nullable=False, server_default="media"),
        sa.Column("not_titulo", sa.String(length=120), nullable=False),
        sa.Column("not_mensaje", sa.Text(), nullable=False),
        sa.Column("not_modulo", sa.String(length=50)),
        sa.Column("not_leida", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("not_fec", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("not_fec_leida", sa.DateTime(timezone=True)),
        sa.Column("not_tabla_ref", sa.String(length=100)),
        sa.Column("not_id_ref", sa.BigInteger()),
        sa.Column("not_resuelta", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("not_fec_resuelta", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "((not_resuelta = false and not_fec_resuelta is null) or (not_resuelta = true and not_fec_resuelta is not null))",
            name="ck_not_resuelta_fecha",
        ),
    )
    op.create_index("idx_notificacion_usuario_fecha", "notificacion", ["usu_id", "not_fec"], unique=False)
    op.create_index("idx_notificacion_usuario_leida", "notificacion", ["usu_id", "not_leida"], unique=False)
    op.create_index("idx_notificacion_tipo_fecha", "notificacion", ["not_tipo", "not_fec"], unique=False)
    op.create_index("idx_notificacion_prioridad_fecha", "notificacion", ["not_prioridad", "not_fec"], unique=False)
    op.create_index("idx_notificacion_modulo_fecha", "notificacion", ["not_modulo", "not_fec"], unique=False)
    op.create_index("idx_notificacion_referencia", "notificacion", ["not_tabla_ref", "not_id_ref"], unique=False)
    op.execute(
        sa.text(
            "create index if not exists idx_notificacion_pendientes on notificacion (usu_id, not_fec desc) where not_leida = false"
        )
    )
    op.execute(
        sa.text(
            "create index if not exists idx_notificacion_no_resuelta on notificacion (usu_id, not_fec desc) where not_resuelta = false"
        )
    )


def downgrade() -> None:
    op.execute("drop index if exists idx_notificacion_no_resuelta")
    op.execute("drop index if exists idx_notificacion_pendientes")
    op.drop_index("idx_notificacion_referencia", table_name="notificacion")
    op.drop_index("idx_notificacion_modulo_fecha", table_name="notificacion")
    op.drop_index("idx_notificacion_prioridad_fecha", table_name="notificacion")
    op.drop_index("idx_notificacion_tipo_fecha", table_name="notificacion")
    op.drop_index("idx_notificacion_usuario_leida", table_name="notificacion")
    op.drop_index("idx_notificacion_usuario_fecha", table_name="notificacion")
    op.drop_table("notificacion")
    sa.Enum(name="prioridad_notificacion").drop(op.get_bind(), checkfirst=True)
