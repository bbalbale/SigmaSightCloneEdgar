"""Add ai_request_metrics table for AI performance tracking

Revision ID: q3r4s5t6u7v8
Revises: p2q3r4s5t6u7
Create Date: 2025-12-22

Phase 4: AI Performance Metrics (Admin Dashboard)
- Tracks token usage (input, output, total)
- Tracks latency (time to first token, total response time)
- Tracks tool usage
- Tracks errors
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'q3r4s5t6u7v8'
down_revision = 'p2q3r4s5t6u7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ai_request_metrics table
    op.create_table(
        'ai_request_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),

        # Request identification
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Model information
        sa.Column('model', sa.String(100), nullable=False),

        # Token usage
        sa.Column('input_tokens', sa.Integer, nullable=True),
        sa.Column('output_tokens', sa.Integer, nullable=True),
        sa.Column('total_tokens', sa.Integer, nullable=True),

        # Latency metrics (milliseconds)
        sa.Column('first_token_ms', sa.Integer, nullable=True),
        sa.Column('total_latency_ms', sa.Integer, nullable=True),

        # Tool usage
        sa.Column('tool_calls_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('tool_calls', postgresql.JSONB, nullable=True),

        # Error tracking
        sa.Column('error_type', sa.String(100), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),

        # Timestamp
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # Create indexes for efficient querying
    op.create_index('ix_ai_request_metrics_conversation_id', 'ai_request_metrics', ['conversation_id'])
    op.create_index('ix_ai_request_metrics_message_id', 'ai_request_metrics', ['message_id'])
    op.create_index('ix_ai_request_metrics_user_id', 'ai_request_metrics', ['user_id'])
    op.create_index('ix_ai_request_metrics_model', 'ai_request_metrics', ['model'])
    op.create_index('ix_ai_request_metrics_error_type', 'ai_request_metrics', ['error_type'])
    op.create_index('ix_ai_request_metrics_created_at', 'ai_request_metrics', ['created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_ai_request_metrics_created_at', table_name='ai_request_metrics')
    op.drop_index('ix_ai_request_metrics_error_type', table_name='ai_request_metrics')
    op.drop_index('ix_ai_request_metrics_model', table_name='ai_request_metrics')
    op.drop_index('ix_ai_request_metrics_user_id', table_name='ai_request_metrics')
    op.drop_index('ix_ai_request_metrics_message_id', table_name='ai_request_metrics')
    op.drop_index('ix_ai_request_metrics_conversation_id', table_name='ai_request_metrics')

    # Drop table
    op.drop_table('ai_request_metrics')
