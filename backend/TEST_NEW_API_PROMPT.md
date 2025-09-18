# SigmaSight Backend API Testing Guide (End‑to‑End Validation)

Purpose: Provide a comprehensive, repeatable testing framework for all SigmaSight Backend API endpoints including Analytics, Target Prices, Raw Data, Authentication, and Chat APIs.

This guide supports testing against a real Postgres DB with seeded demo data, batch processing outputs, and optional LLM connections.

**Supported API Categories:**
- **Authentication APIs**: Login, logout, token refresh, user management
- **Raw Data APIs**: Portfolio data, positions, market data, data quality
- **Analytics APIs**: Correlation matrix, diversification score, factor exposures
- **Target Prices APIs**: CRUD operations, bulk actions, CSV import/export ⭐ **NEWLY IMPLEMENTED**
- **Chat APIs**: Conversation management, SSE streaming, LLM integration

---

## Quick Start (For Experienced Developers)

```bash
# One-liner setup and test (assumes Docker running, .env configured)
cd backend && \
docker compose up -d postgres && \
uv run python scripts/reset_and_seed.py seed && \
uv run python scripts/data_operations/populate_target_prices_via_service.py --csv-file data/target_prices_import.csv --execute && \
uv run python -c "from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2; import asyncio; asyncio.run(batch_orchestrator_v2.run())" && \
uv run uvicorn app.main:app --reload &

# Quick test - multiple API categories
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login -H 'Content-Type: application/json' -d '{"email":"demo_hnw@sigmasight.com","password":"demo12345"}' | jq -r .access_token)
PORTFOLIO_ID=$(curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me | jq -r .portfolio_id)

# Test Analytics API
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/analytics/portfolio/$PORTFOLIO_ID/correlation-matrix" | jq

# Test Target Prices API
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/target-prices/portfolio/$PORTFOLIO_ID" | jq

# Test Raw Data API
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/data/portfolio/$PORTFOLIO_ID/complete" | jq
```

---

## Inputs (Fill Before You Start)
- **Branch**: `APIIntegration` (or your working branch)
- **DB URL**: `postgresql+asyncpg://sigmasight:sigmasight_dev@localhost:5432/sigmasight_db`
- **Auth**: Demo user credentials (from seeding)
  - `demo_hnw@sigmasight.com / demo12345` (High Net Worth Investor)
  - `demo_individual@sigmasight.com / demo12345` (Individual Investor)  
  - `demo_hedge@sigmasight.com / demo12345` (Hedge Fund Style)
- **Portfolio ID**: Copy from DB or from `/auth/me` response
- **Test Data**: Target prices CSV populated (105 records across 3 portfolios)
- **Analytics Params**: `lookback_days=90`, `min_overlap=30` (analytics tests)
- **OpenAI Key** (optional, for chat tests): `OPENAI_API_KEY`

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

## 2) Seed Demo Data (Users, Portfolios, Positions, Factors, Target Prices)

### 2.1) Base Data Seeding
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

### 2.2) Target Prices Data
Populate target prices for comprehensive API testing:
```bash
# Populate target prices (105 records across 3 portfolios)
uv run python scripts/data_operations/populate_target_prices_via_service.py \
  --csv-file data/target_prices_import.csv --execute
```
Expected output: 105 target price records created (35 symbols × 3 portfolios)

### 2.3) Validation
Validate all seeded data:
```bash
# Validate base data
uv run python scripts/reset_and_seed.py validate

# Validate target prices
uv run python -c "
import asyncio
from app.database import AsyncSessionLocal
from app.models.target_prices import TargetPrice
from sqlalchemy import select, func

async def verify():
    async with AsyncSessionLocal() as db:
        count = await db.scalar(select(func.count(TargetPrice.id)))
        print(f'Target price records: {count}')
        
asyncio.run(verify())
"
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

### 5.1) Standard Authentication (curl)

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

### 5.2) Authentication Troubleshooting

⚠️ **IMPORTANT**: Bearer token authentication with curl can fail in certain shell environments or with complex tokens. If you encounter 401 Unauthorized errors despite correct credentials, use the Python alternative below.

**Common Issues:**
- Token not being passed correctly in shell variable expansion
- Special characters in token causing shell escaping issues
- Header formatting issues with curl

**Verification Steps:**
```bash
# Verify token was captured
echo "Token length: ${#TOKEN}"
echo "First 50 chars: ${TOKEN:0:50}..."

# Test token directly (should return user info)
curl -v -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me 2>&1 | grep -E "(401|200|portfolio_id)"

