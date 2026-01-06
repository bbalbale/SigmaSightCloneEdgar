"""Add Clerk auth columns to users table

Revision ID: d5e6f7g8h9i0
Revises: c4724714f341
Create Date: 2026-01-06

Phase 2: Clerk Authentication & Billing
Adds columns for Clerk user ID, subscription tier, invite validation, and AI usage tracking.

Note: This migration is recreated from AuthOnboarding with correct base revision.
Original revision was s5t6u7v8w9x0, which depended on AuthOnboarding's merge migration.
This version depends on main's merge migration (c4724714f341).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5e6f7g8h9i0'
down_revision = 'c4724714f341'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add Clerk authentication columns to users table
    op.add_column('users', sa.Column('clerk_user_id', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('tier', sa.String(20), server_default='free', nullable=False))
    op.add_column('users', sa.Column('invite_validated', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('users', sa.Column('ai_messages_used', sa.Integer(), server_default='0', nullable=False))
    op.add_column('users', sa.Column('ai_messages_reset_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))

    # Add unique index on clerk_user_id for fast lookups
    op.create_index('ix_users_clerk_user_id', 'users', ['clerk_user_id'], unique=True)


def downgrade() -> None:
    # Remove index
    op.drop_index('ix_users_clerk_user_id', table_name='users')

    # Remove columns
    op.drop_column('users', 'ai_messages_reset_at')
    op.drop_column('users', 'ai_messages_used')
    op.drop_column('users', 'invite_validated')
    op.drop_column('users', 'tier')
    op.drop_column('users', 'clerk_user_id')
