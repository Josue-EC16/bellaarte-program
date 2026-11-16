"""backup module

Revision ID: 20260620_0013
Revises: 20260615_0012
Create Date: 2026-06-20 11:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260620_0013"
down_revision = "20260615_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tipo_backup_bd') THEN
                CREATE TYPE tipo_backup_bd AS ENUM (
                    'LOGICO_COMPLETO',
                    'SEMANAL',
                    'MANUAL'
                );
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estado_backup_bd') THEN
                CREATE TYPE estado_backup_bd AS ENUM (
                    'EN_PROCESO',
                    'EXITOSO',
                    'FALLIDO'
                );
            END IF;
        END$$;
        """
    )

    tipo_backup_enum = postgresql.ENUM(
        "LOGICO_COMPLETO",
        "SEMANAL",
        "MANUAL",
        name="tipo_backup_bd",
        create_type=False,
    )
    estado_backup_enum = postgresql.ENUM(
        "EN_PROCESO",
        "EXITOSO",
        "FALLIDO",
        name="estado_backup_bd",
        create_type=False,
    )

    op.create_table(
        "backup_bd",
        sa.Column("bkp_id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("usu_id", sa.Integer(), sa.ForeignKey("usuarios.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=True),
        sa.Column("bkp_tipo", tipo_backup_enum, nullable=False),
        sa.Column("bkp_estado", estado_backup_enum, nullable=False, server_default=sa.text("'EN_PROCESO'")),
        sa.Column("bkp_origen", sa.String(length=30), nullable=False),
        sa.Column("bkp_nombre_archivo", sa.String(length=255), nullable=False),
        sa.Column("bkp_ruta_archivo", sa.Text(), nullable=False),
        sa.Column("bkp_tamano_bytes", sa.BigInteger(), nullable=True),
        sa.Column("bkp_hash_sha256", sa.String(length=128), nullable=True),
        sa.Column("bkp_fec_inicio", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("bkp_fec_fin", sa.DateTime(timezone=True), nullable=True),
        sa.Column("bkp_pg_dump_version", sa.String(length=100), nullable=True),
        sa.Column("bkp_db_nombre", sa.String(length=150), nullable=True),
        sa.Column("bkp_observacion", sa.Text(), nullable=True),
        sa.Column("bkp_error", sa.Text(), nullable=True),
        sa.CheckConstraint("bkp_origen in ('AUTOMATICO', 'MANUAL')", name="ck_backup_origen"),
        sa.CheckConstraint("bkp_tamano_bytes is null or bkp_tamano_bytes >= 0", name="ck_backup_tamano"),
        sa.CheckConstraint(
            "((bkp_estado = 'EN_PROCESO' and bkp_fec_fin is null) or "
            "(bkp_estado in ('EXITOSO', 'FALLIDO') and bkp_fec_fin is not null))",
            name="ck_backup_estado_fechas",
        ),
    )

    op.create_index("ix_backup_bd_fec_inicio", "backup_bd", ["bkp_fec_inicio"], unique=False)
    op.create_index("ix_backup_bd_estado_fec_inicio", "backup_bd", ["bkp_estado", "bkp_fec_inicio"], unique=False)
    op.create_index("ix_backup_bd_tipo_fec_inicio", "backup_bd", ["bkp_tipo", "bkp_fec_inicio"], unique=False)
    op.create_index("ix_backup_bd_origen_fec_inicio", "backup_bd", ["bkp_origen", "bkp_fec_inicio"], unique=False)
    op.create_index("ix_backup_bd_usu_fec_inicio", "backup_bd", ["usu_id", "bkp_fec_inicio"], unique=False)
    op.create_index("ix_backup_bd_nombre_archivo", "backup_bd", ["bkp_nombre_archivo"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_backup_bd_nombre_archivo", table_name="backup_bd")
    op.drop_index("ix_backup_bd_usu_fec_inicio", table_name="backup_bd")
    op.drop_index("ix_backup_bd_origen_fec_inicio", table_name="backup_bd")
    op.drop_index("ix_backup_bd_tipo_fec_inicio", table_name="backup_bd")
    op.drop_index("ix_backup_bd_estado_fec_inicio", table_name="backup_bd")
    op.drop_index("ix_backup_bd_fec_inicio", table_name="backup_bd")
    op.drop_table("backup_bd")
    op.execute("DROP TYPE IF EXISTS estado_backup_bd")
    op.execute("DROP TYPE IF EXISTS tipo_backup_bd")
