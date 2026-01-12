# 03: Database Schema Changes

## New Tables

### `symbol_prices_daily`

Dedicated symbol price history (separate from position-level market data).

```sql
CREATE TABLE symbol_prices_daily (
    symbol VARCHAR(20) NOT NULL,
    price_date DATE NOT NULL,
    open_price DECIMAL(12, 4),
    high_price DECIMAL(12, 4),
    low_price DECIMAL(12, 4),
    close_price DECIMAL(12, 4) NOT NULL,
    adj_close_price DECIMAL(12, 4),
    volume BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    PRIMARY KEY (symbol, price_date),
    FOREIGN KEY (symbol) REFERENCES symbol_universe(symbol)
);

CREATE INDEX idx_symbol_prices_date ON symbol_prices_daily(price_date);
CREATE INDEX idx_symbol_prices_symbol ON symbol_prices_daily(symbol);
```

### `portfolio_analytics_cache`

Cached portfolio-level computations.

```sql
CREATE TABLE portfolio_analytics_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id),
    cache_key VARCHAR(255) NOT NULL,  -- hash of positions
    cache_type VARCHAR(50) NOT NULL,  -- 'factor_exposures', 'stress_test', etc.
    cached_data JSONB NOT NULL,
    valid_until TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (portfolio_id, cache_type, cache_key)
);

CREATE INDEX idx_cache_portfolio ON portfolio_analytics_cache(portfolio_id);
CREATE INDEX idx_cache_valid ON portfolio_analytics_cache(valid_until);
```

### `symbol_onboarding_queue`

Async job queue for new symbol processing.

```sql
CREATE TABLE symbol_onboarding_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed
    requested_by UUID REFERENCES users(id),
    priority VARCHAR(10) DEFAULT 'normal',  -- high, normal, low
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_queue_status ON symbol_onboarding_queue(status, priority, created_at);
CREATE UNIQUE INDEX idx_queue_pending_symbol ON symbol_onboarding_queue(symbol)
    WHERE status IN ('pending', 'processing');
```

---

## Schema Modifications

### `symbol_universe` - Add status tracking

```sql
ALTER TABLE symbol_universe ADD COLUMN status VARCHAR(20) DEFAULT 'active';
-- Values: 'pending', 'active', 'delisted', 'error'

ALTER TABLE symbol_universe ADD COLUMN last_price_date DATE;
ALTER TABLE symbol_universe ADD COLUMN last_factor_date DATE;
ALTER TABLE symbol_universe ADD COLUMN added_source VARCHAR(50);
-- Values: 'seed', 'onboarding', 'admin', 'batch'
```

### `symbol_factor_exposures` - Ensure all factors present

```sql
-- Verify these columns exist (should already be there)
-- market_beta, ir_beta
-- value_beta, growth_beta, momentum_beta, quality_beta, size_beta, low_vol_beta
-- growth_value_spread, momentum_spread, size_spread, quality_spread
```

---

## Migration Plan

**Week 1 Migration**:

