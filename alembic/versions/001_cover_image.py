"""add cover_image to articles

Revision ID: 001_cover_image
Revises: 
Create Date: 2026-04-08

"""
from alembic import op
import sqlalchemy as sa

revision = '001_cover_image'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('articles', sa.Column('cover_image', sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column('articles', 'cover_image')
