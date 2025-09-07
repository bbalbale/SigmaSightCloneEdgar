# Backend Test Prompt (End‑to‑End Validation)

Purpose: Provide a repeatable, code‑first checklist to bring up SigmaSight Backend locally and validate new API endpoints against a real Postgres DB, seeded demo data, batch outputs, and (optionally) LLM connections.

Use this to verify endpoints like analytics/correlation‑matrix, diversification‑score, factor exposures, etc., after implementation.

---

## Quick Start (For Experienced Developers)

```bash
# One-liner setup and test (assumes Docker running, .env configured)
cd backend && \
docker compose up -d postgres && \
uv run python scripts/reset_and_seed.py seed && \
uv run python -c "from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2; import asyncio; asyncio.run(batch_orchestrator_v2.run())" && \
uv run uvicorn app.main:app --reload &

# Quick test
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login -H 'Content-Type: application/json' -d '{"email":"demo_hnw@sigmasight.com","password":"demo12345"}' | jq -r .access_token)
PORTFOLIO_ID=$(curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me | jq -r .portfolio_id)
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/analytics/portfolio/$PORTFOLIO_ID/correlation-matrix" | jq
```

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

### 4.1) Verify Endpoint Implementation
Before testing, confirm endpoint exists:
```bash
# Check if endpoint is registered
curl -s http://localhost:8000/openapi.json | jq '.paths | keys[] | select(contains("correlation"))'

# Check implementation status
grep -r "correlation-matrix" app/api/v1/

# Verify service layer exists
ls -la app/services/ | grep correlation
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

### 7.A) Positive Test Cases

A) Correlation Matrix (3.0.3.10 – IMPLEMENTED)
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
  - Flat metadata fields (not nested `parameters_used`)
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

### 7.B) Error Response Testing
Test edge cases and error conditions:
```bash
# Test with invalid portfolio ID
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/analytics/portfolio/invalid-uuid/diversification-score" | jq

# Test with missing authentication
curl -s "http://localhost:8000/api/v1/analytics/portfolio/$PORTFOLIO_ID/diversification-score" | jq

# Test with invalid parameters
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/analytics/portfolio/$PORTFOLIO_ID/correlation-matrix?lookback_days=-1" | jq

# Test with non-existent portfolio
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/analytics/portfolio/00000000-0000-0000-0000-000000000000/diversification-score" | jq
```

### 7.C) Response Structure Validation
Validate response format and data integrity:
```bash
# Validate diversification score structure
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/analytics/portfolio/$PORTFOLIO_ID/diversification-score?lookback_days=90" | \
  jq 'if .available then 
    if (.portfolio_correlation >= 0 and .portfolio_correlation <= 1) then 
      "✅ Valid response" 
    else 
      "❌ Invalid correlation value: \(.portfolio_correlation)" 
    end 
  else 
    "⚠️ No data: " + .reason 
  end'

# Validate correlation matrix dimensions
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/analytics/portfolio/$PORTFOLIO_ID/correlation-matrix?max_symbols=10" | \
  jq 'if .available then 
    if (.data.matrix | length) == (.data.symbols | length) then 
      "✅ Matrix dimensions match: \(.data.symbols | length)x\(.data.symbols | length)" 
    else 
      "❌ Matrix dimension mismatch" 
    end 
  else 
    "⚠️ No data: " + .reason 
  end'
```

### 7.D) Performance Testing
Measure endpoint response times:
```bash
# Time correlation matrix endpoint
echo "Timing correlation matrix (25 symbols):"
time curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/analytics/portfolio/$PORTFOLIO_ID/correlation-matrix?max_symbols=25" | \
  jq '.metadata | {calculation_date, symbols_included, duration_days}'

# Time diversification score
echo "Timing diversification score:"
time curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/analytics/portfolio/$PORTFOLIO_ID/diversification-score" | \
  jq '.metadata'

# Expected: < 1s for 25 symbols, < 2s for 50 symbols
```

### 7.E) Debug Script Generation
For complex debugging, create a standalone test script:
```bash
# Create test_analytics.py
cat > test_analytics.py << 'EOF'
import asyncio
from app.database import AsyncSessionLocal
from app.services.correlation_service import CorrelationService
from uuid import UUID
import json

PORTFOLIO_ID = "$PORTFOLIO_ID"  # Replace with actual ID

