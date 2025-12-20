"""Add position correlation tables

Revision ID: 40680fc5a516
Revises: b5cd2cea0507
Create Date: 2025-08-05 06:43:35.524022

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '40680fc5a516'
down_revision: Union[str, Sequence[str], None] = 'b5cd2cea0507'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create correlation_calculations table
    op.create_table(
        'correlation_calculations',
        sa.Column('id', sa.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('portfolio_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('duration_days', sa.Integer(), nullable=False),
        sa.Column('calculation_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('overall_correlation', sa.DECIMAL(precision=8, scale=6), nullable=False),
        sa.Column('correlation_concentration_score', sa.DECIMAL(precision=8, scale=6), nullable=False),
        sa.Column('effective_positions', sa.DECIMAL(precision=8, scale=2), nullable=False),
        sa.Column('data_quality', sa.String(length=20), nullable=False),
        sa.Column('min_position_value', sa.DECIMAL(precision=18, scale=4), nullable=True),
        sa.Column('min_portfolio_weight', sa.DECIMAL(precision=8, scale=6), nullable=True),
        sa.Column('filter_mode', sa.String(length=20), server_default='both', nullable=True),
        sa.Column('correlation_threshold', sa.DECIMAL(precision=8, scale=6), server_default='0.7', nullable=True),
        sa.Column('positions_included', sa.Integer(), nullable=False),
        sa.Column('positions_excluded', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('portfolio_id', 'duration_days', 'calculation_date')
    )
    op.create_index('idx_correlation_calculations_portfolio_date', 'correlation_calculations', ['portfolio_id', 'calculation_date'], unique=False)
    
    # Create correlation_clusters table
    op.create_table(
        'correlation_clusters',
        sa.Column('id', sa.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('correlation_calculation_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('cluster_number', sa.Integer(), nullable=False),
        sa.Column('nickname', sa.String(length=100), nullable=False),
        sa.Column('avg_correlation', sa.DECIMAL(precision=8, scale=6), nullable=False),
        sa.Column('total_value', sa.DECIMAL(precision=18, scale=4), nullable=False),
        sa.Column('portfolio_percentage', sa.DECIMAL(precision=8, scale=6), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['correlation_calculation_id'], ['correlation_calculations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_correlation_clusters_calculation', 'correlation_clusters', ['correlation_calculation_id'], unique=False)
    
    # Create correlation_cluster_positions table
    op.create_table(
        'correlation_cluster_positions',
        sa.Column('id', sa.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('cluster_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('position_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('value', sa.DECIMAL(precision=18, scale=4), nullable=False),
        sa.Column('portfolio_percentage', sa.DECIMAL(precision=8, scale=6), nullable=False),
        sa.Column('correlation_to_cluster', sa.DECIMAL(precision=8, scale=6), nullable=False),
        sa.ForeignKeyConstraint(['cluster_id'], ['correlation_clusters.id'], ),
        sa.ForeignKeyConstraint(['position_id'], ['positions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_cluster_positions_cluster', 'correlation_cluster_positions', ['cluster_id'], unique=False)
    op.create_index('idx_cluster_positions_position', 'correlation_cluster_positions', ['position_id'], unique=False)
    
    # Create pairwise_correlations table
    op.create_table(
        'pairwise_correlations',
        sa.Column('id', sa.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('correlation_calculation_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('symbol_1', sa.String(length=20), nullable=False),
        sa.Column('symbol_2', sa.String(length=20), nullable=False),
        sa.Column('correlation_value', sa.DECIMAL(precision=8, scale=6), nullable=False),
        sa.Column('data_points', sa.Integer(), nullable=False),
        sa.Column('statistical_significance', sa.DECIMAL(precision=8, scale=6), nullable=True),
        sa.ForeignKeyConstraint(['correlation_calculation_id'], ['correlation_calculations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_pairwise_correlations_calculation', 'pairwise_correlations', ['correlation_calculation_id'], unique=False)
    op.create_index('idx_pairwise_correlations_calculation_symbols', 'pairwise_correlations', ['correlation_calculation_id', 'symbol_1', 'symbol_2'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('idx_pairwise_correlations_calculation_symbols', table_name='pairwise_correlations')
    op.drop_index('idx_pairwise_correlations_calculation', table_name='pairwise_correlations')
    op.drop_index('idx_cluster_positions_position', table_name='correlation_cluster_positions')
    op.drop_index('idx_cluster_positions_cluster', table_name='correlation_cluster_positions')
    op.drop_index('idx_correlation_clusters_calculation', table_name='correlation_clusters')
    op.drop_index('idx_correlation_calculations_portfolio_date', table_name='correlation_calculations')
    
    # Drop tables
    op.drop_table('pairwise_correlations')
    op.drop_table('correlation_cluster_positions')
    op.drop_table('correlation_clusters')
    op.drop_table('correlation_calculations')
