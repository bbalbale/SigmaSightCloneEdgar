# 03: Database Schema Changes

## Design Principle: Reuse Existing Tables

**We have existing tables that already serve most of our needs.** The V2 architecture reuses them rather than creating duplicates.

---

## Existing Tables We'll Reuse

### `market_data_cache` (Existing - No Changes)

Already stores symbol prices with all needed fields:

```python
class MarketDataCache(Base):
    __tablename__ = "market_data_cache"

    symbol: str          # "AAPL"
    date: date           # 2025-01-10
    open: Decimal        # Open price
    high: Decimal        # High price
    low: Decimal         # Low price
    close: Decimal       # Close price (used for snapshots)
    volume: int          # Trading volume
    sector: str          # "Technology"
    industry: str        # "Consumer Electronics"
    data_source: str     # "yfinance"
```

**V2 Usage**: Symbol batch will upsert prices here. Portfolio refresh reads from here.

---

### `symbol_universe` (Existing - Minor Additions)

Already tracks all symbols with lifecycle info:

```python
class SymbolUniverse(Base):
    __tablename__ = "symbol_universe"

    symbol: str          # Primary key "AAPL"
    asset_type: str      # "equity", "etf", "option_underlying"
    sector: str          # "Technology"
    industry: str        # "Consumer Electronics"
    first_seen_date: date
    last_seen_date: date
    is_active: bool      # True = active, False = delisted/error
```

**V2 Additions** (via Alembic migration):
```sql
-- Track what added this symbol
ALTER TABLE symbol_universe ADD COLUMN added_source VARCHAR(50);
-- Values: 'seed', 'onboarding', 'admin', 'batch'

-- Track last successful data dates (for freshness monitoring)
ALTER TABLE symbol_universe ADD COLUMN last_price_date DATE;
ALTER TABLE symbol_universe ADD COLUMN last_factor_date DATE;
```

---

### `symbol_factor_exposures` (Existing - No Changes)

Already stores per-symbol factor betas:

```python
class SymbolFactorExposure(Base):
    __tablename__ = "symbol_factor_exposures"

    id: UUID
    symbol: str                    # FK to symbol_universe
    factor_id: UUID                # FK to factor_definitions
    calculation_date: date
    beta_value: Decimal            # The factor beta
    r_squared: Decimal             # Regression R²
    observations: int              # Sample size
    calculation_method: str        # "ridge_regression" or "spread_regression"
```

**V2 Usage**: Symbol batch updates this daily. No schema changes needed.

---

### `symbol_daily_metrics` (Existing - No Changes)

Denormalized dashboard data, already populated:

```python
class SymbolDailyMetrics(Base):
    __tablename__ = "symbol_daily_metrics"

    symbol: str          # Primary key
    metrics_date: date
    current_price: Decimal
    return_1d, return_mtd, return_ytd: Decimal
    market_cap, pe_ratio, ps_ratio: Decimal
    sector, industry, company_name: str
    factor_value, factor_growth, factor_momentum, ...: Decimal
```

**V2 Usage**: Updated in Phase 6 of symbol batch.

---

## New Tables

### `symbol_onboarding_queue` (NEW)

Async job queue for new symbol processing during user onboarding.

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

-- Prevent duplicate pending/processing jobs for same symbol
CREATE UNIQUE INDEX idx_queue_pending_symbol ON symbol_onboarding_queue(symbol)
    WHERE status IN ('pending', 'processing');
```

---

## Tables NOT Needed (Removed from Original Plan)

| Proposed Table | Why Not Needed |
|---------------|----------------|
| `symbol_prices_daily` | `market_data_cache` already has this data |
| `symbol_factor_exposures` (new) | Already exists in `symbol_analytics.py` |
| `portfolio_analytics_cache` | Using in-memory cache instead (~65MB) |

---

## Migration Plan

**Single Migration File**:

```python
# migrations_core/versions/xxx_add_v2_batch_tables.py

def upgrade():
    # 1. Create symbol_onboarding_queue (NEW)
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

    # 2. Add tracking columns to symbol_universe
    op.add_column('symbol_universe', sa.Column('added_source', sa.String(50)))
    op.add_column('symbol_universe', sa.Column('last_price_date', sa.Date))
    op.add_column('symbol_universe', sa.Column('last_factor_date', sa.Date))

    # 3. Create indexes
    op.create_index('idx_queue_status', 'symbol_onboarding_queue', ['status', 'priority', 'created_at'])


def downgrade():
    op.drop_table('symbol_onboarding_queue')
    op.drop_column('symbol_universe', 'added_source')
    op.drop_column('symbol_universe', 'last_price_date')
    op.drop_column('symbol_universe', 'last_factor_date')
```

---

## Model Definitions

Only one new model needed:

```python
# app/models/symbol_onboarding.py

from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from app.database import Base

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

---

## Query Patterns

### Get cached price for snapshot
```python
async def get_cached_price(symbol: str, target_date: date) -> Optional[Decimal]:
    """Get price from market_data_cache."""
    result = await db.execute(
        select(MarketDataCache.close)
        .where(
            MarketDataCache.symbol == symbol,
            MarketDataCache.date == target_date
        )
    )
    row = result.first()
    return row.close if row else None
```

### Get latest price date
```python
async def get_latest_price_date(db: AsyncSession) -> date:
    """Get the most recent date in market_data_cache."""
    result = await db.execute(
        select(func.max(MarketDataCache.date))
    )
    return result.scalar() or date.today()
```

### Upsert daily prices (symbol batch)
```python
async def bulk_upsert_prices(db: AsyncSession, prices: List[dict]) -> int:
    """Bulk upsert prices to market_data_cache."""
    from sqlalchemy.dialects.postgresql import insert

    stmt = insert(MarketDataCache).values(prices)
    stmt = stmt.on_conflict_do_update(
        index_elements=['symbol', 'date'],
        set_={
            'open': stmt.excluded.open,
            'high': stmt.excluded.high,
            'low': stmt.excluded.low,
            'close': stmt.excluded.close,
            'volume': stmt.excluded.volume,
            'data_source': stmt.excluded.data_source
        }
    )
    await db.execute(stmt)
    await db.commit()
    return len(prices)
```
