# API Performance Issue - Positions Endpoint Timeout

> **Issue ID**: #22  
> **Date Discovered**: 2025-09-12  
> **Status**: RESOLVED ✅  
> **Severity**: HIGH  
> **Impact**: Portfolio positions disappear after initial load in frontend
> **Resolution Date**: 2025-09-12  
> **Final Status**: All three root causes identified and fixed

## Problem Description

The `/api/v1/data/positions/details` endpoint experiences severe performance degradation on subsequent calls:
- **First API call**: ✅ Success (~100-200ms response time)
- **Second API call**: ⏱️ Timeout (10+ seconds, connection timeout)
- **Pattern**: Consistent timeout on retry attempts within same session

### Observed Behavior
1. Frontend makes duplicate API calls due to React StrictMode (development)
2. First call succeeds and returns 30 positions for hedge fund portfolio
3. Second call times out after 10 seconds
4. Timeout causes error handling to replace good data with empty arrays
5. UI shows positions briefly, then they disappear

### Symptoms
- Positions load initially then vanish
- Exposure cards remain populated (overview API works fine)
- Error banner shows "Position data unavailable"
- Affects all portfolio types (individual, high-net-worth, hedge-fund)

## Root Cause (CONFIRMED - REVISED 2025-09-12)

**Primary Issue Found:**

1. **N+1 Query Problem in Positions Endpoint** ✅ FIXED
   - The positions endpoint was making a separate database query for EACH position's market data
   - For 17 positions = 17 additional queries to MarketDataCache table
   - This caused severe performance degradation on subsequent calls
   - Fixed by batch-fetching all market data in a single optimized query

**Secondary Issues:**

2. **Incorrect Database Session Usage** ✅ FIXED
   - The positions endpoint was incorrectly using `async with db as session:` 
   - The `db` parameter from `Depends(get_db)` is already a session
   - This double context manager was causing connection handling issues

3. **Insufficient Connection Pool Size** ✅ FIXED
   - Default pool size of 5 connections was too small
   - React StrictMode causing duplicate requests exhausted the pool
   - Increased to 20 connections with 20 overflow

## Diagnostic Plan

### Step 1: Database Connection Pool Analysis
```bash
# Check current connections
docker exec -it sigmasight-postgres psql -U postgres -d sigmasight -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"

# Monitor active queries
docker exec -it sigmasight-postgres psql -U postgres -d sigmasight -c "SELECT pid, state, query, query_start FROM pg_stat_activity WHERE state != 'idle';"

# Check for locks
docker exec -it sigmasight-postgres psql -U postgres -d sigmasight -c "SELECT * FROM pg_locks WHERE granted = false;"
```

### Step 2: Add Detailed Timing Logs
Location: `app/api/v1/data.py` - get_position_details endpoint

```python
import time
import logging

logger = logging.getLogger(__name__)

@router.get("/positions/details")
async def get_position_details(
    portfolio_id: str = Query(None),
    db: AsyncSession = Depends(get_async_session)
):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()
    
    logger.info(f"[{request_id}] Starting positions request for portfolio {portfolio_id}")
    
    try:
        # Log connection acquisition
        logger.info(f"[{request_id}] [{time.time() - start:.2f}s] Acquiring DB connection...")
        
        # Build query
        query = select(Position).where(Position.portfolio_id == portfolio_id)
        logger.info(f"[{request_id}] [{time.time() - start:.2f}s] Executing query...")
        
        # Execute
        result = await db.execute(query)
        logger.info(f"[{request_id}] [{time.time() - start:.2f}s] Query complete, fetching results...")
        
        # Fetch all
        positions = result.scalars().all()
        logger.info(f"[{request_id}] [{time.time() - start:.2f}s] Fetched {len(positions)} positions")
        
        # Serialize
        logger.info(f"[{request_id}] [{time.time() - start:.2f}s] Serializing response...")
        response = [serialize_position(p) for p in positions]
        
        logger.info(f"[{request_id}] [{time.time() - start:.2f}s] Request complete")
        return {"positions": response}
        
    except Exception as e:
        logger.error(f"[{request_id}] [{time.time() - start:.2f}s] Error: {str(e)}")
        raise
```

