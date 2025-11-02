# Code Review Follow-Up #2 - Test Improvements

**Date**: 2025-10-29
**Status**: ⚠️ Partial - Recommendations Needed

---

## Summary

This document addresses the second round of follow-up feedback on the test suite, specifically:

1. **Issue #9**: test_position_import_service.py tests never call `import_positions()` (would not have caught abs(quantity) bug)
2. **Issue #10**: conftest.py monkeypatch targets incorrect (would raise AttributeError if used)

---

## Issue #9: Missing Database Integration Tests ⚠️ CRITICAL

**File**: `tests/unit/test_position_import_service.py`

### Problem

The reviewer correctly identified that all 21 tests in `test_position_import_service.py` only test:
- `PositionData` objects (in-memory dataclasses)
- `determine_position_type()` static method

But **none of them call** `PositionImportService.import_positions()`, which is the method that had the `abs(quantity)` bug on line 227.

**Why this matters**: The abs(quantity) regression would still have slipped through even with all 21 tests passing.

### What We Did

Added a new test class `TestPositionImportServiceDatabaseIntegration` with 2 tests:

1. **`test_import_positions_preserves_signed_quantity`** - CRITICAL test that:
   - Creates PositionData with negative quantities (short positions)
   - Calls `import_positions()` to persist to database
   - Queries database to verify `Position.quantity` stayed negative
   - **Would have caught the abs(quantity) bug**

2. **`test_import_positions_maps_option_fields`** - Verifies:
   - underlying_symbol correctly mapped
   - strike_price correctly mapped
   - expiration_date string → date conversion
   - option_type stored in position_type enum

### Current Status: ⚠️ Blocked

**Problem**: These tests require a real database but are in the `unit/` directory.

**Technical Issue**:
- Created pytest_asyncio fixture `test_db_with_tables` using SQLite in-memory database
- SQLite in-memory databases are connection-specific
- Table created in fixture doesn't persist to session used by test
- Tests fail with "no such table: positions"

**Why SQLite doesn't work**:
```python
# This pattern doesn't work with SQLite :memory:
async with engine.begin() as conn:
    await conn.run_sync(Position.__table__.create)  # Creates table on Connection A

async_session = async_sessionmaker(engine, ...)
async with async_session() as session:  # Uses Connection B (different connection!)
    # Table doesn't exist here
```

### Recommended Solution

**Option 1: Move to integration tests** (RECOMMENDED)

Move `TestPositionImportServiceDatabaseIntegration` to `tests/integration/test_position_import.py`:

```python
# tests/integration/test_position_import.py
import pytest
from uuid import uuid4
from decimal import Decimal
from sqlalchemy import select

from app.database import AsyncSessionLocal  # Use real database
from app.services.position_import_service import PositionImportService
from app.models.positions import Position

class TestPositionImportIntegration:
    @pytest.mark.asyncio
    async def test_import_positions_preserves_signed_quantity(self):
        """CRITICAL: Verify signed quantities persist to real database"""
        async with AsyncSessionLocal() as db:
            portfolio_id = uuid4()
            user_id = uuid4()

            # Test data with negative quantities
            positions_data = [
                PositionData(symbol="SHOP", quantity=Decimal("-25"), ...),  # Short
                PositionData(symbol="QQQ_PUT", quantity=Decimal("-15"), ...),  # Short put
            ]

            # Act: Import to real database
            result = await PositionImportService.import_positions(
                db=db, portfolio_id=portfolio_id,
                user_id=user_id, positions_data=positions_data
            )
            await db.commit()

            # Assert: Query and verify signed quantities
            db_result = await db.execute(
                select(Position).where(Position.portfolio_id == portfolio_id)
            )
            positions = db_result.scalars().all()

            shop = next(p for p in positions if p.symbol == "SHOP")
            assert shop.quantity == Decimal("-25"), "Short quantity MUST stay negative!"

            # Cleanup
            for p in positions:
                await db.delete(p)
            await db.commit()
```

**Why this is better**:
- Uses real PostgreSQL database (matches production)
- No SQLite compatibility issues
- Truly tests the database persistence layer
- Cleanup logic is straightforward

**Option 2: Fix SQLite fixture** (NOT RECOMMENDED)

Make SQLite in-memory database work by using the same connection for both table creation and queries. Complex and fragile - not worth the effort.

---

## Issue #10: Incorrect Monkeypatch Targets ✅ FIXED

**File**: `tests/conftest.py:140-195`

### Problem

The mock fixtures tried to patch module-level attributes that don't exist:

```python
# ❌ WRONG - these attributes don't exist
monkeypatch.setattr("app.services.price_cache_service.bootstrap_prices", ...)
monkeypatch.setattr("app.services.preprocessing_service.prepare_portfolio_for_batch", ...)
```

The actual code uses singleton instances:
```python
# app/services/price_cache_service.py
class PriceCacheService:
    async def bootstrap_prices(self, db, symbols, days=30): ...

price_cache_service = PriceCacheService()  # Singleton instance

# Actual usage in code
from app.services.price_cache_service import price_cache_service
await price_cache_service.bootstrap_prices(db, symbols)
```

