"""add staff moderation fields

Revision ID: 002_staff_moderation
Revises: 001_cover_image
Create Date: 2026-04-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '002_staff_moderation'
down_revision = '001_cover_image'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Agent: role field
    op.add_column('agents', sa.Column('role', sa.String(20), server_default='author', nullable=False))

    # Article: moderation fields
    op.add_column('articles', sa.Column('moderation_status', sa.String(20), server_default='pending', nullable=False))
    op.add_column('articles', sa.Column('moderation_note', sa.Text(), nullable=True))
    op.add_column('articles', sa.Column('reviewed_by', UUID(as_uuid=True), nullable=True))
    op.add_column('articles', sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key('fk_articles_reviewed_by', 'articles', 'agents', ['reviewed_by'], ['id'])

    # Comment: soft delete fields
    op.add_column('comments', sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('comments', sa.Column('deleted_reason', sa.String(500), nullable=True))
    op.add_column('comments', sa.Column('deleted_by', UUID(as_uuid=True), nullable=True))
    op.add_column('comments', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key('fk_comments_deleted_by', 'comments', 'agents', ['deleted_by'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_comments_deleted_by', 'comments', type_='foreignkey')
    op.drop_column('comments', 'deleted_at')
    op.drop_column('comments', 'deleted_by')
    op.drop_column('comments', 'deleted_reason')
    op.drop_column('comments', 'is_deleted')

    op.drop_constraint('fk_articles_reviewed_by', 'articles', type_='foreignkey')
    op.drop_column('articles', 'reviewed_at')
    op.drop_column('articles', 'reviewed_by')
    op.drop_column('articles', 'moderation_note')
    op.drop_column('articles', 'moderation_status')

    op.drop_column('agents', 'role')
