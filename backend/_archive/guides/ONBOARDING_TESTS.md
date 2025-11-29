# Onboarding Test Suite

Comprehensive test suite for the SigmaSight User Onboarding System (TODO5.md implementation).

> 📝 **Note**: For detailed PostgreSQL migration documentation and integration test fixes (October 2025), see `_archive/migration_2025_10_29/`

## Overview

The test suite validates the complete onboarding flow from user registration through portfolio calculations, with 90+ tests covering unit, integration, and end-to-end scenarios.

**Database Strategy**: All database tests use **PostgreSQL** (no SQLite). This ensures tests match production exactly.

---

## Test Structure

```
tests/
├── unit/                                    # Unit tests (pure logic, no database)
│   ├── test_invite_code_service.py         # 9 tests ✅
│   ├── test_uuid_strategy.py               # 14 tests ✅
│   ├── test_csv_parser_service.py          # 28 tests ✅ (includes options validation)
│   └── test_position_import_service.py     # 21 tests ✅ (logic only, no database)
├── integration/                             # Integration tests (PostgreSQL required)
│   ├── test_onboarding_api.py              # 16 tests ⚠️ (event loop issues)
│   └── test_position_import.py             # 3 tests (2 passing ✅, 1 needs investigation ⚠️)
├── e2e/                                     # End-to-end tests (complete flow)
│   └── test_onboarding_flow.py             # 3 tests ✅
└── conftest.py                              # Mock fixtures for external APIs
```

---

## Running Tests

### Prerequisites

**For Unit Tests** (no prerequisites):
- Pure logic tests, no database required
- Run instantly with `uv run python -m pytest tests/unit/ -v`

**For Integration/E2E Tests**:

1. **PostgreSQL Running in Docker**:
   ```bash
   docker-compose up -d  # Start PostgreSQL
   docker ps             # Verify postgres container is running
   ```

2. **Dependencies Installed**:
   ```bash
   uv sync --extra dev   # Install pytest and other dev dependencies
   ```

**Note**: Integration tests use the **real PostgreSQL database** (not SQLite). This ensures tests match production behavior exactly.

### Run All Unit Tests

```bash
uv run python -m pytest tests/unit/ -v
```

**Expected**: 72 tests passing (100% pass rate)

### Run Integration Tests

```bash
uv run python -m pytest tests/integration/ -v
```

**Expected**: 16 tests (requires PostgreSQL running)

### Run E2E Tests

```bash
uv run python -m pytest tests/e2e/ -v
```

**Expected**: 3 tests (requires PostgreSQL running, tests complete user journey)

### Run Specific Test

```bash
# Run single test file
uv run python -m pytest tests/unit/test_invite_code_service.py -v

# Run single test method
uv run python -m pytest tests/unit/test_csv_parser_service.py::TestCSVParserFileValidation::test_valid_csv_accepted -v

# Run with output (useful for E2E tests with print statements)
uv run python -m pytest tests/e2e/test_onboarding_flow.py -v -s
```

---

## Test Coverage

### Unit Tests (72 tests)

#### 1. `test_invite_code_service.py` (9 tests)
Tests invite code validation logic:
- ✅ Valid code acceptance (exact match, case insensitive, whitespace handling)
- ✅ Invalid code rejection (wrong code, partial match, empty, None)
- ✅ Master code retrieval

#### 2. `test_uuid_strategy.py` (14 tests)
Tests deterministic and random UUID generation:
- ✅ Demo user (@sigmasight.com) always get deterministic UUIDs
- ✅ Random UUID generation for production users
- ✅ Email/name normalization
- ✅ Portfolio and position UUID generation
- ✅ Config-based UUID strategy

#### 3. `test_csv_parser_service.py` (28 tests)
Tests comprehensive CSV validation with 35+ error codes:

