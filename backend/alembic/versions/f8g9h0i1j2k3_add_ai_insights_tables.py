"""add ai insights and templates tables for analytical reasoning layer

Revision ID: f8g9h0i1j2k3
Revises: e65741f182c4
Create Date: 2025-10-19 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f8g9h0i1j2k3'
down_revision: Union[str, Sequence[str], None] = 'e65741f182c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create ai_insights and ai_insight_templates tables for the Analytical Reasoning Layer.

    ai_insights: Stores AI-generated portfolio analysis and investigations
    ai_insight_templates: Stores versioned prompt templates for different insight types
    """

    # Note: ENUM types (insight_type, insight_severity, data_quality_level) are created automatically
    # by SQLAlchemy when the tables are created below. No manual creation needed.

    # Create ai_insights table
    op.create_table(
        'ai_insights',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('portfolio_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('portfolios.id'), nullable=False),

        # Insight metadata
        sa.Column('insight_type', sa.Enum('daily_summary', 'volatility_analysis', 'concentration_risk',
                                         'hedge_quality', 'factor_exposure', 'stress_test_review', 'custom',
                                         name='insight_type'), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('severity', sa.Enum('info', 'normal', 'elevated', 'warning', 'critical',
                                     name='insight_severity'), nullable=False),

        # Content
        sa.Column('summary', sa.Text, nullable=False),
        sa.Column('full_analysis', sa.Text, nullable=True),
        sa.Column('key_findings', postgresql.JSON, nullable=True),
        sa.Column('recommendations', postgresql.JSON, nullable=True),
        sa.Column('data_limitations', sa.Text, nullable=True),

        # Investigation context
        sa.Column('context_data', postgresql.JSON, nullable=True),
        sa.Column('data_quality', postgresql.JSON, nullable=True),
        sa.Column('focus_area', sa.String(100), nullable=True),
        sa.Column('user_question', sa.Text, nullable=True),

        # AI model information
        sa.Column('model_used', sa.String(50), nullable=False),
        sa.Column('provider', sa.String(20), nullable=False, server_default='anthropic'),
        sa.Column('prompt_version', sa.String(20), nullable=True),

        # Performance metrics
        sa.Column('cost_usd', sa.Numeric(10, 6), nullable=True),
        sa.Column('generation_time_ms', sa.Numeric(10, 2), nullable=True),
        sa.Column('token_count_input', sa.Numeric(10, 0), nullable=True),
        sa.Column('token_count_output', sa.Numeric(10, 0), nullable=True),
        sa.Column('tool_calls_count', sa.Numeric(3, 0), server_default='0'),

        # Caching
        sa.Column('cache_hit', sa.Boolean, server_default='false'),
        sa.Column('cache_source_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ai_insights.id'), nullable=True),
        sa.Column('cache_key', sa.String(64), nullable=True),

        # User interaction
        sa.Column('user_rating', sa.Numeric(2, 1), nullable=True),
        sa.Column('user_feedback', sa.Text, nullable=True),
        sa.Column('viewed', sa.Boolean, server_default='false'),
        sa.Column('dismissed', sa.Boolean, server_default='false'),

        # Timestamps
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
    )

    # Create indexes for ai_insights
    op.create_index('ix_ai_insights_portfolio_id', 'ai_insights', ['portfolio_id'])
    op.create_index('ix_ai_insights_insight_type', 'ai_insights', ['insight_type'])
    op.create_index('ix_ai_insights_created_at', 'ai_insights', ['created_at'])
    op.create_index('ix_ai_insights_cache_key', 'ai_insights', ['cache_key'])
    op.create_index('ix_ai_insights_portfolio_created', 'ai_insights', ['portfolio_id', 'created_at'])
    op.create_index('ix_ai_insights_type_severity', 'ai_insights', ['insight_type', 'severity'])
    op.create_index('ix_ai_insights_cache_lookup', 'ai_insights', ['cache_key', 'created_at'])

    # Create ai_insight_templates table
    op.create_table(
        'ai_insight_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),

        # Template metadata
        sa.Column('insight_type', sa.Enum('daily_summary', 'volatility_analysis', 'concentration_risk',
                                         'hedge_quality', 'factor_exposure', 'stress_test_review', 'custom',
                                         name='insight_type'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('version', sa.String(20), nullable=False),

        # Prompt templates
        sa.Column('system_prompt', sa.Text, nullable=False),
        sa.Column('investigation_prompt', sa.Text, nullable=False),

        # Configuration
        sa.Column('model_preference', sa.String(50), nullable=True),
        sa.Column('max_tokens', sa.Numeric(6, 0), nullable=True),
        sa.Column('temperature', sa.Numeric(3, 2), nullable=True),

        # Tools configuration
        sa.Column('required_tools', postgresql.JSON, nullable=True),
        sa.Column('optional_tools', postgresql.JSON, nullable=True),

        # Quality metrics
        sa.Column('active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('avg_quality_score', sa.Numeric(3, 2), nullable=True),
        sa.Column('usage_count', sa.Numeric(10, 0), server_default='0'),

        # Timestamps
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('deprecated_at', sa.DateTime, nullable=True),
    )

    # Create indexes for ai_insight_templates
    op.create_index('ix_ai_templates_insight_type', 'ai_insight_templates', ['insight_type'])
    op.create_index('ix_ai_templates_type_active', 'ai_insight_templates', ['insight_type', 'active'])
    op.create_index('ix_ai_templates_version', 'ai_insight_templates', ['insight_type', 'version'])


def downgrade() -> None:
    """
    Drop ai_insights and ai_insight_templates tables and their ENUM types.
    """

    # Drop indexes
    op.drop_index('ix_ai_templates_version', 'ai_insight_templates')
    op.drop_index('ix_ai_templates_type_active', 'ai_insight_templates')
    op.drop_index('ix_ai_templates_insight_type', 'ai_insight_templates')

    op.drop_index('ix_ai_insights_cache_lookup', 'ai_insights')
    op.drop_index('ix_ai_insights_type_severity', 'ai_insights')
    op.drop_index('ix_ai_insights_portfolio_created', 'ai_insights')
    op.drop_index('ix_ai_insights_cache_key', 'ai_insights')
    op.drop_index('ix_ai_insights_created_at', 'ai_insights')
    op.drop_index('ix_ai_insights_insight_type', 'ai_insights')
    op.drop_index('ix_ai_insights_portfolio_id', 'ai_insights')

    # Drop tables
    op.drop_table('ai_insight_templates')
    op.drop_table('ai_insights')

    # Drop ENUM types
    op.execute('DROP TYPE IF EXISTS data_quality_level')
    op.execute('DROP TYPE IF EXISTS insight_severity')
    op.execute('DROP TYPE IF EXISTS insight_type')