**Impact**: If these fixtures were used in tests, they would raise `AttributeError: module has no attribute 'bootstrap_prices'`

### Fix Applied

Updated monkeypatch targets to patch the singleton instances directly:

```python
# ✅ CORRECT - patch singleton instances
from app.services.price_cache_service import price_cache_service
from app.services.security_master_service import security_master_service
from app.services.preprocessing_service import preprocessing_service

monkeypatch.setattr(price_cache_service, "bootstrap_prices", mock_bootstrap_prices)
monkeypatch.setattr(security_master_service, "enrich_symbols", mock_enrich_symbols)
monkeypatch.setattr(preprocessing_service, "prepare_portfolio_for_batch", mock_prepare_portfolio)
```

### Files Changed

| File | Lines Changed | Fix |
|------|---------------|-----|
| `tests/conftest.py` | Lines 139-153 | Fixed `mock_market_data_services` fixture |
| `tests/conftest.py` | Lines 188-195 | Fixed `mock_preprocessing_service` fixture |

### Testing the Fixes

The fixtures can now be used in integration tests:

```python
def test_portfolio_creation(client, mock_market_data_services):
    """Test portfolio creation without hitting external APIs"""
    # All YFinance/Polygon/FMP calls are properly mocked
    response = client.post("/api/v1/onboarding/create-portfolio", ...)
    assert response.status_code == 201
```

---

## Recommendations for Next Steps

### 1. Database Integration Tests (Priority: HIGH)

**Recommendation**: Create `tests/integration/test_position_import.py` with the database integration tests.

**Why**: These tests are critical for catching abs(quantity) bugs and truly belong in the integration test suite.

**Action Items**:
- [ ] Create `tests/integration/test_position_import.py`
- [ ] Move `test_import_positions_preserves_signed_quantity` test
- [ ] Move `test_import_positions_maps_option_fields` test
- [ ] Use real PostgreSQL database (AsyncSessionLocal)
- [ ] Add proper cleanup in test teardown

### 2. Wire Mocks into Integration Tests (Priority: MEDIUM)

**Current State**: The mock fixtures in conftest.py are fixed but not used anywhere.

**Recommendation**: Apply `mock_market_data_services` fixture to integration tests:

```python
# tests/integration/test_onboarding_api.py
class TestCreatePortfolioEndpoint:
    def test_valid_portfolio_creation(self, client, mock_market_data_services):
        """Test portfolio creation without hitting external APIs"""
        # Mocks prevent network calls
        response = client.post("/api/v1/onboarding/create-portfolio", ...)
        assert response.status_code == 201
```

**Benefits**:
- Tests run faster (no network calls)
- Tests more reliable (no flaky API failures)
- Tests work offline

### 3. Documentation Updates (Priority: LOW)

- [ ] Update `ONBOARDING_TESTS.md` with integration test location
- [ ] Document mock fixture usage patterns
- [ ] Add example of using mocks in integration tests

---

## Summary of Work Done

### ✅ Completed

1. **Fixed conftest.py monkeypatch targets** (Issue #10)
   - Updated `mock_market_data_services` to patch singleton instances
   - Updated `mock_preprocessing_service` to patch singleton instance
   - Fixtures now work correctly without AttributeError

2. **Created database integration test code** (Issue #9)
   - Written `test_import_positions_preserves_signed_quantity` (critical test)
   - Written `test_import_positions_maps_option_fields`
   - Both tests verify actual database persistence

### ⚠️ Blocked / Needs Decision

1. **Database integration tests location** (Issue #9)
   - Tests written but can't run in `unit/` directory
   - SQLite in-memory database technical issues
   - **Decision needed**: Move to `tests/integration/` or fix SQLite fixture?

### 📋 Recommended Next Steps

1. **Immediate**: Move database integration tests to `tests/integration/test_position_import.py`
2. **Short-term**: Wire mock fixtures into existing integration tests
3. **Long-term**: Add more database integration tests for other services

---

## Technical Notes

### Why SQLite In-Memory Doesn't Work for These Tests

SQLite in-memory databases (`sqlite:///:memory:`) create a new database for each connection. When using async SQLAlchemy:

1. `engine.begin()` gets Connection A
2. Create tables on Connection A
3. `async_session()` gets Connection B (different connection!)
4. Tables don't exist on Connection B

**Solution**: Use same connection for entire test or use real PostgreSQL database.

### Singleton Service Pattern

All SigmaSight services use the singleton pattern:

```python
# Service definition
class ServiceName:
    def method(self): ...

# Singleton instance (at bottom of file)
service_name = ServiceName()

# Usage in application code
from app.services.module import service_name
await service_name.method()
```

**Monkeypatch target**: Always patch the singleton instance, not the module.

---

## Files Modified

| File | Purpose | Status |
|------|---------|--------|
| `tests/conftest.py` | Fixed monkeypatch targets | ✅ Complete |
| `tests/unit/test_position_import_service.py` | Added database tests | ⚠️ Blocked (need to move to integration/) |

---

**Status**: ⚠️ Partial completion - Issue #10 fixed, Issue #9 needs location decision
**Recommendation**: Move database integration tests to `tests/integration/` directory
