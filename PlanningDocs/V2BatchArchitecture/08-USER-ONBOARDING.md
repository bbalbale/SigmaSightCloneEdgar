# 08: User Onboarding Flow

## Overview

When a user uploads a portfolio, we create a snapshot INSTANTLY using cached prices. No batch trigger, no waiting.

**Key Rule**: Snapshot date = price date (not creation time)
- User onboards at 2 PM Tuesday → snapshot_date = Monday (yesterday's close)
- User onboards at 10 PM Tuesday (post-cron) → snapshot_date = Tuesday (today's close)

---

## Flow

```
User uploads CSV
    │
    ▼
┌─────────────────────────────────────┐
│ 1. Parse CSV, validate format       │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 2. Check symbols against universe   │
│    ├── Known symbols: Continue      │
│    └── Unknown symbols: Queue for   │
│        async onboarding             │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 3. Create portfolio + positions     │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 4. Get latest price date from cache │
│    (market_data_cache)            │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 5. Create snapshot for that date    │
│    using cached prices              │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 6. Compute and cache analytics      │
└─────────────────────────────────────┘
    │
    ▼
Return: Portfolio ready!
```

**Total time**: < 5 seconds (for known symbols)

---

## Implementation

```python
async def create_portfolio_with_csv(
    db: AsyncSession,
    user_id: UUID,
    csv_data: UploadFile,
    portfolio_name: str
) -> CreatePortfolioResponse:
    """
    Create portfolio from CSV with instant analytics.

    NO batch trigger. Uses cached prices only.
    """

    # Step 1: Parse and validate CSV
    positions_data = await parse_csv(csv_data)
    symbols = {p.symbol for p in positions_data}

    # Step 2: Check symbol readiness
    known, unknown = await check_symbol_universe(db, symbols)

    if unknown:
        # Queue unknown symbols for async processing
        for symbol in unknown:
            await queue_symbol_onboarding(symbol, requested_by=user_id)

    # Step 3: Create portfolio and positions
    portfolio = Portfolio(
        user_id=user_id,
        name=portfolio_name
    )
    db.add(portfolio)
    await db.flush()

    for pos_data in positions_data:
        position = Position(
            portfolio_id=portfolio.id,
            symbol=pos_data.symbol,
            quantity=pos_data.quantity,
            entry_price=pos_data.entry_price,
            entry_date=pos_data.entry_date
        )
        db.add(position)

    # Step 4: Get latest price date from cache
    latest_price_date = await get_latest_price_date(db)

    # Step 5: Create snapshot using cached prices
    # Only include known symbols in snapshot
    snapshot = await create_portfolio_snapshot(
        db=db,
        portfolio_id=portfolio.id,
        snapshot_date=latest_price_date,
        symbols_to_include=known  # Exclude unknown symbols
    )

    # Step 6: Compute and cache analytics
    await compute_and_cache_analytics(db, portfolio.id)

    await db.commit()

    # Return response
    return CreatePortfolioResponse(
        portfolio_id=str(portfolio.id),
        status="ready" if not unknown else "partial",
        snapshot_date=latest_price_date.isoformat(),
        pending_symbols=list(unknown) if unknown else None,
        message="Portfolio created with full analytics!" if not unknown
                else f"Portfolio created. Loading data for {len(unknown)} new symbol(s)..."
    )
```

---

## Price Date Logic

```python
async def get_latest_price_date(db: AsyncSession) -> date:
    """
    Get the most recent price date in market_data_cache.

    This is the date we'll use for the snapshot.
    - Before 9 PM cron: Yesterday's date
    - After 9 PM cron: Today's date
    """
    result = await db.execute(
        select(func.max(MarketDataCache.date))
    )
    latest_date = result.scalar()

    if not latest_date:
        raise NoPriceDataError("No price data available")

    return latest_date


async def get_cached_price_for_date(
    db: AsyncSession,
    symbol: str,
    price_date: date
) -> Optional[Decimal]:
    """
    Get cached closing price for a symbol on a specific date.

    NEVER fetches live prices - cache only.
    """
    result = await db.execute(
        select(MarketDataCache.close)
        .where(
            MarketDataCache.symbol == symbol.upper(),
            MarketDataCache.date == price_date
        )
    )
    row = result.first()
    return row.close if row else None
```

---

## Snapshot Creation

```python
async def create_portfolio_snapshot(
    db: AsyncSession,
    portfolio_id: UUID,
    snapshot_date: date,
    symbols_to_include: Optional[Set[str]] = None
) -> PortfolioSnapshot:
    """
    Create snapshot using cached prices.

    Args:
        portfolio_id: Portfolio to snapshot
        snapshot_date: Date for the snapshot (matches price date)
        symbols_to_include: If provided, only include these symbols
                           (used to exclude unknown symbols during onboarding)
    """
    positions = await get_active_positions(db, portfolio_id)

    total_value = Decimal('0')
    total_cost = Decimal('0')
    positions_included = 0
    positions_skipped = 0

    for position in positions:
        # Skip if symbol not in include list
        if symbols_to_include and position.symbol not in symbols_to_include:
            positions_skipped += 1
            continue

        # Get cached price
        price = await get_cached_price_for_date(db, position.symbol, snapshot_date)

        if price:
            market_value = position.quantity * price
            total_value += market_value
            total_cost += position.quantity * position.entry_price
            positions_included += 1

            # Update position's market value
            position.market_value = market_value
            position.last_price = price
            position.last_price_date = snapshot_date

    # Calculate P&L
    total_pnl = total_value - total_cost
    pnl_percent = (total_pnl / total_cost * 100) if total_cost else Decimal('0')

    # Create snapshot
    snapshot = PortfolioSnapshot(
        portfolio_id=portfolio_id,
        snapshot_date=snapshot_date,
        total_value=total_value,
        total_cost=total_cost,
        total_pnl=total_pnl,
        pnl_percent=pnl_percent,
        position_count=positions_included
    )

    db.add(snapshot)

    return snapshot
```

---

## Unknown Symbol Handling

When portfolio contains symbols not in universe:

```python
async def check_symbol_universe(
    db: AsyncSession,
    symbols: Set[str]
) -> Tuple[Set[str], Set[str]]:
    """
    Check which symbols are known vs unknown.

    Returns: (known_symbols, unknown_symbols)
    """
    result = await db.execute(
        select(SymbolUniverse.symbol)
        .where(
            SymbolUniverse.symbol.in_([s.upper() for s in symbols]),
            SymbolUniverse.status == 'active'
        )
    )
    known = {row[0] for row in result.all()}
    unknown = {s.upper() for s in symbols} - known

    return known, unknown
```

**Behavior with unknown symbols:**
- Portfolio is created with ALL positions (known + unknown)
- Snapshot only includes known symbols
- Unknown symbols queued for async onboarding
- Response indicates partial status
- When unknown symbols complete, next nightly cron includes them

---

## Frontend Integration

```typescript
// After CSV upload
const response = await createPortfolio(csvFile, portfolioName)

if (response.status === 'ready') {
    // All symbols known - go directly to dashboard
    toast.success('Portfolio created!')
    router.push(`/portfolio/${response.portfolio_id}`)
} else if (response.status === 'partial') {
    // Some symbols pending - show notice but still usable
    toast.info(`Portfolio created. ${response.pending_symbols.length} symbols loading...`)
    router.push(`/portfolio/${response.portfolio_id}`)
}
```

**Key UX change**: No more progress screen for 99% of users. Instant redirect to dashboard.

---

## What About the Old Onboarding Progress UI?

The Phase 7.x onboarding progress screen (`/onboarding/progress`) is **no longer needed for most users**.

**When it's still used:**
- Unknown symbols being onboarded (rare, <1% of users)
- Symbol onboarding taking longer than expected

**Frontend change:**
```typescript
// Old flow (15-30 min wait):
// Upload → Progress screen → Poll for 15-30 min → Dashboard

// New flow (instant):
// Upload → Dashboard (with optional "loading symbols" toast)
```

---

## Timeline

| Scenario | Duration |
|----------|----------|
| All symbols known | < 3 seconds |
| 1-5 unknown symbols | 3 sec + 30-60 sec async |
| 10+ unknown symbols | 3 sec + 1-2 min async |

User can use dashboard immediately in all cases (with partial data if symbols pending).