async def test_correlation():
    async with AsyncSessionLocal() as session:
        service = CorrelationService(session)
        result = await service.get_correlation_matrix(
            UUID(PORTFOLIO_ID), 90, 30, 25
        )
        print("Correlation Matrix Result:")
        print(json.dumps(result, indent=2, default=str))
        
        div_score = await service.get_diversification_score(
            UUID(PORTFOLIO_ID), 90, 30
        )
        print("\nDiversification Score Result:")
        print(json.dumps(div_score, indent=2, default=str))

asyncio.run(test_correlation())
EOF

# Run the debug script
uv run python test_analytics.py
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

### 9.1) Common Issues

- **Database empty or wrong IDs**
  - Re‑seed: `uv run python scripts/reset_and_seed.py seed`
  - Validate: `uv run python scripts/reset_and_seed.py validate`
  
- **No correlation data**
  - Run batch: `uv run python -c "from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2; import asyncio; asyncio.run(batch_orchestrator_v2.run())"`
  - Lower `min_overlap` (e.g., 10) for sparse data
  
- **Auth errors**
  - Ensure token is set, or re‑login
  - Check token expiry: `echo $TOKEN | cut -d. -f2 | base64 -d | jq .exp`
  
- **SSE issues**
  - Check CORS and cookies if testing via a browser client
  - Using curl with Bearer token avoids cookie complications

### 9.2) Schema Validation Issues

Debug Pydantic validation errors (500 with "value is not a valid dict"):
```bash
# Monitor server logs for validation errors
tail -f server.log | grep -A 10 "validation error"

# Common schema issues:
# - Nested dicts in metadata (should be flat Dict[str, Union[str, int, float]])
# - Missing required fields in response
# - Type mismatches (e.g., returning string instead of float)

# Debug with detailed error output
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/analytics/portfolio/$PORTFOLIO_ID/correlation-matrix" 2>&1 | \
  jq '.detail' || echo "Check server logs for full error"
```

### 9.3) Database Verification

Verify batch data exists before testing:
```bash
# Check correlation calculations
uv run python -c "
from app.database import AsyncSessionLocal
import asyncio

async def check():
    async with AsyncSessionLocal() as db:
        # Check correlation calculations
        result = await db.execute('SELECT COUNT(*) FROM correlation_calculations')
        corr_count = result.scalar()
        print(f'Correlation calculations: {corr_count}')
        
        # Check pairwise correlations
        result = await db.execute('SELECT COUNT(*) FROM pairwise_correlations')
        pair_count = result.scalar()
        print(f'Pairwise correlations: {pair_count}')
        
        # Check factor exposures
        result = await db.execute('SELECT COUNT(*) FROM position_factor_exposures')
        factor_count = result.scalar()
        print(f'Factor exposures: {factor_count}')
        
        if corr_count == 0:
            print('⚠️ No correlation data - run batch processing')
        if factor_count == 0:
            print('⚠️ No factor data - run batch processing')

asyncio.run(check())
"

# Check specific portfolio data
uv run python -c "
from app.database import AsyncSessionLocal
from uuid import UUID
import asyncio

PORTFOLIO_ID = '$PORTFOLIO_ID'

async def check_portfolio():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            'SELECT COUNT(*) FROM positions WHERE portfolio_id = :pid',
            {'pid': UUID(PORTFOLIO_ID)}
        )
        print(f'Positions in portfolio: {result.scalar()}')
        
        result = await db.execute(
            'SELECT COUNT(DISTINCT symbol) FROM positions WHERE portfolio_id = :pid',
            {'pid': UUID(PORTFOLIO_ID)}
        )
        print(f'Unique symbols: {result.scalar()}')

asyncio.run(check_portfolio())
"
```

### 9.4) Server Log Analysis

Extract and analyze errors from server logs:
```bash
# Find all 500 errors
grep "500 Internal Server Error" server.log | tail -5

# Find validation errors with context
grep -B 5 -A 10 "ValidationError" server.log | tail -50

# Find specific endpoint errors
grep -A 20 "correlation-matrix" server.log | grep -E "(ERROR|Exception|Traceback)"

# Live monitoring during tests
tail -f server.log | grep --line-buffered -E "(correlation|diversification|factor)" &
MONITOR_PID=$!

# Run your tests here...

# Stop monitoring
kill $MONITOR_PID
```

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