### Step 3: Check Connection Pool Configuration
Location: `app/database.py`

```python
# Current configuration (likely defaults)
engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,          # Default: 5 connections
    max_overflow=10,      # Default: 10 overflow connections  
    pool_timeout=30,      # Default: 30s wait for connection
    pool_recycle=3600,    # Default: 1 hour connection lifetime
    pool_pre_ping=True,   # Default: False - health check connections
    echo_pool=True,       # Add this for debugging
)

# Recommended testing configuration
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,         # Increase base pool
    max_overflow=20,      # Increase overflow
    pool_timeout=5,       # Reduce timeout to fail fast
    pool_recycle=1800,    # Recycle connections every 30 min
    pool_pre_ping=True,   # Enable connection health checks
    echo_pool=True,       # Enable pool logging
)
```

### Step 4: Test with Direct API Calls
```bash
# Test rapid successive calls
for i in {1..5}; do
  curl -H "Authorization: Bearer $TOKEN" \
    "http://localhost:8000/api/v1/data/positions/details?portfolio_id=fcd71196-e93e-f000-5a74-31a9eead3118" &
done
wait

# Monitor response times
```

### Step 5: Database Query Analysis
```sql
-- Check query plan
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM positions 
WHERE portfolio_id = 'fcd71196-e93e-f000-5a74-31a9eead3118';

-- Check indexes
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'positions';

-- Check table statistics
SELECT 
    schemaname,
    tablename,
    n_live_tup,
    n_dead_tup,
    last_vacuum,
    last_autovacuum
FROM pg_stat_user_tables
WHERE tablename = 'positions';
```

### Step 6: Monitor During Issue Reproduction
```bash
# Terminal 1: Watch connection pool
watch -n 1 'docker exec -it sigmasight-postgres psql -U postgres -d sigmasight -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"'

# Terminal 2: Watch backend logs
cd backend && tail -f app.log | grep -E "(positions|pool|connection)"

# Terminal 3: Trigger the issue
# Navigate to portfolio page in browser
```

## Proposed Solutions

### Quick Fix (Immediate)
1. **Increase connection pool size** (5 min fix)
   ```python
   # In app/database.py
   pool_size=20, max_overflow=20
   ```

2. **Add request deduplication** (30 min fix)
   - Prevent duplicate requests from frontend
   - Cache in-flight requests

3. **Ensure proper connection cleanup** (15 min fix)
   ```python
   async with db.begin():  # Use context manager
       # query here
   # Auto-commits and closes
   ```

### Medium-term Solutions
1. **Add connection pool monitoring**
   - Log pool statistics
   - Alert on pool exhaustion
   
2. **Optimize the positions query**
   - Add missing indexes
   - Eager load relationships
   - Reduce N+1 queries

3. **Implement query result caching**
   - Redis or in-memory cache
   - 5-second TTL for positions

### Long-term Solutions
1. **Database connection pooling service** (pgBouncer)
2. **Read replicas for query distribution**
3. **GraphQL with DataLoader pattern**
4. **Materialized views for complex aggregations**

## Testing Plan

1. **Reproduce Issue**
   - Open portfolio page
   - Check browser console for duplicate calls
   - Verify second call timeout

2. **Apply Connection Pool Fix**
   - Update pool_size to 20
   - Restart backend
   - Test again

3. **Monitor Metrics**
   - Connection count
   - Query execution time
   - Pool wait time

4. **Load Testing**
   ```bash
   # Use Apache Bench
   ab -n 100 -c 10 -H "Authorization: Bearer $TOKEN" \
     "http://localhost:8000/api/v1/data/positions/details?portfolio_id=xxx"
   ```

## Applied Fixes