# If 401, check token format
echo $TOKEN | cut -d. -f2 | base64 -d 2>/dev/null | jq .exp || echo "Token decode failed"
```

### 5.3) Python Alternative (Recommended for Automation)

If curl authentication fails, use this Python script for reliable authentication:

```python
#!/usr/bin/env python
"""Reliable authentication test for SigmaSight API"""

import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost:8000"
EMAIL = "demo_hnw@sigmasight.com"
PASSWORD = "demo12345"

# Login
login_response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    json={"email": EMAIL, "password": PASSWORD}
)

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.status_code}")
    print(login_response.text)
    sys.exit(1)

token = login_response.json().get("access_token")
if not token:
    print("❌ No token received")
    sys.exit(1)

print(f"✅ Got token: {token[:50]}...")

# Verify authentication
headers = {"Authorization": f"Bearer {token}"}
me_response = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)

if me_response.status_code != 200:
    print(f"❌ Auth verification failed: {me_response.status_code}")
    print(me_response.text)
    sys.exit(1)

user_data = me_response.json()
portfolio_id = user_data.get("portfolio_id")
print(f"✅ Auth works - Portfolio ID: {portfolio_id}")
print(f"✅ User: {user_data.get('email')}")

# Export for use in bash if needed
print(f"\n# Export these for bash testing:")
print(f"export TOKEN='{token}'")
print(f"export PORTFOLIO_ID='{portfolio_id}'")
```

Save as `test_auth.py` and run:
```bash
uv run python test_auth.py
# Then source the exports if using bash afterward
eval $(uv run python test_auth.py | tail -2)
```

### 5.4) Quick Auth Test Function

Add to your shell for quick auth testing:
```bash
# Add to ~/.bashrc or ~/.zshrc
test_sigmasight_auth() {
    local TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
        -H 'Content-Type: application/json' \
        -d '{"email":"demo_hnw@sigmasight.com","password":"demo12345"}' | jq -r .access_token)
    
    if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
        echo "❌ Failed to get token"
        return 1
    fi
    
    local RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me)
    local PORTFOLIO_ID=$(echo "$RESPONSE" | jq -r .portfolio_id)
    
    if [ "$PORTFOLIO_ID" = "null" ]; then
        echo "❌ Auth failed - no portfolio_id"
        echo "Response: $RESPONSE"
        return 1
    fi
    
    echo "✅ Auth successful"
    echo "Token: ${TOKEN:0:50}..."
    echo "Portfolio ID: $PORTFOLIO_ID"
    export TOKEN
    export PORTFOLIO_ID
}

# Usage
test_sigmasight_auth
```

---

## 6) API Testing Framework

### 6.1) Smoke Tests (Core Data APIs)

Verify basic API functionality across all categories:

**Raw Data APIs:**
```bash
# List portfolios
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/data/portfolios | jq

# Portfolio complete data
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/data/portfolio/$PORTFOLIO_ID/complete | jq

# Data quality check
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/data/portfolio/$PORTFOLIO_ID/data-quality | jq
```

**Authentication APIs:**
```bash
# Current user info
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me | jq

# Token refresh
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/auth/refresh | jq
```

**Health Check:**
```bash
# API health
curl -s http://localhost:8000/health | jq

# OpenAPI documentation
curl -s http://localhost:8000/openapi.json | jq '.info'
```

### 6.2) General API Testing Patterns

**Endpoint Discovery:**
```bash
# List all endpoints
curl -s http://localhost:8000/openapi.json | jq '.paths | keys[]' | sort

# Check specific endpoint registration
curl -s http://localhost:8000/openapi.json | jq '.paths | keys[] | select(contains("target-prices"))'

# Verify implementation exists
grep -r "target-prices" app/api/v1/
```

**Error Response Testing (Universal Patterns):**
```bash
# Test with invalid portfolio ID
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/[endpoint]/invalid-uuid" | jq

# Test without authentication
curl -s "http://localhost:8000/api/v1/[endpoint]/$PORTFOLIO_ID" | jq

# Test with malformed data
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"invalid": "data"}' \
  "http://localhost:8000/api/v1/[endpoint]/$PORTFOLIO_ID" | jq
```

**Performance Testing Pattern:**
```bash
# Time any endpoint
echo "Timing [endpoint]:"
time curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/[endpoint]/$PORTFOLIO_ID" | jq '.metadata // .data // empty'
```

---

## 7) Specific API Category Tests

### 7.A) Target Prices APIs (COMPREHENSIVE - 10 Endpoints) ⭐

**Prerequisites:** Target prices data must be seeded (see section 2.2)

#### 7.A.1) Read Operations

**List Target Prices (GET /target-prices/portfolio/{id}):**
```bash
# List all target prices for portfolio
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/target-prices/portfolio/$PORTFOLIO_ID" | jq

