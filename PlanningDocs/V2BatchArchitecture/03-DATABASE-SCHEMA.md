# 03: Database Schema Changes

## Design Principle: Zero New Tables, Zero Migrations

**V2 is a pure code change.** We reuse existing tables and query them directly instead of adding denormalized columns.

---

## Existing Tables We'll Reuse

### `market_data_cache` (No Changes)

Already stores symbol prices with all needed fields:

```python
class MarketDataCache(Base):
    __tablename__ = "market_data_cache"

    symbol: str          # "AAPL"
    date: date           # 2025-01-10
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal       # Used for snapshots
    volume: int
    sector: str
    industry: str
    data_source: str     # "yfinance"
```

**V2 Usage**: Symbol batch upserts prices here. Portfolio refresh reads from here.

---

### `symbol_universe` (No Changes)

Already tracks all symbols with lifecycle info:

```python
class SymbolUniverse(Base):
    __tablename__ = "symbol_universe"

    symbol: str          # Primary key "AAPL"
    asset_type: str      # "equity", "etf"
    sector: str
    industry: str
    first_seen_date: date
    last_seen_date: date
    is_active: bool      # True = active, False = delisted/error
```

**V2 Usage**: No schema changes. Query existing columns.

---

### `symbol_factor_exposures` (No Changes)

Already stores per-symbol factor betas:

```python
class SymbolFactorExposure(Base):
    __tablename__ = "symbol_factor_exposures"

    id: UUID
    symbol: str
    factor_id: UUID
    calculation_date: date
    beta_value: Decimal
    r_squared: Decimal
    calculation_method: str
```

**V2 Usage**: Symbol batch updates this daily. No schema changes.

---

### `symbol_daily_metrics` (No Changes)

Denormalized dashboard data:

```python
class SymbolDailyMetrics(Base):
    __tablename__ = "symbol_daily_metrics"

    symbol: str
    metrics_date: date
    current_price: Decimal
    return_1d, return_mtd, return_ytd: Decimal
    market_cap, pe_ratio: Decimal
    factor_value, factor_growth, factor_momentum: Decimal
```

**V2 Usage**: Updated in Phase 6 of symbol batch.

---

## Tables NOT Needed

| Proposed Table | Why Not Needed |
|---------------|----------------|
| `symbol_prices_daily` | `market_data_cache` already has this data |
| `symbol_factor_exposures` (new) | Already exists |
| `portfolio_analytics_cache` | Using in-memory cache (~65MB) |
| `symbol_onboarding_queue` | Using in-memory queue |

---

## Columns NOT Needed

Originally proposed adding to `symbol_universe`:
- `added_source` → Not critical, skip
- `last_price_date` → Query `market_data_cache` instead
- `last_factor_date` → Query `symbol_factor_exposures` instead

**Result: Zero migrations required.**

---

## Query Patterns (Instead of Denormalized Columns)

### Get latest price date for freshness monitoring
```python
async def get_latest_price_date(db: AsyncSession) -> date:
    """Query market_data_cache for latest date."""
    result = await db.execute(
        select(func.max(MarketDataCache.date))
    )
    return result.scalar() or date.today()
```

### Get latest factor date for freshness monitoring
```python
async def get_latest_factor_date(db: AsyncSession) -> date:
    """Query symbol_factor_exposures for latest date."""
    result = await db.execute(
        select(func.max(SymbolFactorExposure.calculation_date))
    )
    return result.scalar() or date.today()
```

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

---

## Migration Plan

**None required.** V2 is a pure code change.
