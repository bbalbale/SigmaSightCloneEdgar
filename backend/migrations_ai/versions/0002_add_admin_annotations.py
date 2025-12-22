"""Add ai_admin_annotations table for AI tuning

Revision ID: 0002
Revises: 0001
Create Date: 2025-12-22

Creates the admin annotations table for AI tuning:
- ai_admin_annotations: Admin comments and corrections on AI responses

Part of Phase 2 Admin Dashboard implementation.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create ai_admin_annotations table."""

    # Create ai_admin_annotations table
    op.create_table(
        'ai_admin_annotations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('admin_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('annotation_type', sa.String(50), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('suggested_response', sa.Text, nullable=True),
        sa.Column('severity', sa.String(20), nullable=True),
        sa.Column('tags', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # Create indexes for efficient querying
    op.create_index('ix_ai_admin_annotations_message_id', 'ai_admin_annotations', ['message_id'])
    op.create_index('ix_ai_admin_annotations_admin_user_id', 'ai_admin_annotations', ['admin_user_id'])
    op.create_index('ix_ai_admin_annotations_type', 'ai_admin_annotations', ['annotation_type'])
    op.create_index('ix_ai_admin_annotations_status', 'ai_admin_annotations', ['status'])
    op.create_index('ix_ai_admin_annotations_severity', 'ai_admin_annotations', ['severity'])
    op.create_index('ix_ai_admin_annotations_created', 'ai_admin_annotations', ['created_at'])


def downgrade() -> None:
    """Drop ai_admin_annotations table."""
    op.drop_table('ai_admin_annotations')