# With pagination
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/target-prices/portfolio/$PORTFOLIO_ID?limit=10&offset=0" | jq

# Filter by symbol
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/target-prices/portfolio/$PORTFOLIO_ID?symbol=AAPL" | jq
```

**Get Individual Target Price (GET /target-prices/{id}):**
```bash
# First get a target price ID
TARGET_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/target-prices/portfolio/$PORTFOLIO_ID?limit=1" | jq -r '.target_prices[0].id')

# Get specific target price
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/target-prices/$TARGET_ID" | jq
```

#### 7.A.2) Create Operations  

**Create Single Target Price (POST /target-prices/portfolio/{id}):**
```bash
# Create new target price
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "symbol": "TEST",
    "position_type": "LONG", 
    "target_price_eoy": 150.00,
    "target_price_next_year": 180.00,
    "downside_target_price": 120.00,
    "current_price": 140.00,
    "analyst_notes": "Test target price"
  }' \
  "http://localhost:8000/api/v1/target-prices/portfolio/$PORTFOLIO_ID" | jq
```

**Bulk Create (POST /target-prices/portfolio/{id}/bulk):**
```bash
# Create multiple target prices
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "target_prices": [
      {
        "symbol": "TEST1",
        "position_type": "LONG",
        "target_price_eoy": 100.00,
        "target_price_next_year": 110.00,
        "downside_target_price": 80.00,
        "current_price": 95.00
      },
      {
        "symbol": "TEST2", 
        "position_type": "LONG",
        "target_price_eoy": 200.00,
        "target_price_next_year": 220.00,
        "downside_target_price": 160.00,
        "current_price": 190.00
      }
    ]
  }' \
  "http://localhost:8000/api/v1/target-prices/portfolio/$PORTFOLIO_ID/bulk" | jq
```

#### 7.A.3) Update Operations

**Update Target Price (PUT /target-prices/{id}):**
```bash
# Update existing target price
curl -s -X PUT -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "target_price_eoy": 160.00,
    "target_price_next_year": 190.00,
    "analyst_notes": "Updated target price"
  }' \
  "http://localhost:8000/api/v1/target-prices/$TARGET_ID" | jq
```

**Bulk Update (PUT /target-prices/portfolio/{id}/bulk):**
```bash
# Update multiple target prices
curl -s -X PUT -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "updates": [
      {
        "id": "'$TARGET_ID'",
        "target_price_eoy": 170.00,
        "analyst_notes": "Bulk update test"
      }
    ]
  }' \
  "http://localhost:8000/api/v1/target-prices/portfolio/$PORTFOLIO_ID/bulk" | jq
```

#### 7.A.4) Delete Operations

**Delete Target Price (DELETE /target-prices/{id}):**
```bash
# Delete specific target price
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/target-prices/$TARGET_ID" | jq
```

**Bulk Delete (DELETE /target-prices/portfolio/{id}/bulk):**
```bash
# Delete multiple target prices
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "target_price_ids": ["'$TARGET_ID'"]
  }' \
  "http://localhost:8000/api/v1/target-prices/portfolio/$PORTFOLIO_ID/bulk" | jq
```

#### 7.A.5) CSV Import/Export Operations

**CSV Import (POST /target-prices/portfolio/{id}/import):**
```bash
# Import from CSV file
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -F "file=@data/target_prices_import.csv" \
  -F "update_existing=false" \
  "http://localhost:8000/api/v1/target-prices/portfolio/$PORTFOLIO_ID/import" | jq

# Expected response: {"created": N, "updated": 0, "errors": [], "total": N}
```

**CSV Export (GET /target-prices/portfolio/{id}/export):**
```bash
# Export to CSV
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/target-prices/portfolio/$PORTFOLIO_ID/export" \
  > exported_target_prices.csv

# Verify export
head -5 exported_target_prices.csv
wc -l exported_target_prices.csv
```

#### 7.A.6) Target Prices Validation Tests

**Data Integrity:**
```bash
# Verify expected returns are calculated
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/target-prices/portfolio/$PORTFOLIO_ID?symbol=AAPL" | \
  jq '.target_prices[0] | {
    symbol,
    target_price_eoy,
    current_price,
    expected_return_eoy,
    calculated_return: ((.target_price_eoy / .current_price - 1) * 100)
  }'
```

**Error Handling:**
```bash
# Test duplicate creation (should fail)
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "symbol": "AAPL",
    "position_type": "LONG",
    "target_price_eoy": 250.00
  }' \
  "http://localhost:8000/api/v1/target-prices/portfolio/$PORTFOLIO_ID" | jq

