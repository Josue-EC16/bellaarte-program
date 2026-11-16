"""Persist an immutable LENY quality profile; historical chats stay baseline.

Only schema leny is changed. Applying this migration is an explicit operation,
never an application startup action.
"""
from alembic import op
import sqlalchemy as sa

revision = '20261105_0025'
down_revision = '20261105_0024'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('conversaciones', sa.Column('quality_profile', sa.String(16),
        nullable=False, server_default='baseline'), schema='leny')
    op.create_check_constraint('ck_leny_conversation_quality_profile', 'conversaciones',
        "quality_profile IN ('baseline','spec03')", schema='leny')


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT EXISTS(SELECT 1 FROM leny.conversaciones WHERE quality_profile='spec03')")):
        raise RuntimeError('SPEC03 conversations must retain their profile; use operational rollback instead.')
    op.drop_constraint('ck_leny_conversation_quality_profile', 'conversaciones', schema='leny', type_='check')
    op.drop_column('conversaciones', 'quality_profile', schema='leny')