**File-Level Validation**:
- ✅ Valid CSV acceptance
- ✅ File size limits (10MB max)
- ✅ File type validation (.csv only)
- ✅ Empty file rejection
- ✅ Missing required columns
- ✅ Comment lines ignored (lines starting with #)

**Position-Level Validation**:
- ✅ Symbol validation (required, max 100 chars, valid characters)
- ✅ Quantity validation (required, non-zero, numeric, supports negative for shorts)
- ✅ Entry price validation (required, positive, max 2 decimals)
- ✅ Entry date validation (required, YYYY-MM-DD format, not future, not >100 years old)
- ✅ Duplicate detection (same symbol + entry date)
- ✅ Cash positions (SPAXX, etc.)
- ✅ Closed positions (exit date and price)

**Options Validation** (5 tests):
- ✅ Valid options position accepted (underlying, strike, expiration, type)
- ✅ Invalid strike price rejected (ERR_POS_020: non-numeric strike)
- ✅ Invalid expiration date rejected (ERR_POS_021: malformed date)
- ✅ Multiple invalid option fields reported together
- ✅ Negative strike price rejected

**Edge Cases**:
- ✅ Multiple valid positions
- ✅ Mixed valid/invalid rows
- ✅ Investment class auto-detection

#### 4. `test_position_import_service.py` (21 tests) ⭐ NEW
Tests position import logic - **would have caught abs(quantity) bug from code review**:

**Signed Quantity Preservation** (3 tests - CRITICAL):
- ✅ Long position quantity stays positive
- ✅ Short position quantity stays negative (validates fix for code review issue #1)
- ✅ Zero quantity edge case handling

**Options Field Mapping** (3 tests):
- ✅ Long call option fields correctly mapped (LC position type)
- ✅ Short put option fields correctly mapped (SP position type, negative quantity)
- ✅ Expiration date format validation (YYYY-MM-DD)

**UUID Generation** (3 tests):
- ✅ Deterministic UUIDs for same position data
- ✅ Different symbols generate different UUIDs
- ✅ Different entry dates generate different UUIDs

**Position Type Determination** (6 tests):
- ✅ PUBLIC + positive quantity → LONG
- ✅ PUBLIC + negative quantity → SHORT
- ✅ OPTIONS + positive + CALL → LC (Long Call)
- ✅ OPTIONS + positive + PUT → LP (Long Put)
- ✅ OPTIONS + negative + CALL → SC (Short Call)
- ✅ OPTIONS + negative + PUT → SP (Short Put)

**Investment Class Mapping** (4 tests):
- ✅ STOCK subtype implies PUBLIC class
- ✅ HEDGE_FUND is valid PRIVATE subtype
- ✅ MONEY_MARKET is valid PRIVATE subtype
- ✅ TREASURY_BILLS is valid PRIVATE subtype

**Closed Position Handling** (1 test):
- ✅ Positions with exit date and price handled correctly

**Mock Fixtures** (added to `conftest.py`):
- `mock_market_data_services` - Mocks YFinance/Polygon/FMP API calls
- `mock_preprocessing_service` - Mocks preprocessing pipeline
- `mock_batch_orchestrator` - Mocks batch calculations
- Pytest markers: `@pytest.mark.integration`, `@pytest.mark.slow`, `@pytest.mark.network`

### Integration Tests (16 tests)

#### 1. `test_onboarding_api.py`

**TestRegistrationEndpoint** (5 tests):
- POST /api/v1/onboarding/register
  - Valid registration succeeds (201)
  - Invalid invite code rejected (401 ERR_INVITE_001)
  - Duplicate email rejected (409 ERR_USER_001)
  - Weak password rejected (422 ERR_USER_003)
  - Invalid email rejected (422)

**TestCSVTemplateEndpoint** (2 tests):
- GET /api/v1/onboarding/csv-template
  - CSV template download succeeds
  - Cache headers present (max-age=3600)

**TestCreatePortfolioEndpoint** (4 tests):
- POST /api/v1/onboarding/create-portfolio
  - Valid portfolio creation succeeds (201)
  - Unauthenticated request rejected (401)
  - Duplicate portfolio rejected (409 ERR_PORT_001)
  - Invalid CSV rejected (400 ERR_PORT_008)

**TestCalculateEndpoint** (5 tests):
- POST /api/v1/portfolio/{id}/calculate
  - Valid calculate request succeeds (202) - **Uses `mock_preprocessing_service` and `mock_batch_orchestrator`**
  - Unauthenticated request rejected (401)
  - Wrong user calculate rejected (403)
  - Invalid portfolio ID rejected (404)
  - Force parameter works

#### 2. `test_position_import.py` (3 tests) ⭐ NEW

**CRITICAL**: Tests that actually call `import_positions()` with PostgreSQL database.

**TestPositionImportDatabasePersistence**:

1. **`test_import_positions_preserves_signed_quantity`** - **CRITICAL**
   - Creates PositionData with negative quantities (short positions)
   - Calls `import_positions()` to persist to PostgreSQL
   - Queries database to verify `Position.quantity` stayed negative
   - **Would have caught the abs(quantity) bug from code review issue #1**

2. **`test_import_positions_maps_option_fields`**
   - Verifies underlying_symbol, strike_price, expiration_date correctly mapped to PostgreSQL columns
   - Tests Numeric type handling (PostgreSQL-specific)
   - Verifies string → date conversion

3. **`test_import_positions_deterministic_uuids`**
   - Verifies deterministic UUID generation works correctly with PostgreSQL
   - Tests idempotency (same data → same UUID)

**Mock Fixtures** (from `conftest.py`):
- `mock_market_data_services` - Prevents network calls to YFinance/Polygon/FMP
- `mock_preprocessing_service` - Mocks preprocessing pipeline
- `mock_batch_orchestrator` - Prevents actual batch calculations

### End-to-End Tests (3 tests)

#### 1. `test_onboarding_flow.py`

**Complete User Journey** (test_complete_user_journey_success):
1. User registers with invite code → 201
2. User logs in → 200 + JWT token
3. User downloads CSV template → 200
4. User creates portfolio with 5 positions → 201
5. User triggers calculations → 202
6. Verifies all data persisted correctly

**Error Handling** (test_error_handling_throughout_flow):
- Tests error handling at each step of the flow
- Validates proper error codes and status codes
- Ensures system degrades gracefully

**Portfolio Constraints** (test_duplicate_portfolio_prevention):
- Validates one-portfolio-per-user constraint
- Ensures proper 409 error on duplicate creation

---

## Test Data Management

### Cleanup Strategy

**Unit Tests**:
- No database interaction
- No cleanup needed

**Integration & E2E Tests**:
- Use actual PostgreSQL database in Docker
- Automatic cleanup after each test
- Test users deleted via `client` fixture teardown

**Test User Emails** (automatically cleaned up):
```python
"newuser@example.com"
"testuser@example.com"
"otheruser@example.com"
"user@example.com"
"duplicate@example.com"
```

---

## Error Code Coverage

Tests validate 35+ structured error codes:

### CSV Errors (ERR_CSV_*)
- ERR_CSV_001: File too large
- ERR_CSV_002: Invalid file type
- ERR_CSV_003/005: Empty file
- ERR_CSV_004: Missing required column
- ERR_CSV_006: Malformed CSV

### Position Errors (ERR_POS_*)
- ERR_POS_001: Missing symbol
- ERR_POS_004: Missing quantity
- ERR_POS_005: Non-numeric quantity
- ERR_POS_006: Zero quantity
- ERR_POS_008: Missing entry price
- ERR_POS_012: Missing entry date
- ERR_POS_013: Invalid date format
- ERR_POS_020: Invalid strike price (malformed options) ⭐ NEW
- ERR_POS_021: Invalid expiration date (malformed options) ⭐ NEW
- ERR_POS_023: Duplicate position

### User Errors (ERR_USER_*)
- ERR_USER_001: Email already exists
- ERR_USER_002: Invalid email format
- ERR_USER_003: Weak password

### Portfolio Errors (ERR_PORT_*)
- ERR_PORT_001: User already has portfolio
- ERR_PORT_002: Portfolio name required
- ERR_PORT_004: Equity balance required
- ERR_PORT_008: CSV validation failed

### Invite Code Errors (ERR_INVITE_*)
- ERR_INVITE_001: Invalid invite code

---

## Test Patterns & Best Practices

### Unit Test Patterns

```python
# Fast, isolated, no database
@pytest.mark.asyncio
async def test_csv_validation():
    csv_file = create_upload_file(content)
    result = await CSVParserService.validate_csv(csv_file)
    assert result.is_valid is True
```

### Integration Test Patterns

```python
# Use real database, automatic cleanup
def test_registration(self, client):
    response = client.post("/api/v1/onboarding/register", json={...})
    assert response.status_code == 201
    # User automatically cleaned up after test
```

### E2E Test Patterns

```python
# Complete flow with detailed logging
def test_complete_journey(self, client):
    print("\n📝 Step 1: User Registration")
    # ... register
    print("\n🔐 Step 2: User Login")
    # ... login
    print("\n💼 Step 3: Create Portfolio")
    # ... create portfolio
    # etc.
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Test Onboarding

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: sigmasight_dev
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
    steps:
      - uses: actions/checkout@v3
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Run unit tests
        run: uv run python -m pytest tests/unit/ -v
      - name: Run integration tests
        run: uv run python -m pytest tests/integration/ -v
      - name: Run E2E tests
        run: uv run python -m pytest tests/e2e/ -v
```

---

## Troubleshooting

### Issue: "Module not found: aiosqlite"
**Solution**: Install dev dependencies
```bash
uv add --dev aiosqlite
```

### Issue: "Connection refused" on integration tests
**Solution**: Start PostgreSQL database
```bash
docker-compose up -d
docker ps  # Verify postgres is running
```

### Issue: "Database pool exhausted"
**Solution**: Cleanup is automatic, but you can manually clean test users:
```python
async with AsyncSessionLocal() as db:
    result = await db.execute(select(User).where(User.email.like("%example.com")))
    users = result.scalars().all()
    for user in users:
        await db.delete(user)
    await db.commit()
```

### Issue: Tests hanging or timing out
**Solution**: Reduce test scope or increase timeout
```bash
# Run single test class
uv run python -m pytest tests/integration/test_onboarding_api.py::TestRegistrationEndpoint -v

# Increase timeout
uv run python -m pytest tests/integration/ -v --timeout=300
```

---

## Future Enhancements

### Potential Additions

1. **Performance Tests**:
   - Batch upload of 1000+ positions
   - Concurrent user registrations
   - Large CSV file handling (9.9MB)

2. **Security Tests**:
   - SQL injection attempts
   - JWT token manipulation
   - CSV injection attacks

3. **Load Tests**:
   - 50 concurrent user registrations
   - Batch calculation under load
   - API rate limiting validation

4. **Negative Tests**:
   - Malformed JWT tokens
   - Expired tokens
   - Invalid content-types

---

## Test Metrics

### Current Coverage

- **Total Tests**: 91 (72 unit + 16 integration + 3 E2E)
- **Unit Test Pass Rate**: 100% (72/72) ✅
- **Integration Test Status**: Ready to run (requires database)
- **E2E Test Status**: Ready to run (requires database)

### Execution Time

- **Unit Tests**: ~0.16 seconds (all 72 tests)
- **Integration Tests**: ~5-10 seconds (estimated, with database)
- **E2E Tests**: ~10-15 seconds (estimated, complete flow)

### Test Additions (Phase 1 Critical Fixes)

**Date**: 2025-10-29

Added 25 new unit tests to address code review findings:

1. **Options Validation Tests** (4 new tests in `test_csv_parser_service.py`):
   - Tests for ERR_POS_020 (invalid strike price)
   - Tests for ERR_POS_021 (invalid expiration date)
   - Validates code review fix #4 (options validation error raising)

2. **Position Import Tests** (21 new tests in `test_position_import_service.py`):
   - **CRITICAL**: Tests for signed quantity preservation (would have caught abs(quantity) bug)
   - Tests for options field mapping
   - Tests for deterministic UUID generation
   - Tests for position type determination (LONG/SHORT/LC/LP/SC/SP)
   - Tests for investment class mapping (including new HEDGE_FUND, MONEY_MARKET, TREASURY_BILLS subtypes)

3. **Mock Fixtures** (added to `conftest.py`):
   - External API mocking to prevent network dependencies
   - Pytest markers for test categorization

---

## Contributing

When adding new onboarding features:

1. **Write unit tests first** - Fast feedback, no database needed
2. **Add integration tests** - Validate API contracts
3. **Update E2E tests** - Ensure end-to-end flow still works
4. **Update this document** - Keep test documentation current

---

## References

- **Implementation Spec**: `backend/TODO5.md`
- **API Endpoints**: `backend/README.md` (Onboarding section)
- **Error Codes**: `backend/app/core/onboarding_errors.py`
- **User Guide**: `backend/ONBOARDING_GUIDE.md`

---

**Last Updated**: 2025-10-29
**Test Suite Version**: 1.0
**Status**: ✅ Ready for use
