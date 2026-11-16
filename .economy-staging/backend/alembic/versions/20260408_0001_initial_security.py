"""initial security schema

Revision ID: 20260408_0001
Revises:
Create Date: 2026-04-08 01:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260408_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_roles_codigo", "roles", ["codigo"], unique=True)
    op.create_index("ix_roles_id", "roles", ["id"], unique=False)
    op.create_unique_constraint("uq_roles_nombre", "roles", ["nombre"])

    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombres", sa.String(length=120), nullable=False),
        sa.Column("apellido_paterno", sa.String(length=120), nullable=False),
        sa.Column("apellido_materno", sa.String(length=120), nullable=True),
        sa.Column("ci", sa.String(length=30), nullable=False),
        sa.Column("celular", sa.String(length=30), nullable=False),
        sa.Column("correo", sa.String(length=150), nullable=False),
        sa.Column("zona", sa.String(length=120), nullable=False),
        sa.Column("direccion", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_usuarios_id", "usuarios", ["id"], unique=False)
    op.create_index("ix_usuarios_ci", "usuarios", ["ci"], unique=True)
    op.create_index("ix_usuarios_correo", "usuarios", ["correo"], unique=True)

    op.create_table(
        "cuentas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("rol_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["rol_id"], ["roles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("usuario_id"),
    )
    op.create_index("ix_cuentas_id", "cuentas", ["id"], unique=False)
    op.create_index("ix_cuentas_username", "cuentas", ["username"], unique=True)

    op.create_table(
        "auditoria_sistema",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cuenta_id", sa.Integer(), nullable=True),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("accion", sa.String(length=80), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("referencia", sa.String(length=120), nullable=True),
        sa.Column("ip_address", sa.String(length=60), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["cuenta_id"], ["cuentas.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_auditoria_sistema_id", "auditoria_sistema", ["id"], unique=False)
    op.create_index("ix_auditoria_sistema_accion", "auditoria_sistema", ["accion"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_auditoria_sistema_accion", table_name="auditoria_sistema")
    op.drop_index("ix_auditoria_sistema_id", table_name="auditoria_sistema")
    op.drop_table("auditoria_sistema")
    op.drop_index("ix_cuentas_username", table_name="cuentas")
    op.drop_index("ix_cuentas_id", table_name="cuentas")
    op.drop_table("cuentas")
    op.drop_index("ix_usuarios_correo", table_name="usuarios")
    op.drop_index("ix_usuarios_ci", table_name="usuarios")
    op.drop_index("ix_usuarios_id", table_name="usuarios")
    op.drop_table("usuarios")
    op.drop_constraint("uq_roles_nombre", "roles", type_="unique")
    op.drop_index("ix_roles_id", table_name="roles")
    op.drop_index("ix_roles_codigo", table_name="roles")
    op.drop_table("roles")

