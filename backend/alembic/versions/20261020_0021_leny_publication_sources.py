"""Pin approved document indices, revocable chat sources and provider quarantine.

Revision ID: 20261020_0021
Revises: 20261019_0020
No commercial structure or original/vector data is rewritten. No publication is
created by upgrade. Business rollback is disabling retrieval, not downgrade.
"""
from alembic import op
import sqlalchemy as sa

revision = '20261020_0021'
down_revision = '20261019_0020'
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint('uq_leny_rag_indexation_publication_state', 'rag_indexaciones',
                                ['version_id', 'id', 'status'], schema='leny')
    op.add_column('documentos', sa.Column('published_indexation_id', sa.Uuid()), schema='leny')
    op.add_column('documentos', sa.Column('published_at', sa.DateTime(timezone=True)), schema='leny')
    op.add_column('documentos', sa.Column('published_by', sa.Integer()), schema='leny')
    op.add_column('documentos', sa.Column('published_indexation_status', sa.String(16), sa.Computed(
        "CASE WHEN published_indexation_id IS NOT NULL THEN 'validated'::varchar(16) END", persisted=True)), schema='leny')
    op.create_foreign_key('fk_leny_document_published_actor', 'documentos', 'usuarios', ['published_by'], ['id'],
                          source_schema='leny', referent_schema='public', ondelete='RESTRICT')
    op.create_foreign_key('fk_leny_document_published_indexation', 'documentos', 'rag_indexaciones',
        ['published_version_id', 'published_indexation_id', 'published_indexation_status'], ['version_id', 'id', 'status'],
        source_schema='leny', referent_schema='leny', ondelete='RESTRICT')
    op.create_check_constraint('ck_leny_document_publication_metadata', 'documentos',
        '(published_version_id IS NULL AND published_indexation_id IS NULL AND published_at IS NULL AND published_by IS NULL) OR '
        '(published_version_id IS NOT NULL AND published_indexation_id IS NOT NULL AND published_at IS NOT NULL AND published_by IS NOT NULL)', schema='leny')
    op.create_check_constraint('ck_leny_document_publication_active', 'documentos',
                               "published_version_id IS NULL OR state='active'", schema='leny')
    op.drop_constraint('ck_leny_document_unpublished_stage01', 'documentos', type_='check', schema='leny')
    op.create_table('rag_fuentes_mensaje',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('message_id', sa.Uuid(), nullable=False),
        sa.Column('ordinal', sa.Integer(), nullable=False),
        sa.Column('fragment_id', sa.Uuid()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['message_id'], ['leny.mensajes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['fragment_id'], ['leny.rag_fragmentos.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('message_id', 'ordinal', name='uq_leny_rag_source_ordinal'),
        sa.UniqueConstraint('message_id', 'fragment_id', name='uq_leny_rag_source_fragment'),
        sa.CheckConstraint('ordinal BETWEEN 1 AND 5', name='ck_leny_rag_source_ordinal'), schema='leny')
    op.create_index('ix_leny_rag_source_fragment', 'rag_fuentes_mensaje', ['fragment_id'], schema='leny')
    op.create_table('inferencia_estado',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column('state', sa.String(16), nullable=False, server_default='idle'),
        sa.Column('request_id', sa.Uuid()),
        sa.Column('model', sa.String(120)),
        sa.Column('phase', sa.String(24)),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('id = 1', name='ck_leny_inference_singleton'),
        sa.CheckConstraint("state IN ('idle','inflight','uncertain')", name='ck_leny_inference_state'),
        sa.CheckConstraint("phase IS NULL OR phase IN ('classifier','query_embedding','generation')", name='ck_leny_inference_phase'),
        sa.CheckConstraint("(state = 'idle' AND request_id IS NULL AND model IS NULL AND phase IS NULL) OR "
            "(state IN ('inflight','uncertain') AND request_id IS NOT NULL AND model IS NOT NULL AND "
            "length(trim(model)) BETWEEN 1 AND 120 AND phase IS NOT NULL)", name='ck_leny_inference_metadata'), schema='leny')
    op.execute("INSERT INTO leny.inferencia_estado(id,state) VALUES(1,'idle')")


def downgrade():
    # A reviewable fail-closed downgrade: never silently erase publication,
    # conversation provenance or an unresolved provider call.
    op.execute("""DO $guard$ BEGIN
      IF EXISTS(SELECT 1 FROM leny.documentos WHERE published_version_id IS NOT NULL)
         OR EXISTS(SELECT 1 FROM leny.rag_fuentes_mensaje)
         OR EXISTS(SELECT 1 FROM leny.inferencia_estado WHERE state <> 'idle') THEN
        RAISE EXCEPTION '0021 downgrade requires no publications, sources or pending inference';
      END IF;
    END $guard$""")
    op.drop_table('inferencia_estado', schema='leny')
    op.drop_table('rag_fuentes_mensaje', schema='leny')
    op.create_check_constraint('ck_leny_document_unpublished_stage01', 'documentos', 'published_version_id IS NULL', schema='leny')
    op.drop_constraint('ck_leny_document_publication_active', 'documentos', type_='check', schema='leny')
    op.drop_constraint('ck_leny_document_publication_metadata', 'documentos', type_='check', schema='leny')
    op.drop_constraint('fk_leny_document_published_indexation', 'documentos', type_='foreignkey', schema='leny')
    op.drop_constraint('fk_leny_document_published_actor', 'documentos', type_='foreignkey', schema='leny')
    for name in ('published_indexation_status', 'published_by', 'published_at', 'published_indexation_id'):
        op.drop_column('documentos', name, schema='leny')
    op.drop_constraint('uq_leny_rag_indexation_publication_state', 'rag_indexaciones', type_='unique', schema='leny')
