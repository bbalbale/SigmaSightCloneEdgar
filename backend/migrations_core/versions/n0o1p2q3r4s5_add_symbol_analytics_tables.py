"""add_symbol_analytics_tables

Revision ID: n0o1p2q3r4s5
Revises: m9n0o1p2q3r4
Create Date: 2025-12-20 12:00:00.000000

Symbol Factor Universe Architecture - Phase 1: Database Schema

Creates three new tables for symbol-level analytics:
1. symbol_universe - Master list of all symbols
2. symbol_factor_exposures - Per-symbol factor betas (Ridge + Spread)
3. symbol_daily_metrics - Denormalized dashboard data

These tables enable:
- Factor calculations done once per symbol (not per position)
- Symbol Dashboard page with sorting/filtering
- Symbol returns as single source of truth for P&L
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'n0o1p2q3r4s5'
down_revision = 'f8g9h0i1j2k3'  # Current Railway version (AI insights tables)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create symbol_universe table (master list of symbols)
    op.create_table(
        'symbol_universe',
        sa.Column('symbol', sa.String(20), primary_key=True),
        sa.Column('asset_type', sa.String(20), nullable=True),  # 'equity', 'etf', 'option_underlying'
        sa.Column('sector', sa.String(100), nullable=True),
        sa.Column('industry', sa.String(100), nullable=True),
        sa.Column('first_seen_date', sa.Date(), nullable=True),
        sa.Column('last_seen_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Indexes for symbol_universe
    op.create_index('idx_symbol_universe_active', 'symbol_universe', ['is_active'])
    op.create_index('idx_symbol_universe_sector', 'symbol_universe', ['sector'])
    op.create_index('idx_symbol_universe_asset_type', 'symbol_universe', ['asset_type'])

    print("Created table: symbol_universe")

    # 2. Create symbol_factor_exposures table (per-symbol factor betas)
    op.create_table(
        'symbol_factor_exposures',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('symbol', sa.String(20), sa.ForeignKey('symbol_universe.symbol', ondelete='CASCADE'), nullable=False),
        sa.Column('factor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('factor_definitions.id'), nullable=False),
        sa.Column('calculation_date', sa.Date(), nullable=False),
        # Regression results
        sa.Column('beta_value', sa.Numeric(10, 6), nullable=False),
        sa.Column('r_squared', sa.Numeric(6, 4), nullable=True),
        sa.Column('observations', sa.Integer(), nullable=True),
        sa.Column('quality_flag', sa.String(20), nullable=True),  # 'full_history', 'limited_history'
        # Calculation metadata
        sa.Column('calculation_method', sa.String(50), nullable=False),  # 'ridge_regression', 'spread_regression'
        sa.Column('regularization_alpha', sa.Numeric(6, 4), nullable=True),  # Only for ridge
        sa.Column('regression_window_days', sa.Integer(), nullable=True),  # 365 for ridge, 180 for spread
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Unique constraint for upsert pattern
    op.create_unique_constraint('uq_symbol_factor_date', 'symbol_factor_exposures', ['symbol', 'factor_id', 'calculation_date'])

    # Indexes for symbol_factor_exposures
    op.create_index('idx_symbol_factor_lookup', 'symbol_factor_exposures', ['symbol', 'calculation_date'])
    op.create_index('idx_symbol_factor_calc_date', 'symbol_factor_exposures', ['calculation_date'])
    op.create_index('idx_symbol_factor_method', 'symbol_factor_exposures', ['calculation_method', 'calculation_date'])

    print("Created table: symbol_factor_exposures")

    # 3. Create symbol_daily_metrics table (denormalized dashboard data)
    op.create_table(
        'symbol_daily_metrics',
        sa.Column('symbol', sa.String(20), sa.ForeignKey('symbol_universe.symbol', ondelete='CASCADE'), primary_key=True),
        sa.Column('metrics_date', sa.Date(), nullable=False),
        # Price & Returns
        sa.Column('current_price', sa.Numeric(12, 4), nullable=True),
        sa.Column('return_1d', sa.Numeric(10, 6), nullable=True),
        sa.Column('return_mtd', sa.Numeric(10, 6), nullable=True),
        sa.Column('return_ytd', sa.Numeric(10, 6), nullable=True),
        sa.Column('return_1m', sa.Numeric(10, 6), nullable=True),
        sa.Column('return_3m', sa.Numeric(10, 6), nullable=True),
        sa.Column('return_1y', sa.Numeric(10, 6), nullable=True),
        # Valuation
        sa.Column('market_cap', sa.Numeric(18, 2), nullable=True),
        sa.Column('enterprise_value', sa.Numeric(18, 2), nullable=True),
        sa.Column('pe_ratio', sa.Numeric(10, 4), nullable=True),
        sa.Column('ps_ratio', sa.Numeric(10, 4), nullable=True),
        sa.Column('pb_ratio', sa.Numeric(10, 4), nullable=True),
        # Company Info
        sa.Column('sector', sa.String(100), nullable=True),
        sa.Column('industry', sa.String(100), nullable=True),
        sa.Column('company_name', sa.String(255), nullable=True),
        # Ridge Factors
        sa.Column('factor_value', sa.Numeric(10, 6), nullable=True),
        sa.Column('factor_growth', sa.Numeric(10, 6), nullable=True),
        sa.Column('factor_momentum', sa.Numeric(10, 6), nullable=True),
        sa.Column('factor_quality', sa.Numeric(10, 6), nullable=True),
        sa.Column('factor_size', sa.Numeric(10, 6), nullable=True),
        sa.Column('factor_low_vol', sa.Numeric(10, 6), nullable=True),
        # Spread Factors
        sa.Column('factor_growth_value_spread', sa.Numeric(10, 6), nullable=True),
        sa.Column('factor_momentum_spread', sa.Numeric(10, 6), nullable=True),
        sa.Column('factor_size_spread', sa.Numeric(10, 6), nullable=True),
        sa.Column('factor_quality_spread', sa.Numeric(10, 6), nullable=True),
        # Metadata
        sa.Column('data_quality_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Indexes for symbol_daily_metrics (dashboard sorting)
    op.create_index('idx_metrics_date', 'symbol_daily_metrics', ['metrics_date'])
    op.create_index('idx_metrics_sector', 'symbol_daily_metrics', ['sector'])
    op.create_index('idx_metrics_market_cap', 'symbol_daily_metrics', ['market_cap'])
    op.create_index('idx_metrics_return_ytd', 'symbol_daily_metrics', ['return_ytd'])
    op.create_index('idx_metrics_pe', 'symbol_daily_metrics', ['pe_ratio'])
    op.create_index('idx_metrics_factor_momentum', 'symbol_daily_metrics', ['factor_momentum'])
    op.create_index('idx_metrics_factor_value', 'symbol_daily_metrics', ['factor_value'])
    op.create_index('idx_metrics_sector_cap', 'symbol_daily_metrics', ['sector', 'market_cap'])

    print("Created table: symbol_daily_metrics")
    print("\nSymbol analytics tables created successfully!")


def downgrade() -> None:
    # Drop tables in reverse order (due to foreign key dependencies)
    op.drop_table('symbol_daily_metrics')
    print("Dropped table: symbol_daily_metrics")

    op.drop_table('symbol_factor_exposures')
    print("Dropped table: symbol_factor_exposures")

    op.drop_table('symbol_universe')
    print("Dropped table: symbol_universe")

    print("\nSymbol analytics tables dropped successfully!")
