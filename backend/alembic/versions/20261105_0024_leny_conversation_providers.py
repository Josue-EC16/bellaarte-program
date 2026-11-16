"""Persist immutable conversation provider and technical Gemini usage only.

Application to the habitual ERP requires separate explicit authorization.
No commercial tables, publications, documents or permissions are modified.
"""
from alembic import op
import sqlalchemy as sa

revision = '20261105_0024'
down_revision = '20261104_0023'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    # The observed historical assistant model was exactly this local Qwen.
    # Refuse to invent provenance if the data changed since that inspection.
    unknown = connection.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM leny.mensajes "
        "WHERE role='assistant' AND (model IS NULL OR model<>'qwen3.5:4b-q4_K_M'))"))
    if unknown:
        raise RuntimeError('Historical conversation models require explicit review before provider backfill.')
    op.add_column('conversaciones', sa.Column('llm_provider', sa.String(16), nullable=False,
        server_default='ollama'), schema='leny')
    op.add_column('conversaciones', sa.Column('llm_model', sa.String(120), nullable=False,
        server_default='qwen3.5:4b-q4_K_M'), schema='leny')
    op.create_check_constraint('ck_leny_conversation_provider', 'conversaciones',
        "llm_provider IN ('ollama','gemini')", schema='leny')
    op.create_table('gemini_requests',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('request_id', sa.Uuid(), nullable=True),
        sa.Column('conversation_id', sa.Uuid(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('phase', sa.String(32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reserved_tokens', sa.Integer(), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('thinking_tokens', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(32), nullable=False, server_default='reserved'),
        sa.Column('error_code', sa.String(64), nullable=True),
        sa.CheckConstraint('reserved_tokens >= 0', name='ck_leny_gemini_reserved_positive'),
        sa.CheckConstraint('input_tokens IS NULL OR input_tokens >= 0', name='ck_leny_gemini_input_positive'),
        sa.CheckConstraint('output_tokens IS NULL OR output_tokens >= 0', name='ck_leny_gemini_output_positive'),
        sa.CheckConstraint('thinking_tokens IS NULL OR thinking_tokens >= 0', name='ck_leny_gemini_thinking_positive'),
        schema='leny')
    # Deliberately no cascading FK: technical quota history survives chat deletion.
    op.create_index('ix_leny_gemini_requests_created', 'gemini_requests', ['created_at'], schema='leny')


def downgrade():
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM leny.conversaciones WHERE llm_provider='gemini')")):
        raise RuntimeError('Gemini conversations must be preserved; use operational disable rather than destructive downgrade.')
    if connection.scalar(sa.text('SELECT EXISTS(SELECT 1 FROM leny.gemini_requests)')):
        raise RuntimeError('Gemini usage history must be preserved; use operational disable rather than destructive downgrade.')
    op.drop_index('ix_leny_gemini_requests_created', table_name='gemini_requests', schema='leny')
    op.drop_table('gemini_requests', schema='leny')
    op.drop_constraint('ck_leny_conversation_provider', 'conversaciones', schema='leny', type_='check')
    op.drop_column('conversaciones', 'llm_model', schema='leny')
    op.drop_column('conversaciones', 'llm_provider', schema='leny')
