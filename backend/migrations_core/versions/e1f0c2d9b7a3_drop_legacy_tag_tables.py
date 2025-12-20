"""drop_legacy_tag_tables

Revision ID: e1f0c2d9b7a3
Revises: c9c0e8d2a7a1
Create Date: 2025-09-24 11:55:00.000000

Drops legacy tags + position_tags tables now that strategy_tags + TagV2 are in place.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f0c2d9b7a3'
down_revision: Union[str, Sequence[str], None] = 'c9c0e8d2a7a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if 'position_tags' in tables:
        op.drop_table('position_tags')

    if 'tags' in tables:
        op.drop_table('tags')


def downgrade() -> None:
    # Recreate legacy tables (minimal schema for downgrade compatibility)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if 'tags' not in tables:
        op.create_table(
            'tags',
            sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
            sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('name', sa.String(50), nullable=False),
            sa.Column('tag_type', sa.String(50), nullable=False, server_default='REGULAR'),
            sa.Column('description', sa.String(255), nullable=True),
            sa.Column('color', sa.String(7), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index('ix_tags_user_id_name', 'tags', ['user_id', 'name'], unique=True)
        op.create_index('ix_tags_tag_type', 'tags', ['tag_type'])

    if 'position_tags' not in tables:
        op.create_table(
            'position_tags',
            sa.Column('position_id', sa.UUID(), sa.ForeignKey('positions.id'), primary_key=True, nullable=False),
            sa.Column('tag_id', sa.UUID(), sa.ForeignKey('tags.id'), primary_key=True, nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index('ix_position_tags_position_id_tag_id', 'position_tags', ['position_id', 'tag_id'])

