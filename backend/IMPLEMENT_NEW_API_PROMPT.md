# API Implementation Prompt (Standard Playbook)

Purpose: Provide a consistent, code-first prompt to implement a new API endpoint in the SigmaSight backend, aligned with our namespaces, auth, schemas, and documentation patterns.

Use this for endpoints in backend/TODO3.md. Implementation details and response shapes should be documented in the TODO items themselves.

---

## CRITICAL: Permission Requirements

### 🔴 ALWAYS Get Explicit Approval For:
1. **Database Changes**: ANY schema changes, new tables, column modifications
   - Must be documented as separate TODO item
   - Must include Alembic migration plan
   - Must test with Docker deployment
2. **Service Layer Changes**: 
   - Creating new service classes or data models
   - Modifying existing service methods or classes
   - Especially changes to existing data models
3. **Direct ORM Access**: 
   - NEVER access database directly from API endpoints
   - Always use service layer abstraction
   - If service method doesn't exist, ASK before creating

### ✅ Proceed Without Approval:
- Adding new API endpoints using existing services
- Creating new Pydantic schemas for requests/responses
- Adding new methods to retrieve existing data
- Implementing endpoints that only format/return pre-calculated data

---

## Inputs (Fill These Before Starting)
- Endpoint ID (from TODO3.md): e.g., 3.0.3.10
- Canonical path and method: e.g., `GET /api/v1/analytics/correlation/{portfolio_id}/matrix`
- Status: Approved for implementation? (Yes/No). If not, request approval.
- Response shape source: Check TODO3.md for requirements and examples. If TODO3.md references API_SPECIFICATIONS_V1.4.4/1.4.5, treat those as example shape references — TODO3.md governs the contract.
- Ownership check required: Yes/No (most `/analytics/` endpoints: Yes)
- Missing data behavior: `404 Not Found` vs `200 OK` with empty payload + metadata
- Pagination requirement: Yes/No and limits (if large payloads)
- Performance target: < 500ms; add caching notes if needed

---

## Standard Shaping Controls (Keep Endpoints Simple)
- lookback_days (int): horizon used by batch calculation (e.g., 90). Enforced bounds (e.g., 30–365).
- min_overlap (int): minimum overlapping observations for pairwise stats (e.g., 30). Bounds (e.g., 10–365).
- selection_by (enum): `weight` | `explicit` — default `weight`.
  - weight: pick top symbols by current gross market value (abs(quantity*last_price)).
  - explicit: require `symbols` CSV query param; intersect with symbols present in batch results.
- symbols (CSV): only when `selection_by=explicit`.
- max_symbols (int): default 25; hard cap 50 — limit output size.
- min_weight (float 0–1): default 0.01 — filter small positions before selection.
- view (enum): `matrix` | `pairs` — default `matrix`. Choose output shape for dashboards vs. chat.

Enforce defaults/caps in the service layer. Prefer a small set of high‑signal params to avoid heavy frontends.

---

## Standard Selection Policy (Default Behavior)
- Selection mode: weight-only in v1 — pick top `max_symbols` by current gross market value (abs(quantity*last_price)); no explicit list or min_weight filtering in v1.
- Validate params: enforce `min_overlap <= lookback_days`; clamp `max_symbols` to a safe cap (e.g., 50).
- Consistency: use the same selection policy across endpoints that consume the same batch results (e.g., correlation matrix and diversification score) to keep UX and results coherent.

---

## Pre-Implementation Discovery (AI Agent Tasks)
Before implementing, check:
1) Does the service layer already exist? Search: `grep -r "class.*Service" app/services/`
2) Are there existing schemas? Check: `app/schemas/analytics.py`, `app/schemas/risk.py`
3) Is data pre-calculated via batch? Check: `app/batch/` and `app/models/` for relevant tables
4) Are there similar endpoints? Search: `grep -r "similar_pattern" app/api/v1/`
5) Check if retrieval methods exist: `grep "get_.*correlation\|fetch_.*" app/services/`

**Important**: Many analytics endpoints retrieve pre-calculated batch data rather than computing on-the-fly.

---

## Generalized Development Tasks
1) Create/extend router under correct namespace; register in aggregator router
2) Add request/response Pydantic schemas (use existing modules where possible)
3) Enforce auth and portfolio ownership (where applicable)
4) Implement service layer with async DB access and minimal queries
5) Return response matching the spec’s shape and types (no extra fields unless documented)
6) Add logging and robust error handling (4xx for client errors, 5xx for unexpected)
7) Update API_SPECIFICATIONS_V1.4.5.md with full attribution and example
8) Update backend/TODO3.md status and add completion notes
9) Provide a cURL example or add an integration test when feasible

---

## Naming and Paths
- Use `snake_case` for code, `lower-kebab` for paths.
- Path params: always `{portfolio_id}` (not `{id}`).
- Namespaces:
  - Raw data: `/api/v1/data/...`
  - Analytics: `/api/v1/analytics/...`
  - Management: `/api/v1/management/...`
