# 14: Freshness Contracts

## Overview

Data freshness SLAs for V2 batch architecture. Staleness is calculated based on trading days only (weekends and holidays excluded). Staleness indicators are admin-only; users are not shown data age.

---

## Freshness SLAs

| Data Type | Freshness Target | Staleness Tolerance | Notes |
|-----------|------------------|---------------------|-------|
| Symbol prices | EOD (after 4 PM ET) | 1 trading day | Core data |
| Symbol betas/factors | EOD | 1 trading day | Calculated from prices |
| P&L snapshots | EOD | Never stale | Created fresh daily |
| Position market values | EOD | 1 trading day | Updated from prices |
| Portfolio factor exposures | On-demand | 24h cache TTL | Computed and cached |

---

## Trading Day Calculation

```python
from datetime import date, timedelta
import holidays

US_HOLIDAYS = holidays.NYSE()  # NYSE holiday calendar

def get_last_trading_day(reference_date: date = None) -> date:
    """Get the most recent trading day."""
    check_date = reference_date or date.today()

    while True:
        # Weekend check
        if check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            check_date -= timedelta(days=1)
            continue

        # Holiday check
        if check_date in US_HOLIDAYS:
            check_date -= timedelta(days=1)
            continue

        return check_date


def calculate_staleness_days(data_date: date, reference_date: date = None) -> int:
    """
    Calculate trading days of staleness.

    Returns 0 if current, 1 if one trading day old, etc.
    Weekends and holidays are NOT counted.
    """
    reference = reference_date or date.today()
    last_trading_day = get_last_trading_day(reference)

    if data_date >= last_trading_day:
        return 0  # Current

    # Count trading days between data_date and last_trading_day
    trading_days = 0
    check_date = last_trading_day

    while check_date > data_date:
        check_date -= timedelta(days=1)
        if check_date.weekday() < 5 and check_date not in US_HOLIDAYS:
            trading_days += 1

    return trading_days


def get_staleness_status(data_date: date) -> str:
    """Get staleness status for admin display."""
    days = calculate_staleness_days(data_date)

    if days == 0:
        return "current"
    elif days == 1:
        return "stale_1d"
    else:
        return f"stale_{days}d"
```

**Examples:**

| Scenario | Data Date | Reference Date | Staleness |
|----------|-----------|----------------|-----------|
| Friday data on Monday | Jan 10 (Fri) | Jan 13 (Mon) | 0 (current) |
| Thursday data on Monday | Jan 9 (Thu) | Jan 13 (Mon) | 1 trading day |
| Friday data on Tuesday | Jan 10 (Fri) | Jan 14 (Tue) | 1 trading day |
| MLK Day (holiday) | Jan 17 (Fri) | Jan 21 (Tue) | 0 (current) |

---

## Alerting Thresholds

```python
class StalenessAlert(Enum):
    NONE = "none"
    WARNING = "warning"
    CRITICAL = "critical"


def get_alert_level(data_date: date) -> StalenessAlert:
    """Determine alert level based on staleness."""
    days = calculate_staleness_days(data_date)

    if days == 0:
        return StalenessAlert.NONE
    elif days == 1:
        return StalenessAlert.WARNING
    else:  # 2+ days
        return StalenessAlert.CRITICAL


async def check_and_alert_staleness():
    """Check data freshness and send alerts if needed."""
    latest_price_date = await get_latest_price_date()
    alert_level = get_alert_level(latest_price_date)

    if alert_level == StalenessAlert.WARNING:
        await send_alert(
            level="warning",
            message=f"Market data is 1 trading day stale (as of {latest_price_date})",
            channel="ops"
        )
    elif alert_level == StalenessAlert.CRITICAL:
        days = calculate_staleness_days(latest_price_date)
        await send_alert(
            level="critical",
            message=f"Market data is {days} trading days stale (as of {latest_price_date})",
            channel="ops"
        )
```

---

## Admin Dashboard Display

```typescript
// Admin-only staleness indicator
interface DataFreshnessStatus {
  latestPriceDate: string;
  stalenessStatus: 'current' | 'stale_1d' | 'stale_2d' | 'stale_3d+';
  tradingDaysStale: number;
  alertLevel: 'none' | 'warning' | 'critical';
  nextExpectedUpdate: string;  // "Tonight 9:00 PM ET"
}

// Admin dashboard component
function DataFreshnessPanel({ status }: { status: DataFreshnessStatus }) {
  return (
    <div className="panel">
      <h3>Market Data Freshness</h3>

      <div className="stat">
        <label>Latest Price Date</label>
        <value>{formatDate(status.latestPriceDate)}</value>
      </div>

      <div className="stat">
        <label>Status</label>
        {status.alertLevel === 'none' && (
          <Badge variant="success">Current</Badge>
        )}
        {status.alertLevel === 'warning' && (
          <Badge variant="warning">1 day stale</Badge>
        )}
        {status.alertLevel === 'critical' && (
          <Badge variant="error">{status.tradingDaysStale} days stale</Badge>
        )}
      </div>

      <div className="stat">
        <label>Next Update</label>
        <value>{status.nextExpectedUpdate}</value>
      </div>
    </div>
  );
}
```

---

## User Visibility

**Rule: Users do NOT see staleness indicators.**

- No "Data as of..." labels on dashboard
- No warning banners about delayed data
- Data is presented as current

**Exception**: Onboarding flow explains pricing basis (see below).

---

## Onboarding Flow: Price Disclosure

When user uploads portfolio, the confirmation screen includes:

```typescript
// Onboarding confirmation component
function OnboardingConfirmation({ result }: { result: CreatePortfolioResponse }) {
  return (
    <div className="confirmation">
      <h2>Portfolio Created!</h2>

      <p className="info-text">
        Your portfolio has been valued using market closing prices
        from {formatDate(result.snapshotDate)}.
      </p>

      {isBeforeMarketClose() && (
        <p className="info-text muted">
          Today's closing prices will be reflected after 9:00 PM ET.
        </p>
      )}

      <Button onClick={() => router.push(`/portfolio/${result.portfolioId}`)}>
        View Portfolio
      </Button>
    </div>
  );
}
```

**Copy variations:**

| Time of Upload | Message |
|----------------|---------|
| Before 9 PM ET weekday | "Valued using yesterday's closing prices. Today's prices will be reflected after 9:00 PM ET." |
| After 9 PM ET weekday | "Valued using today's closing prices." |
| Weekend | "Valued using Friday's closing prices. New prices will be reflected Monday after 9:00 PM ET." |

---

## API Response

```python
@router.get("/admin/data/freshness")
async def get_data_freshness(
    db: AsyncSession = Depends(get_db)
) -> DataFreshnessResponse:
    """Get data freshness status for admin dashboard."""

    latest_price_date = await get_latest_price_date(db)
    staleness_days = calculate_staleness_days(latest_price_date)
    alert_level = get_alert_level(latest_price_date)

    return DataFreshnessResponse(
        latest_price_date=latest_price_date.isoformat(),
        staleness_status=get_staleness_status(latest_price_date),
        trading_days_stale=staleness_days,
        alert_level=alert_level.value,
        next_expected_update=get_next_batch_time().isoformat()
    )
```

---

## Summary

| Aspect | Decision |
|--------|----------|
| Staleness calculation | Trading days only (skip weekends/holidays) |
| User visibility | None (admin-only) |
| Warning alert | 1 trading day stale |
| Critical alert | 2+ trading days stale |
| Onboarding disclosure | Show price date on confirmation screen |
