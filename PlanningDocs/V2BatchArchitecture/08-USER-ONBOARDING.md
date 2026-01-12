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

---

## Required Code Changes (Breaking Change from V1)

### Problem: Current UX Assumes Long-Running Batch

The current onboarding flow is built around 15-20 minute batch processing:

```
Current V1 Flow:
Upload CSV → POST /portfolios (fast) → POST /calculate (triggers batch)
    → Redirect to /onboarding/progress → Poll status for 15-20 min → Dashboard
```

V2's instant snapshot invalidates this entire flow.

---

### Frontend Changes Required

#### 1. `frontend/src/hooks/usePortfolioUpload.ts`

**Current behavior**: Calls `createPortfolio()` then `triggerCalculations()` then redirects to progress page.

**V2 change**: Skip `triggerCalculations()` entirely. Redirect directly to dashboard.

```typescript
// BEFORE (V1)
const handleUpload = async (file: File) => {
    const portfolio = await createPortfolio(file);
    await triggerCalculations(portfolio.id);  // DELETE THIS
    router.push(`/onboarding/progress?id=${portfolio.id}`);  // CHANGE THIS
};

// AFTER (V2)
const handleUpload = async (file: File) => {
    const response = await createPortfolio(file);

    if (response.status === 'ready') {
        router.push(`/portfolio/${response.portfolio_id}`);
    } else if (response.status === 'partial') {
        // Some symbols pending - still go to dashboard
        toast.info(`${response.pending_symbols.length} symbols loading...`);
        router.push(`/portfolio/${response.portfolio_id}`);
    }
};
```

#### 2. `frontend/app/onboarding/progress/page.tsx`

**Current behavior**: Shows batch phase progress (Phase 1, 2, 3...) with progress bars.

**V2 change**: Either deprecate entirely OR repurpose for symbol-only onboarding.

**Option A: Deprecate**
- Remove the page entirely
- All users go directly to dashboard

**Option B: Repurpose for symbol onboarding only**
- Only show when `response.status === 'partial'`
- Only track symbol onboarding progress (not full batch)
- Simplified UI: "Loading data for XYZ, ABC..." with checkmarks

```typescript
// Repurposed progress page (Option B)
function OnboardingProgress() {
    const { pendingSymbols } = useSymbolOnboardingStatus(portfolioId);

    if (pendingSymbols.length === 0) {
        // All symbols ready - redirect to dashboard
        router.push(`/portfolio/${portfolioId}`);
        return null;
    }

    return (
        <div>
            <h2>Loading market data...</h2>
            {pendingSymbols.map(symbol => (
                <SymbolStatusRow key={symbol} symbol={symbol} />
            ))}
            <p>You can start using your portfolio now.</p>
            <Button onClick={() => router.push(`/portfolio/${portfolioId}`)}>
                Go to Dashboard →
            </Button>
        </div>
    );
}
```

#### 3. `frontend/src/hooks/useOnboardingStatus.ts`

**Current behavior**: Polls `/api/v1/onboarding/status/{id}` for batch progress.

**V2 change**: Replace with symbol-specific status polling.

```typescript
// BEFORE (V1) - Polls for batch phases
const { phase, progress, isComplete } = useOnboardingStatus(portfolioId);

// AFTER (V2) - Polls for symbol status only
const { pendingSymbols, isComplete } = useSymbolOnboardingStatus(portfolioId);
```

---

### Backend Changes Required

#### 1. `backend/app/api/v1/portfolios.py`

**Current behavior**: `POST /portfolios` creates portfolio, returns ID. Separate `POST /calculate` triggers batch.

**V2 change**: `POST /portfolios` creates portfolio + instant snapshot + returns status.

```python
# BEFORE (V1)
@router.post("/portfolios")
async def create_portfolio(...):
    portfolio = await create_portfolio_record(...)
    return {"portfolio_id": str(portfolio.id)}

# AFTER (V2)
@router.post("/portfolios")
async def create_portfolio(...):
    portfolio = await create_portfolio_record(...)

    # Check symbols
    known, unknown = await check_symbol_universe(symbols)

    # Create instant snapshot with known symbols
    snapshot = await create_portfolio_snapshot(portfolio.id, known)

    # Queue unknown symbols for async processing
    if unknown:
        for symbol in unknown:
            await symbol_onboarding_queue.enqueue(symbol)
        asyncio.create_task(process_onboarding_queue())

    return {
        "portfolio_id": str(portfolio.id),
        "status": "ready" if not unknown else "partial",
        "pending_symbols": list(unknown) if unknown else None,
        "snapshot_date": snapshot.snapshot_date.isoformat()
    }
```

#### 2. `backend/app/api/v1/onboarding.py`

**Current behavior**: `POST /calculate` triggers full batch processing.

**V2 change**: Deprecate or remove. No longer needed for standard onboarding.

```python
# BEFORE (V1)
@router.post("/portfolios/{id}/calculate")
async def trigger_calculations(id: UUID):
    await batch_orchestrator.run_batch_sequence(portfolio_id=id)
    return {"status": "started"}

# AFTER (V2)
# DELETE THIS ENDPOINT or keep for manual admin use only
```

#### 3. `backend/app/api/v1/onboarding_status.py`

**Current behavior**: Returns batch phase progress (Phase 1: 45%, Phase 2: 0%...).

**V2 change**: Return simple ready/partial/pending status.

```python
# BEFORE (V1)
@router.get("/onboarding/status/{portfolio_id}")
async def get_onboarding_status(portfolio_id: UUID):
    batch_run = batch_run_tracker.get_current()
    return {
        "phase": batch_run.current_phase,
        "progress": batch_run.progress_percent,
        "phases": batch_run.phase_details
    }

# AFTER (V2)
@router.get("/onboarding/status/{portfolio_id}")
async def get_onboarding_status(portfolio_id: UUID):
    # Check if portfolio has snapshot
    snapshot = await get_latest_snapshot(portfolio_id)

    # Check for pending symbols
    positions = await get_positions(portfolio_id)
    pending_symbols = await get_pending_symbol_onboarding(
        [p.symbol for p in positions]
    )

    if not pending_symbols:
        return {"status": "ready", "pending_symbols": []}
    else:
        return {
            "status": "partial",
            "pending_symbols": [
                {"symbol": s.symbol, "status": s.status}
                for s in pending_symbols
            ]
        }
```

---

### Migration Strategy

| Phase | Action |
|-------|--------|
| 1 | Deploy backend V2 endpoints alongside V1 (new response format) |
| 2 | Update frontend to use new flow (skip triggerCalculations) |
| 3 | Deprecate old progress page or repurpose for symbol-only |
| 4 | Remove old batch-trigger endpoints after validation |

---

### Summary of File Changes

| File | Change |
|------|--------|
| `frontend/src/hooks/usePortfolioUpload.ts` | Skip triggerCalculations, direct redirect |
| `frontend/app/onboarding/progress/page.tsx` | Deprecate or repurpose for symbol status |
| `frontend/src/hooks/useOnboardingStatus.ts` | Replace with symbol-specific polling |
| `backend/app/api/v1/portfolios.py` | Add instant snapshot, return status |
| `backend/app/api/v1/onboarding.py` | Deprecate /calculate endpoint |
| `backend/app/api/v1/onboarding_status.py` | Simplify to ready/partial status |
