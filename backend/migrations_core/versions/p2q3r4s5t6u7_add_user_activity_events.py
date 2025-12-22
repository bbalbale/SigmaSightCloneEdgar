"""add_user_activity_events

Revision ID: p2q3r4s5t6u7
Revises: o1p2q3r4s5t6
Create Date: 2025-12-22 16:00:00.000000

Admin Dashboard Phase 3: User Activity Tracking

Creates user_activity_events table for onboarding funnel tracking:
- Tracks registration, login, portfolio creation events
- Records errors with error_code for debugging
- Supports session tracking for pre/post auth correlation
- 30-day data retention (aggregated to daily_metrics later)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'p2q3r4s5t6u7'
down_revision = 'o1p2q3r4s5t6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_activity_events table
    op.create_table(
        'user_activity_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_id', sa.String(255), nullable=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('event_category', sa.String(50), nullable=False),
        sa.Column('event_data', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('error_code', sa.String(50), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # Create indexes for efficient querying
    op.create_index('ix_user_activity_events_user_id', 'user_activity_events', ['user_id'])
    op.create_index('ix_user_activity_events_session_id', 'user_activity_events', ['session_id'])
    op.create_index('ix_user_activity_events_event_type', 'user_activity_events', ['event_type'])
    op.create_index('ix_user_activity_events_event_category', 'user_activity_events', ['event_category'])
    op.create_index('ix_user_activity_events_error_code', 'user_activity_events', ['error_code'])
    op.create_index('ix_user_activity_events_created_at', 'user_activity_events', ['created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_user_activity_events_created_at', table_name='user_activity_events')
    op.drop_index('ix_user_activity_events_error_code', table_name='user_activity_events')
    op.drop_index('ix_user_activity_events_event_category', table_name='user_activity_events')
    op.drop_index('ix_user_activity_events_event_type', table_name='user_activity_events')
    op.drop_index('ix_user_activity_events_session_id', table_name='user_activity_events')
    op.drop_index('ix_user_activity_events_user_id', table_name='user_activity_events')

    # Drop table
    op.drop_table('user_activity_events')
