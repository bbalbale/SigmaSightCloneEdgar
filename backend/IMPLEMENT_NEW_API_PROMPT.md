# API Implementation Prompt (Standard Playbook)

Purpose: Provide a consistent, code-first prompt to implement a new API endpoint in the SigmaSight backend, aligned with our namespaces, auth, schemas, and documentation patterns.

Use this for endpoints in backend/TODO3.md starting at 3.0.3.10 (Correlation Matrix) and onward. Treat API_SPECIFICATIONS_V1.4.5.md as the source of truth; use API_SPECIFICATIONS_V1.4.4.md only for example shapes where helpful. Final behavior should match 1.4.5 or an approved TODO3.md note.

---

## Inputs (Fill These Before Starting)
- Endpoint ID (from TODO3.md): e.g., 3.0.3.10
- Canonical path and method: e.g., `GET /api/v1/analytics/correlation/{portfolio_id}/matrix`
- Status: Approved for implementation? (Yes/No). If not, request approval.
- Source spec: Paragraph/link from API_SPECIFICATIONS_V1.4.5.md; if absent, reference 1.4.4 for response shape.
- Ownership check required: Yes (most `/analytics/` endpoints require portfolio ownership validation).
- Performance target: < 500ms, paginated if large.

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
- For large collections, implement pagination and include `total`, `limit`, `offset`.

---

## Service Layer and Data Access
- Place non-trivial logic in a service file under `app/services/`, e.g., `CorrelationService`, `RiskMetricsService`.
- Use async SQLAlchemy sessions via `db: AsyncSession = Depends(get_db)` (or `get_async_session` for raw-data endpoints that follow that pattern).
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
    try:
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)
        svc = CorrelationService()
        data = await svc.get_matrix(db, portfolio_id, lookback_days, min_overlap)
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
    async def get_matrix(self, db: AsyncSession, portfolio_id, lookback_days: int, min_overlap: int):
        # TODO: implement using existing correlation engine
        # Return shape aligned with API_SPECIFICATIONS_V1.4.5 (and 1.4.4 example):
        # { "data": { "matrix": { ... }, "average_correlation": 0.75 } }
        return {"data": {"matrix": {}, "average_correlation": None}}
```

---

## Logging and Errors
- Use `get_logger(__name__)`. Log portfolio_id, user_id, parameters, and timing (if helpful).
- Convert known conditions to `HTTPException` with 4xx (e.g., ownership, validation).
- Return 500 only for unexpected errors.

---

## Documentation Tasks
- Update `backend/_docs/requirements/API_SPECIFICATIONS_V1.4.5.md`:
  - Add the endpoint under the appropriate section with: Endpoint, Status, File, Function, Authentication, Database/Service access, Purpose, Parameters, Response.
  - If using 1.4.4 for response shape, say so explicitly.
- Update `backend/TODO3.md`:
  - Change status for the item (e.g., from “APPROVED FOR IMPLEMENTATION” to “COMPLETED”).
  - Add a short “Completion Notes” block (files touched, tests run).

---

## Testing and Validation
- Add/extend integration tests if a test harness exists; otherwise provide a manual cURL block in the spec.
- Sanity checks:
  - Auth required and enforced.
  - Ownership required and enforced.
  - Response matches schema and sample shape.
  - Large payloads paginated (if applicable).
  - Latency reasonable on demo data (< 500ms).

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
- Correlation (3.0.3.10): use 1.4.4 for example response shape; enforce `lookback_days` and `min_overlap` limits.
- Diversification Score (3.0.3.11): may derive from correlation + weights; consider small dedicated endpoint.
- Factor Exposures (3.0.3.12 & 3.0.3.15): split portfolio vs positions; positions always paginated.
- Risk Metrics (3.0.3.13): include `portfolio_beta`, `annualized_volatility`, `max_drawdown` (optionally Sharpe/Sortino); query params: `lookback_days`, `benchmark`.
- Stress Test (3.0.3.14): path `/analytics/{portfolio_id}/stress-test`; use 1.4.4 scenarios shape and 1.4.5 description; delete unused legacy stub first.

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
