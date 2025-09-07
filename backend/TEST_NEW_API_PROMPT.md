# Backend Test Prompt (End‑to‑End Validation)

Purpose: Provide a repeatable, code‑first checklist to bring up SigmaSight Backend locally and validate new API endpoints against a real Postgres DB, seeded demo data, batch outputs, and (optionally) LLM connections.

Use this to verify endpoints like analytics/correlation‑matrix, diversification‑score, factor exposures, etc., after implementation.

---

## Inputs (Fill Before You Start)
- Branch: `frontendtest` (or your working branch)
- DB URL: `postgresql+asyncpg://sigmasight:sigmasight_dev@localhost:5432/sigmasight_db`
- Auth: demo user credentials (from seeding)
  - `demo_hnw@sigmasight.com / demo12345` (or the others listed in logs)
- Portfolio ID: copy from DB or from `/auth/me` response
- Lookback params: `lookback_days=90`, `min_overlap=30` (analytics tests)
- OpenAI key (optional, for chat tests): `OPENAI_API_KEY`

---

## 1) Environment Setup

1. Prereqs
   - Docker Desktop running
   - Python 3.11+ and `uv` installed (or use `pip` as fallback)
2. Start Postgres
   ```bash
   cd backend
   docker compose up -d postgres
   # Verify
   docker ps | grep postgres
   ```
3. Configure env
   - Create `.env` in `backend/` with at least:
     ```env
     DATABASE_URL=postgresql+asyncpg://sigmasight:sigmasight_dev@localhost:5432/sigmasight_db
     OPENAI_API_KEY=sk-...          # Optional, for chat tests
     MODEL_DEFAULT=gpt-4o-mini      # Example; aligns with your config
     MODEL_FALLBACK=gpt-4o-mini     # Example
     DEBUG=true
     ```

---

## 2) Seed Demo Data (Users, Portfolios, Positions, Factors)

Use the authoritative seeding script (safe mode first):
```bash
cd backend
uv run python scripts/reset_and_seed.py seed
# or destructive full reset (dev only):
# uv run python scripts/reset_and_seed.py reset --confirm
```
You should see logs confirming:
- 3 demo users, 3 portfolios, 60+ positions
- 8 factor definitions
- Market data rows populated

Validate (optional):
```bash
uv run python scripts/reset_and_seed.py validate
```

---

## 3) Run Batch (Generate Analytics Data)

Generate correlation matrices, factor exposures, stress tests, etc.:
```bash
uv run python -c "from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2; import asyncio; asyncio.run(batch_orchestrator_v2.run())"
```
This populates tables such as:
- `correlation_calculations`, `pairwise_correlations`
- `factor_exposures`, `position_factor_exposures`

---

## 4) Start the API Server

```bash
uv run uvicorn app.main:app --reload
# API docs: http://localhost:8000/docs
```

---

## 5) Authenticate and Get Portfolio ID

1) Login and capture token
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo_hnw@sigmasight.com","password":"demo12345"}' | jq -r .access_token)
```
2) Get current user (includes portfolio_id)
```bash
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me | jq
PORTFOLIO_ID=<paste from .portfolio_id>
```

---

## 6) Smoke Tests (Core Data APIs)

- List portfolios (raw data):
```bash
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/data/portfolios | jq
```
- Portfolio complete (raw data):
```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/data/portfolio/$PORTFOLIO_ID/complete | jq
```

---

## 7) Analytics Tests (New Endpoints)

A) Correlation Matrix (3.0.3.10 – matrix, when implemented)
```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/analytics/portfolio/$PORTFOLIO_ID/correlation-matrix?lookback_days=90&min_overlap=30&max_symbols=25" | jq
```
Expected:
- 200 OK with either `available: false` metadata or `data.matrix` and `data.average_correlation`.

B) Diversification Score (3.0.3.11 – IMPLEMENTED)
```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/analytics/portfolio/$PORTFOLIO_ID/diversification-score?lookback_days=90&min_overlap=30" | jq
```
Expected:
- 200 OK with `available: true` and fields:
  - `portfolio_correlation` ∈ [0,1]
  - `duration_days`, `calculation_date`, `symbols_included`
  - `metadata.parameters_used` echoing inputs
- Or `available: false` with `reason` `no_calculation_available` or `insufficient_symbols`.

C) Factor Exposures (planned in TODO3.md)
- Portfolio factors:
```bash
# After implementation
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/analytics/portfolio/$PORTFOLIO_ID/factor-exposures | jq
```
- Position factors (paginated):
```bash
# After implementation
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/analytics/portfolio/$PORTFOLIO_ID/positions/factor-exposures?limit=50&offset=0" | jq
```

---

## 8) Optional: Chat/LLM Live Test

If `OPENAI_API_KEY` is set and you want to validate chat SSE:
```bash
# Create conversation
CID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"mode":"green"}' \
  http://localhost:8000/api/v1/chat/conversations | jq -r .id)

# Send a message (SSE) – stream will be returned
curl -N -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"conversation_id":"'$CID'","text":"What are my top factor exposures?"}' \
  http://localhost:8000/api/v1/chat/send
```
Look for SSE events: `message_created`, `start`, `message` (tokens), `done`.

---

## 9) Troubleshooting

- Database empty or wrong IDs
  - Re‑seed: `uv run python scripts/reset_and_seed.py seed`
  - Validate: `uv run python scripts/reset_and_seed.py validate`
- No correlation data
  - Run batch: `uv run python -c "from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2; import asyncio; asyncio.run(batch_orchestrator_v2.run())"`
  - Lower `min_overlap` (e.g., 10) for sparse data
- Auth errors
  - Ensure token is set, or re‑login
- SSE issues
  - Check CORS and cookies if testing via a browser client; using curl with Bearer token avoids cookie complications

---

## 10) Success Criteria
- Backend starts without errors; DB seeding validated
- Batch run completes; correlation/factor tables populated
- Auth works; portfolio ID resolvable
- Diversification score returns a sane value (0–1) with correct metadata
- (When implemented) correlation matrix and factor endpoints return expected shapes

---

References:
- CLAUDE.md (root): High‑level workflows + gotchas
- BACKEND_INITIAL_COMPLETE_WORKFLOW_GUIDE.md: Environment + project bring‑up
- BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md: Regular workflows and validation