# Test invalid data types
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "symbol": "INVALID",
    "target_price_eoy": "not_a_number"
  }' \
  "http://localhost:8000/api/v1/target-prices/portfolio/$PORTFOLIO_ID" | jq
```

**Performance Testing:**
```bash
# Time target prices list (should be < 500ms for 35 records)
echo "Timing target prices list:"
time curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/target-prices/portfolio/$PORTFOLIO_ID" | \
  jq '.target_prices | length'

# Time CSV export (should be < 1s)
echo "Timing CSV export:"
time curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/target-prices/portfolio/$PORTFOLIO_ID/export" | wc -l
```

### 7.B) Analytics APIs (Correlation, Diversification, Factors)

**Prerequisites:** Batch processing must be completed (see section 3)

#### 7.B.1) Correlation Matrix (IMPLEMENTED)
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

Quick one-shot validation script (read-only):
```bash
# Validates 7-factor complete set and 7 factors on first two positions
chmod +x backend/scripts/test_factor_exposures.sh
BASE_URL=http://localhost:8000/api/v1 \
EMAIL=demo_hnw@sigmasight.com \
PASSWORD=demo12345 \
backend/scripts/test_factor_exposures.sh
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

### 10.1) Environment & Data
- ✅ Backend starts without errors (`uvicorn app.main:app --reload`)
- ✅ Database seeding validated (3 users, 3 portfolios, 60+ positions)
- ✅ Target prices populated (105 records across 3 portfolios)
- ✅ Batch processing completed (correlation/factor tables populated)

### 10.2) Authentication & Authorization
- ✅ Auth works; JWT tokens generated successfully
- ✅ Portfolio ID resolvable via `/auth/me`
- ✅ Token refresh functionality working
- ✅ Authorization correctly restricts access to portfolio-specific data

### 10.3) API Category Testing

**Raw Data APIs:**
- ✅ Portfolio complete data returns without errors
- ✅ Data quality checks provide meaningful metrics
- ✅ Pagination works correctly for large datasets

**Target Prices APIs (COMPREHENSIVE - 10 endpoints):**
- ✅ List target prices returns 35 records per portfolio
- ✅ CRUD operations (Create, Read, Update, Delete) function correctly
- ✅ Bulk operations handle multiple records efficiently
- ✅ CSV import processes 35 symbols successfully
- ✅ CSV export generates valid CSV format
- ✅ Expected returns calculated automatically (e.g., AAPL: ~45% EOY)
- ✅ Data validation prevents duplicate records
- ✅ Performance: List < 500ms, CSV export < 1s

**Analytics APIs:**
- ✅ Diversification score returns value ∈ [0,1] with correct metadata
- ✅ Correlation matrix returns expected dimensions when data available
- ✅ Factor exposures provide comprehensive coverage (when implemented)

**Chat APIs (Optional):**
- ✅ SSE streaming works for LLM interactions
- ✅ Conversation management functional

### 10.4) Performance Benchmarks
- Target Prices list: < 500ms for 35 records
- CSV export: < 1s for 35 records
- Analytics endpoints: < 2s for complex calculations
- Authentication: < 100ms for token operations

### 10.5) Error Handling
- ✅ Invalid UUIDs return appropriate 400/404 errors
- ✅ Missing authentication returns 401 Unauthorized
- ✅ Malformed data returns 422 Validation Error
- ✅ Non-existent resources return 404 Not Found
- ✅ Duplicate creation attempts handled gracefully

---

## References & Documentation

**Core Setup & Workflows:**
- `CLAUDE.md` (root): High‑level workflows + gotchas
- `BACKEND_INITIAL_COMPLETE_WORKFLOW_GUIDE.md`: Environment + project bring‑up
- `BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md`: Regular workflows and validation

**API Documentation:**
- `_docs/requirements/API_SPECIFICATIONS_V1.4.5.md`: Complete API specifications
- Target Prices section E (APIs 23-32): Detailed endpoint documentation

**Target Prices Implementation:**
- `README_TARGET_PRICES_IMPORT.md`: CSV import/export guide with rationale
- `app/api/v1/target_prices.py`: Full API implementation (10 endpoints)
- `app/services/target_price_service.py`: Business logic and service layer
- `data/target_prices_import.csv`: Sample data (35 symbols, 3 portfolios)

**Testing & Validation:**
- `scripts/data_operations/populate_target_prices_via_service.py`: Data seeding script
- `scripts/reset_and_seed.py`: Core data seeding and validation