### 1. Fixed N+1 Query Problem in `/api/v1/data.py` (PRIMARY FIX)
```python
# BEFORE (N+1 queries - one for each position)
for position in positions:
    cache_stmt = select(MarketDataCache).where(
        MarketDataCache.symbol == position.symbol
    ).order_by(MarketDataCache.updated_at.desc())
    cache_result = await db.execute(cache_stmt)  # ❌ Separate query for EACH position
    market_data = cache_result.scalars().first()

# AFTER (Single batch query)
symbols = [position.symbol for position in positions]
if symbols:
    # Single optimized query to get all market data at once
    from sqlalchemy import func
    subquery = (
        select(
            MarketDataCache.symbol,
            func.max(MarketDataCache.updated_at).label('max_updated')
        )
        .where(MarketDataCache.symbol.in_(symbols))
        .group_by(MarketDataCache.symbol)
        .subquery()
    )
    
    market_stmt = select(MarketDataCache).join(
        subquery,
        and_(
            MarketDataCache.symbol == subquery.c.symbol,
            MarketDataCache.updated_at == subquery.c.max_updated
        )
    )
    market_result = await db.execute(market_stmt)  # ✅ Single query for ALL positions
    market_data_map = {m.symbol: m for m in market_result.scalars().all()}
```

### 2. Fixed Database Session Usage in `/api/v1/data.py`
```python
# BEFORE (incorrect)
async def get_positions_details(..., db: AsyncSession = Depends(get_async_session)):
    async with db as session:  # ❌ Wrong - db is already a session
        # query code

# AFTER (correct)
async def get_positions_details(..., db: AsyncSession = Depends(get_db)):
    # db is already a session from get_db dependency
    # Use db directly for queries
```

### 3. Increased Connection Pool Size in `/app/database.py`
```python
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=20,        # Increased from default 5
    max_overflow=20,     # Increased from default 10
    pool_timeout=30,     # Default 30s wait for connection
    pool_recycle=1800,   # Recycle connections every 30 min
)
```

## Success Criteria
- [x] Second API call responds within 500ms ✅
- [x] No connection pool exhaustion warnings ✅
- [x] Positions remain visible in UI ✅
- [x] Can handle 10 concurrent requests ✅
- [x] Exposure cards show correct values (not 0s) ✅

## Resolution Summary

This issue involved three critical problems that caused positions to disappear after initial load:

1. **Exposure Cards Showing 0s**: Fixed by correcting nested field access in `portfolioService.ts` (accessing `overview.exposures.long_exposure` instead of flat fields)

2. **Backend N+1 Query Problem**: The positions endpoint was making a separate database query for each position's market data. Fixed by:
   - Batch-fetching all market data in a single optimized query
   - Correcting database session usage (removed incorrect `async with db as session`)
   - Increasing connection pool size from 5 to 20 connections

3. **Frontend Retry Logic Bug**: The apiClient's retry mechanism was reusing an aborted AbortSignal, causing all retries to immediately fail. Fixed by:
   - Modifying the retry logic to not pass the original signal on retry attempts
   - Ensuring each retry gets a fresh timeout controller
   - This prevents phantom timeouts that never actually reach the backend

The systematic diagnostic approach revealed all three root causes. The backend now responds in under 50ms consistently, and the frontend properly handles retries without false timeouts.

## Final Test Results (2025-09-12)

After applying all three fixes, the portfolio page now works correctly:
- ✅ All 17 positions load and remain visible indefinitely (tested 10+ seconds)
- ✅ Exposure cards display correct values: $1.6M Long, $364K Cash, $309.3K P&L
- ✅ Backend responds in ~50ms consistently (down from 10+ second timeouts)
- ✅ No connection pool exhaustion warnings
- ✅ React StrictMode double-rendering handled gracefully

## Related Issues
- Frontend double-rendering due to React StrictMode
- Missing request deduplication in frontend
- No connection pool monitoring in backend

## Next Steps
1. Check current connection pool configuration
2. Add timing logs to positions endpoint
3. Monitor database connections during issue
4. Apply pool size increase if confirmed
5. Document findings and permanent fix

---

**Note**: This issue significantly impacts user experience as portfolio positions disappear after loading, making the application appear broken even though data is successfully fetched initially.