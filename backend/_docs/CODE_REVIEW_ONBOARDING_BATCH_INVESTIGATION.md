# Code Review: Onboarding Batch Investigation

**Date**: January 8, 2026
**Investigator**: Claude Opus 4.5
**Issue**: Batch processing not triggering during Testscotty2/Testscotty3 onboarding
**Status**: Findings documented, awaiting review

---

## Executive Summary

**Finding**: The onboarding flow does NOT automatically trigger batch processing. This is BY DESIGN according to the current codebase. The batch must be triggered via a separate `POST /api/v1/portfolios/{id}/calculate` call.

**Key Question for Review**: Was this design intentional, or was an automatic batch trigger removed at some point?

---

## Investigation Evidence

### 1. Onboarding Endpoint (`/api/v1/onboarding/create-portfolio`)

**File**: `backend/app/api/v1/onboarding.py`

**Lines 290-291** (docstring):
```python
**Fast response (<5s)** - No preprocessing or calculations.
Use POST /api/v1/portfolio/{id}/calculate to run analytics.
```

**Lines 376-382** (response body):
```python
"next_step": {
    "action": "calculate",
    "endpoint": f"/api/v1/portfolio/{portfolio.id}/calculate",
    "description": "Trigger batch calculations to populate risk metrics"
}
```

The onboarding endpoint explicitly:
1. Does NOT run batch processing
2. Returns a `next_step` instructing the client to call `/calculate`

### 2. Onboarding Service

**File**: `backend/app/services/onboarding_service.py`

**Line 200**: `Does NOT run preprocessing - that's deferred to calculate endpoint.`

**Line 377**: `"Use the /calculate endpoint to run risk analytics."`

The service layer confirms batch is deferred.

### 3. E2E Test Confirms Two-Step Flow

**File**: `backend/tests/e2e/test_onboarding_flow.py`

```python
# Line 170: Assert onboarding returns next_step to calculate
assert portfolio_data["next_step"]["action"] == "calculate"

# Lines 180-185: Test SEPARATELY calls the calculate endpoint
calculate_response = client.post(
    f"/api/v1/portfolio/{portfolio_id}/calculate",
)
assert calculate_response.status_code == 202
```

The official e2e test shows the expected flow is:
1. Call `/onboarding/create-portfolio` → creates portfolio
2. Call `/portfolio/{id}/calculate` → triggers batch

### 4. Git History Check

Checked commits `44d4a72c` ("fix 8 critical bugs preventing onboarding flow from working") - even that version has the same "use /calculate endpoint" design.

No evidence of an automatic batch trigger being removed.

### 5. Batch Trigger Locations

Searched entire codebase for batch triggers:

```
/backend/app/api/v1/portfolios.py:598         → POST /{id}/calculate endpoint
/backend/app/api/v1/endpoints/admin_batch.py  → Admin endpoints
/backend/app/api/v1/admin_fix.py              → Admin fix endpoints
```

**No batch trigger exists in**:
- `/api/v1/onboarding/create-portfolio`
- `onboarding_service.py`

---

## Database Evidence

### Testscotty3 Test (January 8, 2026)

| Check | Result |
|-------|--------|
| User created | ✅ 19:41:56 UTC |
| Portfolio created | ✅ "Scott Y 5M" |
| Positions imported | ✅ 13 positions |
| Snapshots | ❌ 0 (no batch ran) |
| Factor exposures | ❌ 0 (no batch ran) |
| New batch_run_history entry | ❌ None since Jan 7 |

---

## Architecture Diagram

```
Current Flow (as designed):
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND                                  │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 1: POST /onboarding/create-portfolio                  │
│  - Creates portfolio                                         │
│  - Imports positions from CSV                               │
│  - Returns next_step: { action: "calculate", ... }          │
│  - NO BATCH TRIGGERED                                       │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 2: POST /portfolios/{id}/calculate                    │
│  - Triggers run_portfolio_onboarding_backfill()             │
│  - Runs batch processing in background                      │
│  - Creates snapshots, factor exposures, etc.                │
└─────────────────────────────────────────────────────────────┘
```

---

## Hypotheses

### Hypothesis A: Frontend Should Auto-Call Calculate (Most Likely)

The onboarding endpoint returns `next_step.action = "calculate"`. The frontend should automatically call the calculate endpoint after successful portfolio creation.

**Question**: Is the frontend doing this? Was it doing this before?

### Hypothesis B: Design Changed Without Frontend Update

The backend was designed for fast onboarding (<5s) with deferred calculations. But perhaps an earlier version had automatic batch trigger, and the frontend relied on that.

**Question**: Check git history for frontend onboarding component to see if it calls `/calculate`.

### Hypothesis C: Missing Integration

The backend and frontend may have been developed with different expectations about who triggers the batch.

---

## Recommendations

### Option 1: Fix Frontend (If hypothesis A is correct)

Ensure frontend calls `POST /portfolios/{id}/calculate` after successful onboarding:

```typescript
// After successful portfolio creation
const portfolioResult = await createPortfolio(csvFile, ...);
if (portfolioResult.next_step.action === "calculate") {
  await fetch(portfolioResult.next_step.endpoint, { method: "POST" });
}
```

### Option 2: Add Auto-Trigger to Backend (If design should change)

Modify `onboarding.py` to trigger batch after portfolio creation:

```python
# In create_portfolio endpoint, after db.commit():
background_tasks.add_task(
    batch_orchestrator.run_portfolio_onboarding_backfill,
    str(result['portfolio_id']),
    get_most_recent_trading_day()
)
```

**Note**: This would require adding `BackgroundTasks` dependency to the endpoint.

### Option 3: Hybrid Approach

Keep fast onboarding but add optional auto-trigger parameter:

```python
auto_calculate: bool = Form(False, description="Auto-trigger calculations")
```

---

## Questions for User/Product Owner

1. **Was the frontend ever calling `/calculate` automatically after onboarding?**

2. **Should onboarding be "fast response" (current design) or "complete with analytics"?**

3. **For the immediate Testscotty3 test**: Should we manually trigger the batch to verify the Phase 1 fix works?

---

## Files Reviewed

1. `backend/app/api/v1/onboarding.py` - Main onboarding endpoint
2. `backend/app/services/onboarding_service.py` - Onboarding business logic
3. `backend/app/api/v1/portfolios.py` - Calculate endpoint (lines 521-608)
4. `backend/tests/e2e/test_onboarding_flow.py` - Expected flow
5. Git history for onboarding files (10+ commits)

---

## Conclusion

The batch not triggering is NOT a bug in the Phase 1 fix. The Phase 1 fix (`run_portfolio_onboarding_backfill`) is correctly implemented in the `/calculate` endpoint.

The issue is that the `/calculate` endpoint is never being called after onboarding completes. This is either:
- A frontend issue (not calling the endpoint)
- A design gap (backend should auto-trigger)
- A miscommunication about expected behavior

**Immediate Action**: Manually trigger batch for Testscotty3 to verify Phase 1 fix works, while investigating the frontend/design question separately.