- Router placement:
  - Create a file under `app/api/v1/analytics/` (or appropriate namespace) with an `APIRouter` and a clear `prefix` (e.g., `/correlation`, `/risk`, `/factors`, `/portfolio`).
  - Register the router in `app/api/v1/analytics/router.py` (or main router if needed).

---

## Authentication and Security
- Require auth for all analytics endpoints: `current_user: CurrentUser = Depends(get_current_user)`.
- For portfolio-scoped endpoints, validate ownership: `await validate_portfolio_ownership(db, portfolio_id, current_user.id)`.
- Never leak portfolios that aren’t owned by the current user.

---

## Schemas and Serialization
- Define response/request Pydantic models in `app/schemas/...` (prefer an existing module like `analytics.py`; otherwise create a focused one).
- Ensure datetime fields are UTC ISO‑8601 with `Z` (use utilities in `app/core/datetime_utils.py`).
- Use numeric types consistently; round only at presentation layer unless the spec requires.
- Decimal serialization: Pydantic may emit Decimals as strings; convert to float in response DTOs when appropriate to keep JSON ergonomic.
- For large collections, implement pagination and include `total`, `limit`, `offset`.

---

## Service Layer and Data Access
- **CRITICAL**: Check if data is batch-processed before implementing calculations
  - Look for existing batch jobs in `app/batch/batch_orchestrator_v2.py`
  - Check database models for pre-calculated tables (e.g., `CorrelationCalculation`, `FactorExposure`)
  - If batch-processed, implement retrieval NOT recalculation
- Place non-trivial logic in a service file under `app/services/`, e.g., `CorrelationService`, `RiskMetricsService`.
- **NEVER** access ORM models directly from API endpoints - always use service layer
- Use async SQLAlchemy sessions via `db: AsyncSession = Depends(get_db)` (or `get_async_session` for raw-data endpoints that follow that pattern).
- Query models from `app/models/...` with minimal round trips; rely on existing indexes where possible (e.g., `MarketDataCache` has symbol/date indexes).
- For external data (e.g., Polygon), use existing clients/services with rate limiting.
- Cache expensive calculations if feasible; document TTL if you add caching.

### Service Read Patterns (No Recompute)
- For correlation-based endpoints:
  - Read from `correlation_calculations` (header per run) and `pairwise_correlations` (full NxN, both directions + diagonal)
  - Provide canonical read methods on the service:
    - `get_matrix(portfolio_id, lookback_days, min_overlap, max_symbols)`
    - `get_weighted_correlation(portfolio_id, lookback_days, min_overlap, max_symbols)`
  - Selection policy: reuse the Standard Selection Policy above (weight-only) to derive the symbol set.

---

## Missing-Data Contract and Metadata
- Prefer `200 OK` with an `available=false` envelope for “no data yet” cases rather than 404, unless the resource truly doesn’t exist.
- Standard metadata (example):
```json
{
  "available": false,
  "reason": "no_calculation_available|insufficient_symbols",
  "duration_days": 90,
  "calculation_date": null
}
```
- When data is available, include lightweight metadata next to the payload:
  - `duration_days`, `calculation_date` (UTC ISO8601), `symbols_included`, and `parameters_used` (lookback_days, min_overlap, max_symbols, selection_method)

---

## Output Rules (Matrix and Scalar)
- Matrix (e.g., correlation): symmetric nested map `{symbol: {symbol: corr}}` over the selected symbols; diagonal = 1.0; order symbols by weight.
- Scalar (e.g., diversification): weighted absolute correlation using current gross weights `w_i`:
  - numerator = Σ_{i<j} (w_i × w_j × |c_ij|)
  - denominator = Σ_{i<j} (w_i × w_j)
  - `portfolio_correlation = numerator / denominator`

---
- Query models from `app/models/...` with minimal round trips; rely on existing indexes where possible (e.g., `MarketDataCache` has symbol/date indexes).
- For external data (e.g., Polygon), use existing clients/services with rate limiting.
- Cache expensive calculations if feasible; document TTL if you add caching.

---

## Endpoint Template (FastAPI)
```python
# app/api/v1/analytics/correlation.py
from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, validate_portfolio_ownership
from app.database import get_db
from app.schemas.auth import CurrentUser
from app.schemas.analytics import CorrelationMatrixResponse  # create this
from app.services.correlation_service import CorrelationService  # create this
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/correlation", tags=["correlation-analytics"])

@router.get("/{portfolio_id}/matrix", response_model=CorrelationMatrixResponse)
async def get_correlation_matrix(
    portfolio_id: UUID,
    lookback_days: int = Query(90, ge=30, le=365),
    min_overlap: int = Query(30, ge=10, le=365),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Input validation
    if min_overlap > lookback_days:
        raise HTTPException(400, "Min overlap cannot exceed lookback days")
    
    try:
        # Performance monitoring
        import time
        start = time.time()
        
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)
        
        # Note: Check if service needs db in constructor or as method param
        svc = CorrelationService(db)  # Many services need db in constructor
        data = await svc.get_matrix(portfolio_id, lookback_days, min_overlap)
        
        elapsed = time.time() - start
        if elapsed > 0.5:
            logger.warning(f"Slow response: {elapsed:.2f}s for {portfolio_id}")
            
        return CorrelationMatrixResponse(**data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Correlation matrix failed for {portfolio_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error computing correlation matrix")
```

