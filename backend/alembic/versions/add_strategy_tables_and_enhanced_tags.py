"""add_strategy_tables_and_enhanced_tags

Revision ID: add_strategies_001
Revises: 1dafe8c1dd84
Create Date: 2025-09-24 10:00:00.000000

This migration adds the complete strategy system and enhanced tag tables.
Strategies are containers for positions, with every position belonging to exactly one strategy.
Tags are user-scoped organizational metadata that can be applied to strategies.

CONDITIONAL MIGRATION: This migration now includes guards to handle cases where tables/
columns/indexes already exist (e.g., from migration 001's consolidated schema).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'add_strategies_001'
down_revision: Union[str, Sequence[str], None] = '1dafe8c1dd84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add strategy tables and enhanced tag system (with conditional guards)."""

    # Get connection and inspector to check existing schema
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()

    # Create strategies table (if not exists)
    if 'strategies' not in existing_tables:
        op.create_table('strategies',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('portfolio_id', sa.UUID(), nullable=False),
            sa.Column('strategy_type', sa.String(50), nullable=False, server_default='standalone'),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('net_exposure', sa.Numeric(20, 2), nullable=True),
            sa.Column('total_cost_basis', sa.Numeric(20, 2), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_by', sa.UUID(), nullable=True),
            sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['created_by'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.CheckConstraint(
                "strategy_type IN ('standalone', 'covered_call', 'protective_put', 'iron_condor', 'straddle', 'strangle', 'butterfly', 'pairs_trade', 'custom')",
                name='valid_strategy_type'
            )
        )
        op.create_index('idx_strategies_portfolio', 'strategies', ['portfolio_id'])
        op.create_index('idx_strategies_type', 'strategies', ['strategy_type'])
        op.create_index('idx_strategies_synthetic', 'strategies', ['is_synthetic'])

    # Add strategy_id to positions table (if column doesn't exist)
    if 'positions' in existing_tables:
        positions_columns = [col['name'] for col in inspector.get_columns('positions')]
        if 'strategy_id' not in positions_columns:
            op.add_column('positions',
                sa.Column('strategy_id', sa.UUID(), nullable=True)
            )
            op.create_foreign_key(
                'fk_positions_strategy',
                'positions', 'strategies',
                ['strategy_id'], ['id'],
                ondelete='RESTRICT'
            )
            op.create_index('idx_positions_strategy', 'positions', ['strategy_id'])

    # Create strategy_legs junction table (if not exists)
    if 'strategy_legs' not in existing_tables:
        op.create_table('strategy_legs',
            sa.Column('strategy_id', sa.UUID(), nullable=False),
            sa.Column('position_id', sa.UUID(), nullable=False),
            sa.Column('leg_type', sa.String(50), nullable=False, server_default='single'),
            sa.Column('leg_order', sa.Integer(), nullable=False, server_default='0'),
            sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['position_id'], ['positions.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('strategy_id', 'position_id')
        )
        op.create_index('idx_strategy_legs_position', 'strategy_legs', ['position_id'])

    # Create enhanced tags table (if not exists)
    if 'tags_v2' not in existing_tables:
        op.create_table('tags_v2',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('user_id', sa.UUID(), nullable=False),
            sa.Column('name', sa.String(50), nullable=False),
            sa.Column('color', sa.String(7), nullable=True, server_default='#4A90E2'),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('archived_by', sa.UUID(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['archived_by'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'name', 'is_archived', name='unique_active_tag_name_v2'),
            sa.CheckConstraint("color ~ '^#[0-9A-Fa-f]{6}$'", name='valid_hex_color')
        )
        op.create_index('idx_tags_v2_user_active', 'tags_v2', ['user_id'],
                        postgresql_where=sa.text('is_archived = false'))
        op.create_index('idx_tags_v2_display_order', 'tags_v2', ['user_id', 'display_order'])

    # Create strategy_tags junction table (if not exists)
    if 'strategy_tags' not in existing_tables:
        op.create_table('strategy_tags',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('strategy_id', sa.UUID(), nullable=False),
            sa.Column('tag_id', sa.UUID(), nullable=False),
            sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('assigned_by', sa.UUID(), nullable=True),
            sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['tag_id'], ['tags_v2.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['assigned_by'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('strategy_id', 'tag_id', name='unique_strategy_tag')
        )
        op.create_index('idx_strategy_tags_strategy', 'strategy_tags', ['strategy_id'])
        op.create_index('idx_strategy_tags_tag', 'strategy_tags', ['tag_id'])

    # Create strategy_metrics table (if not exists)
    if 'strategy_metrics' not in existing_tables:
        op.create_table('strategy_metrics',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('strategy_id', sa.UUID(), nullable=False),
            sa.Column('calculation_date', sa.Date(), nullable=False),
            sa.Column('net_delta', sa.Numeric(10, 4), nullable=True),
            sa.Column('net_gamma', sa.Numeric(10, 6), nullable=True),
            sa.Column('net_theta', sa.Numeric(20, 2), nullable=True),
            sa.Column('net_vega', sa.Numeric(20, 2), nullable=True),
            sa.Column('total_pnl', sa.Numeric(20, 2), nullable=True),
            sa.Column('max_profit', sa.Numeric(20, 2), nullable=True),
            sa.Column('max_loss', sa.Numeric(20, 2), nullable=True),
            sa.Column('break_even_points', postgresql.JSONB(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('strategy_id', 'calculation_date', name='unique_strategy_date')
        )
        op.create_index('idx_strategy_metrics_strategy', 'strategy_metrics', ['strategy_id'])
        op.create_index('idx_strategy_metrics_date', 'strategy_metrics', ['calculation_date'])


def downgrade() -> None:
    """Remove strategy tables and enhanced tag system (with conditional guards)."""

    # Get connection and inspector to check existing schema
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()

    # Drop strategy_metrics table (if exists)
    if 'strategy_metrics' in existing_tables:
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('strategy_metrics')]
        if 'idx_strategy_metrics_date' in existing_indexes:
            op.drop_index('idx_strategy_metrics_date', 'strategy_metrics')
        if 'idx_strategy_metrics_strategy' in existing_indexes:
            op.drop_index('idx_strategy_metrics_strategy', 'strategy_metrics')
        op.drop_table('strategy_metrics')

    # Drop strategy_tags table (if exists)
    if 'strategy_tags' in existing_tables:
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('strategy_tags')]
        if 'idx_strategy_tags_tag' in existing_indexes:
            op.drop_index('idx_strategy_tags_tag', 'strategy_tags')
        if 'idx_strategy_tags_strategy' in existing_indexes:
            op.drop_index('idx_strategy_tags_strategy', 'strategy_tags')
        op.drop_table('strategy_tags')

    # Drop tags_v2 table (if exists)
    if 'tags_v2' in existing_tables:
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('tags_v2')]
        if 'idx_tags_v2_display_order' in existing_indexes:
            op.drop_index('idx_tags_v2_display_order', 'tags_v2')
        if 'idx_tags_v2_user_active' in existing_indexes:
            op.drop_index('idx_tags_v2_user_active', 'tags_v2')
        op.drop_table('tags_v2')

    # Drop strategy_legs table (if exists)
    if 'strategy_legs' in existing_tables:
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('strategy_legs')]
        if 'idx_strategy_legs_position' in existing_indexes:
            op.drop_index('idx_strategy_legs_position', 'strategy_legs')
        op.drop_table('strategy_legs')

    # Remove strategy_id from positions (if exists)
    if 'positions' in existing_tables:
        positions_columns = [col['name'] for col in inspector.get_columns('positions')]
        if 'strategy_id' in positions_columns:
            # Check if FK constraint exists
            existing_fks = [fk['name'] for fk in inspector.get_foreign_keys('positions')]
            if 'fk_positions_strategy' in existing_fks:
                op.drop_constraint('fk_positions_strategy', 'positions', type_='foreignkey')

            # Check if index exists
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('positions')]
            if 'idx_positions_strategy' in existing_indexes:
                op.drop_index('idx_positions_strategy', 'positions')

            op.drop_column('positions', 'strategy_id')

    # Drop strategies table (if exists)
    if 'strategies' in existing_tables:
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('strategies')]
        if 'idx_strategies_synthetic' in existing_indexes:
            op.drop_index('idx_strategies_synthetic', 'strategies')
        if 'idx_strategies_type' in existing_indexes:
            op.drop_index('idx_strategies_type', 'strategies')
        if 'idx_strategies_portfolio' in existing_indexes:
            op.drop_index('idx_strategies_portfolio', 'strategies')
        op.drop_table('strategies')