```python
# migrations_core/versions/xxx_add_v2_batch_tables.py

def upgrade():
    # Create symbol_prices_daily
    op.create_table(
        'symbol_prices_daily',
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('price_date', sa.Date, nullable=False),
        sa.Column('open_price', sa.Numeric(12, 4)),
        sa.Column('high_price', sa.Numeric(12, 4)),
        sa.Column('low_price', sa.Numeric(12, 4)),
        sa.Column('close_price', sa.Numeric(12, 4), nullable=False),
        sa.Column('adj_close_price', sa.Numeric(12, 4)),
        sa.Column('volume', sa.BigInteger),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('symbol', 'price_date'),
        sa.ForeignKeyConstraint(['symbol'], ['symbol_universe.symbol'])
    )

    # Create portfolio_analytics_cache
    op.create_table(
        'portfolio_analytics_cache',
        sa.Column('id', sa.UUID, primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('portfolio_id', sa.UUID, sa.ForeignKey('portfolios.id'), nullable=False),
        sa.Column('cache_key', sa.String(255), nullable=False),
        sa.Column('cache_type', sa.String(50), nullable=False),
        sa.Column('cached_data', sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('portfolio_id', 'cache_type', 'cache_key')
    )

    # Create symbol_onboarding_queue
    op.create_table(
        'symbol_onboarding_queue',
        sa.Column('id', sa.UUID, primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('requested_by', sa.UUID, sa.ForeignKey('users.id')),
        sa.Column('priority', sa.String(10), server_default='normal'),
        sa.Column('error_message', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True))
    )

    # Add columns to symbol_universe
    op.add_column('symbol_universe', sa.Column('status', sa.String(20), server_default='active'))
    op.add_column('symbol_universe', sa.Column('last_price_date', sa.Date))
    op.add_column('symbol_universe', sa.Column('last_factor_date', sa.Date))
    op.add_column('symbol_universe', sa.Column('added_source', sa.String(50)))

    # Create indexes
    op.create_index('idx_symbol_prices_date', 'symbol_prices_daily', ['price_date'])
    op.create_index('idx_cache_portfolio', 'portfolio_analytics_cache', ['portfolio_id'])
    op.create_index('idx_cache_valid', 'portfolio_analytics_cache', ['valid_until'])
    op.create_index('idx_queue_status', 'symbol_onboarding_queue', ['status', 'priority', 'created_at'])


def downgrade():
    op.drop_table('symbol_onboarding_queue')
    op.drop_table('portfolio_analytics_cache')
    op.drop_table('symbol_prices_daily')
    op.drop_column('symbol_universe', 'status')
    op.drop_column('symbol_universe', 'last_price_date')
    op.drop_column('symbol_universe', 'last_factor_date')
    op.drop_column('symbol_universe', 'added_source')
```

---

## Data Migration

After schema migration, backfill `symbol_prices_daily` from existing `market_data_cache`:

```python
async def backfill_symbol_prices():
    """One-time migration of prices from market_data_cache to symbol_prices_daily."""

    async with AsyncSessionLocal() as db:
        # Get all unique symbols from market_data_cache
        symbols = await db.execute(
            select(MarketDataCache.symbol).distinct()
        )

        for symbol in symbols.scalars():
            # Get all prices for this symbol
            prices = await db.execute(
                select(MarketDataCache)
                .where(MarketDataCache.symbol == symbol)
                .order_by(MarketDataCache.date)
            )

            # Insert into symbol_prices_daily
            for price in prices.scalars():
                await db.execute(
                    insert(SymbolPricesDaily).values(
                        symbol=price.symbol,
                        price_date=price.date,
                        open_price=price.open,
                        high_price=price.high,
                        low_price=price.low,
                        close_price=price.close,
                        adj_close_price=price.adjusted_close,
                        volume=price.volume
                    ).on_conflict_do_nothing()
                )

        await db.commit()
```

---

## Model Definitions

```python
# app/models/symbol_prices.py

class SymbolPricesDaily(Base):
    __tablename__ = 'symbol_prices_daily'

    symbol = Column(String(20), ForeignKey('symbol_universe.symbol'), primary_key=True)
    price_date = Column(Date, primary_key=True)
    open_price = Column(Numeric(12, 4))
    high_price = Column(Numeric(12, 4))
    low_price = Column(Numeric(12, 4))
    close_price = Column(Numeric(12, 4), nullable=False)
    adj_close_price = Column(Numeric(12, 4))
    volume = Column(BigInteger)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# app/models/portfolio_cache.py

class PortfolioAnalyticsCache(Base):
    __tablename__ = 'portfolio_analytics_cache'

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey('portfolios.id'), nullable=False)
    cache_key = Column(String(255), nullable=False)
    cache_type = Column(String(50), nullable=False)
    cached_data = Column(JSONB, nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('portfolio_id', 'cache_type', 'cache_key'),
    )


# app/models/symbol_onboarding.py

class SymbolOnboardingQueue(Base):
    __tablename__ = 'symbol_onboarding_queue'

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    symbol = Column(String(20), nullable=False)
    status = Column(String(20), server_default='pending')
    requested_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    priority = Column(String(10), server_default='normal')
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
```