Register the router:
```python
# app/api/v1/analytics/router.py
from app.api.v1.analytics.correlation import router as correlation_router
...
router.include_router(correlation_router)
```

Service example:
```python
# app/services/correlation_service.py
from sqlalchemy.ext.asyncio import AsyncSession

class CorrelationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_matrix(self, portfolio_id, lookback_days: int, min_overlap: int):
        # Retrieve pre-calculated results; do not recompute here.
        # Example target shape (adjust per TODO3.md):
        # { "available": true, "metadata": {...}, "matrix": { ... }, "average_correlation": 0.75 }
        return {"available": False, "metadata": {"reason": "not_implemented"}}
```

---

## Logging and Errors
- Use `get_logger(__name__)`. Log portfolio_id, user_id, parameters, and timing (if helpful).
- Convert known conditions to `HTTPException` with 4xx (e.g., ownership, validation).
- Return 500 only for unexpected errors.

---

## Common Gotchas (AI Agents Beware!)
1. **Service initialization**: Most services need `db` passed to constructor, not created empty
2. **UUID handling**: Always convert string UUIDs to UUID objects
3. **Async patterns**: Never mix sync/async - causes greenlet errors
4. **Missing data**: Implement graceful degradation, not 500 errors
5. **Response wrapping**: Check if spec wants `{"data": {...}}` wrapper or direct response
6. **Decimal types**: Use `Decimal` for financial values, convert to float only in JSON response
7. **Table doesn't exist**: Check if migration needed or table name mismatch
8. **Auth fails**: Ensure you're using `get_current_user` dependency
9. **404 on route**: Check router registration in parent router file

---

## Documentation Tasks
- Update `backend/_docs/requirements/API_SPECIFICATIONS_V1.4.5.md` if it exists:
  - Add the endpoint under the appropriate section with: Endpoint, Status, File, Function, Authentication, Database/Service access, Purpose, Parameters, Response.
- Update `backend/TODO3.md`:
  - Change status for the item (e.g., from "APPROVED FOR IMPLEMENTATION" to "COMPLETED").
  - Add a short "Completion Notes" block (files touched, tests run).

---

## Testing and Validation

### Import Verification
Before implementing, verify imports work:
```bash
cd backend
uv run python -c "from app.services.correlation_service import CorrelationService; print('✅')"
```

### Quick Test Commands
```bash
# Test with demo portfolio (use actual UUID from database)
TOKEN="your_jwt_token"
PORTFOLIO_ID="fcd71196-e93e-f000-5a74-31a9eead3118"
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/analytics/correlation/$PORTFOLIO_ID/matrix?lookback_days=90"
```

### Sanity checks:
- Auth required and enforced
- Ownership required and enforced
- Response matches schema and sample shape
- Large payloads paginated (if applicable)
- Latency reasonable on demo data (< 500ms)
- Test with Docker deployment if database changes made

---

## Acceptance Criteria (Checklist)
- [ ] Endpoint path/method match TODO3.md and spec
- [ ] Router registered and reachable under `/api/v1/...`
- [ ] Auth + ownership enforced
- [ ] Pydantic schemas added/updated
- [ ] Service layer implemented (no heavy logic in router)
- [ ] Proper logging and error handling
- [ ] Docs updated in API_SPECIFICATIONS_V1.4.5.md
- [ ] TODO3.md status updated with notes
- [ ] Manual test (cURL) included; optional automated test

---

## Notes on Specific Endpoint Families
- Correlation (3.0.3.10): Retrieve pre-calculated correlations from database; enforce `lookback_days` and `min_overlap` limits.
- Diversification Score (3.0.3.11): May derive from correlation + weights; consider small dedicated endpoint.
- Factor Exposures (3.0.3.12 & 3.0.3.15): Split portfolio vs positions; positions always paginated.
- Risk Metrics (3.0.3.13): Include `portfolio_beta`, `annualized_volatility`, `max_drawdown` (optionally Sharpe/Sortino); query params: `lookback_days`, `benchmark`.
- Stress Test (3.0.3.14): Path `/analytics/{portfolio_id}/stress-test`; check TODO3.md for specific requirements.

---

## Versioning & Deprecation
- If replacing an existing path that is in use: add new route, mark old as `deprecated=True`, migrate callers, and remove after window.
- If no one uses the old path: delete the old route and implement the new canonical path.

---

## Commit Message Template
```
feat(analytics): implement {Endpoint Name} API

- add router {file}
- add schemas {files}
- add service {file}
- register router
- update API_SPECIFICATIONS_V1.4.5.md (docs)
- update TODO3.md (status + notes)
```

This prompt is intended to be pasted into a work session and filled with the specifics for the chosen endpoint before coding.
