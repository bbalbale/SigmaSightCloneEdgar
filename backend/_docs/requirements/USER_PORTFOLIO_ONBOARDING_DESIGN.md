# User & Portfolio Onboarding - Backend Design Document

**Version**: 1.1
**Date**: 2025-11-05
**Status**: Updated - Multi-Portfolio Support Added
**Author**: AI Assistant (Claude)

---

## Changelog

### Version 1.1 (2025-11-05)
- **Phase Renumbering**: Inserted new Phase 2 for Multi-Portfolio Support
- **Phase 2 Added**: Multi-Portfolio Support (6 tasks)
- **Phase 3 Updated**: Admin & Superuser Tooling moved from Phase 2 to Phase 3
- **Scope Updated**: Removed "Multi-account support (future feature)" - now Phase 2
- **Design Decisions Updated**: Changed "Portfolio Limit" and "Account Types" decisions
- **API Endpoints Updated**: CSV import endpoint now requires account_name and account_type
- **Response Schemas Updated**: Added account metadata to responses

### Version 1.0 (2025-10-28)
- Initial version: Core onboarding design with Phase 1 and Phase 2 (Admin)

---

## Table of Contents

1. [Overview](#overview)
2. [Design Decisions Summary](#design-decisions-summary)
3. [API Endpoint Specifications](#api-endpoint-specifications)
4. [Error Conditions Catalog](#error-conditions-catalog)
5. [Service Layer Architecture](#service-layer-architecture)
6. [Database Schema Changes](#database-schema-changes)
7. [CSV Template Specification](#csv-template-specification)
8. [Frontend UX Flow](#frontend-ux-flow)
9. [Security Model](#security-model)
10. [Implementation Phases](#implementation-phases)
11. [Migration Plan](#migration-plan)

---

## 1. Overview

### Purpose
Enable self-service onboarding for test users to create accounts and portfolios via invite codes, supporting CSV import of positions from major brokerages (Schwab, Fidelity, Vanguard).

### Scope

**Phase 1: Core Onboarding (MVP)** ✅ COMPLETED
- API endpoints for user registration and portfolio creation
- CSV parsing for broker-exported position data
- Invite code security system (config-based single code)
- Full batch processing integration
- Synchronous portfolio creation flow

**Phase 2: Multi-Portfolio Support** 🔄 IN PROGRESS
- Update CSV import to support account_name and account_type
- Remove single-portfolio restriction
- Support importing multiple portfolios per user
- Integration with multi-portfolio CRUD APIs
- Documentation and testing

**Phase 3: Admin & Superuser Tooling** (Future Implementation)
- Superuser authentication and authorization
- User impersonation for testing
- Admin dashboard endpoints

**Out of Scope:**
- Frontend implementation details (FE team responsibility)
- Tax lot tracking (future feature)
- Automated cleanup (manual only)

### Target Users
- **10-50 test users** (internal testing + external beta)
- Real users with real portfolio data
- Same database as production (Railway Sandbox → Production)

---

## 2. Design Decisions Summary

**Target**: 50 beta users with white-glove support

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **User Creation** | Self-service with single invite code | Controlled access, simple for 50 users |
| **Portfolio Limit** | Multiple portfolios per user | Support family office, multiple accounts (Phase 2) |
| **Portfolio Init** | CSV required for import flow | Ensure data quality, bulk position import |
| **Position Model** | Single aggregated position per symbol | Simpler than tax lots, matches broker CSVs |
| **Entry Date** | Required in standardized CSV | Necessary for calculations |
| **UUID Strategy** | Hybrid: deterministic for testing → random | Test thoroughly, maintain demos |
| **Invite Codes** | Single master code (config-based) | No database, looks unique to users |
| **Batch Processing** | Synchronous (30-60s timeout) | Simpler for MVP |
| **Superuser Access** | *Phase 3 only* | Not needed for core onboarding or multi-portfolio |
| **Equity Balance** | Separate API field | Handle leverage correctly |
| **CSV Validation** | All-or-nothing (strict) | Data quality |
| **Demo Seeding** | Keep separate, share utilities | Don't break existing system |
| **Rate Limiting** | None | Trust 50 beta users |
| **Audit Logging** | Application logs only | Sufficient for small scale |
| **Account Types** | Required (9 types) | Enables multi-portfolio aggregation (Phase 2) |
| **Error Codes** | ~35 essential codes | Balanced detail |

---

## 3. API Endpoint Specifications

### **Phase 1: Core Onboarding - 4 Endpoints** ✅ COMPLETED

These are the MVP endpoints for user onboarding and portfolio creation:

1. `POST /api/v1/onboarding/register` - User registration with single invite code
2. `POST /api/v1/onboarding/import-portfolio` - Portfolio creation with CSV (no automatic batch trigger)
3. `GET /api/v1/onboarding/csv-template` - Download CSV template
4. `POST /api/v1/portfolio/{portfolio_id}/calculate` - User-triggered portfolio calculations

### **Phase 2: Multi-Portfolio Support - Updates to Existing Endpoints** 🔄 IN PROGRESS

Updates to Phase 1 endpoints to support multiple portfolios per user:

- Update `POST /api/v1/onboarding/import-portfolio` to require `account_name` and `account_type`
- Remove validation preventing multiple portfolios per user
- Update response schema to include account metadata
- Update CSV template documentation to include account type guidance
- Document integration with multi-portfolio CRUD APIs (`/api/v1/portfolios`)

**Note:** Multi-portfolio CRUD APIs already exist (implemented Nov 1, 2025). See `backend/_docs/MULTI_PORTFOLIO_API_REFERENCE.md` for complete documentation.

### **Phase 3: Admin & Superuser - 3 Endpoints** *(Future Implementation)*

These admin tooling endpoints will be implemented after Phase 2:

1. `POST /api/v1/admin/impersonate` - Start impersonation
2. `POST /api/v1/admin/stop-impersonation` - End impersonation
3. `GET /api/v1/admin/users` - List all users

**Note:** Phase 3 also includes all work from `ADMIN_AUTH_SUPPLEMENT.md` (superuser authentication, JWT modifications, bootstrap script, etc.)

---

### 3.1 User Registration

#### `POST /api/v1/onboarding/register`

**Description:** Create new user account with invite code validation (single master code).

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe",
  "invite_code": "PRESCOTT-LINNAEAN-COWPERTHWAITE"
}
```

**Response (201 Created):**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "full_name": "John Doe",
  "created_at": "2025-10-28T10:30:00Z",
  "message": "Account created successfully. Please login to create your portfolio."
}
```

**Error Responses:**
- `401` - Invalid invite code
- `409` - Email already exists
- `422` - Validation errors (password too weak, invalid email, etc.)

**Note:** All users receive the same invite code (`PRESCOTT-LINNAEAN-COWPERTHWAITE`), validated against config value.

---

### 3.2 Portfolio Creation with CSV Import

#### `POST /api/v1/onboarding/import-portfolio`

**Description:** Create portfolio and import positions from CSV. Supports multiple portfolios per user (Phase 2). Does NOT automatically trigger batch processing (use separate calculate endpoint).

**Request:**
```
Content-Type: multipart/form-data

Fields:
- portfolio_name: string (required)
- account_name: string (required) ← Phase 2: NEW
- account_type: string (required) ← Phase 2: NEW (taxable, ira, roth_ira, 401k, 403b, 529, hsa, trust, other)
- description: string (optional)
- equity_balance: decimal (required, e.g., 500000.00)
- csv_file: file (required, .csv format)
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/onboarding/import-portfolio \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -F "portfolio_name=My Trading Portfolio" \
  -F "account_name=Schwab Taxable" \
  -F "account_type=taxable" \
  -F "description=Main trading account at Schwab" \
  -F "equity_balance=500000.00" \
  -F "csv_file=@positions.csv"
```

**Success Response (201 Created):**
```json
{
  "portfolio_id": "a3209353-9ed5-4885-81e8-d4bbc995f96c",
  "name": "My Trading Portfolio",
  "account_name": "Schwab Taxable",
  "account_type": "taxable",
  "description": "Main trading account at Schwab",
  "equity_balance": "500000.00",
  "positions_imported": 45,
  "created_at": "2025-10-28T10:35:00Z",
  "message": "Portfolio created successfully. Use /api/v1/portfolio/{portfolio_id}/calculate to run calculations."
}
```

**Error Responses:**

**400 Bad Request - CSV Validation Failed:**
```json
{
  "error": {
    "code": "ERR_CSV_007",
    "message": "No valid positions found in CSV. Please fix errors and try again.",
    "details": [
      {
        "row": 8,
        "field": "entry_date",
        "error": "Invalid date format. Expected YYYY-MM-DD, got '01/15/2024'"
      }
    ]
  }
}
```

**409 Conflict - Duplicate Portfolio Name:**
```json
{
  "error": {
    "code": "ERR_PORT_001",
    "message": "You already have a portfolio with this account name. Please use a different name."
  }
}
```

**Note:** Phase 2 removed the "one portfolio per user" restriction. Users can now import multiple portfolios.

**413 Payload Too Large - File Too Large:**
```json
{
  "error": {
    "code": "ERR_CSV_001",
    "message": "CSV file is too large. Maximum size is 10MB."
  }
}
```

**415 Unsupported Media Type - Invalid File Type:**
```json
{
  "error": {
    "code": "ERR_CSV_002",
    "message": "Please upload a .csv file."
  }
}
```

**422 Unprocessable Entity - Missing Required Fields:**
```json
{
  "error": {
    "code": "ERR_PORT_002",
    "message": "Portfolio name is required."
  }
}
```

---

### 3.2.1 Download CSV Template

#### `GET /api/v1/onboarding/csv-template`

**File Location:** `app/api/v1/onboarding.py`

**Description:** Download CSV template for portfolio import. Returns a 12-column CSV file with instructions and example rows. Essential for Phase 1 testing and user onboarding.

**Request:**
```bash
curl -X GET http://localhost:8000/api/v1/onboarding/csv-template
```

**Response (200 OK):**
```
Content-Type: text/csv
Content-Disposition: attachment; filename=sigmasight_portfolio_template.csv
Cache-Control: public, max-age=3600

Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share
# SigmaSight Portfolio Import Template
# Instructions: Fill in your positions below the header row
# Required columns: Symbol, Quantity, Entry Price Per Share, Entry Date
# For help: https://docs.sigmasight.io/csv-import
AAPL,100,158.00,2024-01-15,PUBLIC,,,,,,,
SPY250919C00460000,200,7.00,2024-01-10,OPTIONS,,SPY,460.00,2025-09-19,CALL,,
SPAXX,8271.36,1.00,2024-01-01,PUBLIC,,,,,,,
CASH_USD,1,25000.00,2024-01-01,PRIVATE,CASH,,,,,
```

**Implementation Notes:**
- No authentication required (public template)
- Template embedded in endpoint code (no static file serving)
- Includes instruction comments and example rows
- Proper cache headers (1 hour) for performance

---

### 3.3 User-Triggered Portfolio Calculations

#### `POST /api/v1/portfolio/{portfolio_id}/calculate`

**File Location:** `app/api/v1/analytics/portfolio.py`

**Description:** Trigger batch calculations for user's portfolio. **Includes preprocessing step** (security master enrichment + price cache bootstrap) followed by normal batch orchestrator. Users can only trigger calculations for portfolios they own.

**Processing Steps:**
1. **Preprocessing (10-30s):** Enriches security master data (sector/industry) and bootstraps historical price cache for all portfolio symbols
2. **Batch Calculations (30-60s):** Runs normal batch orchestrator (Greeks, factors, correlations, stress tests, etc.)
3. **Total Time:** 40-90 seconds

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/portfolio/a3209353-9ed5-4885-81e8-d4bbc995f96c/calculate \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

**Response (202 Accepted):**
```json
{
  "status": "started",
  "batch_run_id": "f7b3c8a1-9d2e-4f56-8a7c-1b2d3e4f5a6b",
  "portfolio_id": "a3209353-9ed5-4885-81e8-d4bbc995f96c",
  "preprocessing": {
    "security_master_populated": 42,
    "price_cache_populated": 38,
    "coverage_percent": 90.5
  },
  "message": "Portfolio calculations started (including preprocessing). This will take 40-90 seconds.",
  "poll_url": "/api/v1/portfolio/a3209353-9ed5-4885-81e8-d4bbc995f96c/calculation-status"
}
```

**Error Responses:**
- `403` - Portfolio not owned by user
- `404` - Portfolio not found
- `409` - Calculations already running for this portfolio

**Architecture Notes:**
- This endpoint provides user-facing access to batch processing
- Uses `batch_orchestrator.run_daily_batch_sequence()` with current date and specific portfolio ID
- Validates portfolio ownership before triggering calculations
- Returns immediately with batch_run_id for status tracking
- Separate from `POST /admin/batch/run` which is admin-only and can process all portfolios

**Implementation Example:**
```python
from datetime import date
from app.batch.batch_orchestrator import batch_orchestrator

result = await batch_orchestrator.run_daily_batch_sequence(
    calculation_date=date.today(),
    portfolio_ids=[str(portfolio_id)],
    db=db
)
```

**Comparison with Admin Endpoint:**

| Feature | User Endpoint | Admin Endpoint |
|---------|---------------|----------------|
| **Path** | `/api/v1/portfolio/{id}/calculate` | `/admin/batch/run` |
| **Auth** | Portfolio ownership | Superuser required |
| **Scope** | Single portfolio (owned by user) | Any portfolio or all portfolios |
| **Force Override** | Not allowed | Can force with `force=true` |
| **Use Case** | User-initiated refresh | System operations, troubleshooting |

---

### 3.4 Admin: Impersonate User **[PHASE 2]**

#### `POST /api/v1/admin/impersonate`

**Description:** Generate impersonation token to act as another user (superuser only).

**Request:**
```json
{
  "target_user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response (200 OK):**
```json
{
  "impersonation_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_at": "2025-10-28T18:40:00Z",
  "impersonating": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "full_name": "John Doe"
  },
  "original_user": {
    "user_id": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
    "email": "elliott@sigmasight.io"
  },
  "message": "Now acting as user@example.com. Use this token for all API calls."
}
```

**Usage:**
```bash
# Use impersonation token for all subsequent requests
curl -X GET http://localhost:8000/api/v1/data/portfolio/complete \
  -H "Authorization: Bearer <IMPERSONATION_TOKEN>"
```

**Error Responses:**
- `403` - User is not a superuser
- `404` - Target user not found

---

### 3.5 Admin: Stop Impersonation **[PHASE 2]**

#### `POST /api/v1/admin/stop-impersonation`

**Description:** End impersonation session and return to original user context.

**Request:**
```
Authorization: Bearer <IMPERSONATION_TOKEN>
```

**Response (200 OK):**
```json
{
  "message": "Impersonation ended",
  "original_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "original_user": {
    "user_id": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
    "email": "elliott@sigmasight.io"
  }
}
```

---

### 3.6 Admin: List All Users **[PHASE 2]**

#### `GET /api/v1/admin/users`

**Description:** List all users (superuser only). Demo users can be identified by `@sigmasight.com` email pattern.

**Query Parameters:**
- `limit` (optional): default 50, max 200
- `offset` (optional): default 0

**Response (200 OK):**
```json
{
  "users": [
    {
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "full_name": "John Doe",
      "has_portfolio": true,
      "created_at": "2025-10-28T10:30:00Z"
    },
    {
      "user_id": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
      "email": "demo_individual@sigmasight.com",
      "full_name": "Demo Individual Investor",
      "has_portfolio": true,
      "created_at": "2025-10-01T08:00:00Z"
    }
  ],
  "total": 2,
  "limit": 50,
  "offset": 0
}
```

**Note:** Demo users are identified by `@sigmasight.com` email domain. No `account_type` field needed.

---

## 4. Error Conditions Catalog

### 4.1 Registration Errors

**Invite Code Errors (Simplified for Single Master Code):**

| Code | Error | Condition | User Message |
|------|-------|-----------|--------------|
| `ERR_INVITE_001` | Invalid invite code | Code doesn't match master code (`PRESCOTT-LINNAEAN-COWPERTHWAITE`) | "Invalid invite code. Please check and try again." |

**User Validation Errors:**

| Code | Error | Condition | User Message |
|------|-------|-----------|--------------|
| `ERR_USER_001` | Email already exists | Duplicate email in database | "An account with this email already exists. Please login instead." |
| `ERR_USER_002` | Invalid email format | Email fails regex validation | "Please provide a valid email address." |
| `ERR_USER_003` | Password too weak | Password < 8 chars or missing requirements | "Password must be at least 8 characters with uppercase, lowercase, and number." |
| `ERR_USER_004` | Full name required | `full_name` is empty | "Please provide your full name." |

**Note:** With the single master invite code system (Phase 1), we simplified from 5 invite code errors down to just 1. No database lookups, expiration checks, or usage tracking needed.

### 4.2 CSV Validation Errors

| Code | Error | Condition | User Message |
|------|-------|-----------|--------------|
| `ERR_CSV_001` | File too large | File size > 10MB | "CSV file is too large. Maximum size is 10MB." |
| `ERR_CSV_002` | Invalid file type | Extension not `.csv` | "Please upload a .csv file." |
| `ERR_CSV_003` | Empty file | File has 0 rows | "CSV file is empty. Please upload a file with position data." |
| `ERR_CSV_004` | Missing header row | First row doesn't contain required columns | "CSV must have header row with: Symbol, Quantity, Entry Price Per Share, Entry Date" |
| `ERR_CSV_005` | Missing required column | Required column not found | "Missing required column: {column_name}" |
| `ERR_CSV_006` | Invalid CSV format | Malformed CSV (unclosed quotes, etc.) | "Invalid CSV format. Please check file and try again." |
| `ERR_CSV_007` | No valid positions | All rows failed validation | "No valid positions found in CSV. Please fix errors and try again." |

### 4.3 Position Validation Errors (Row-Level)

| Code | Field | Condition | User Message |
|------|-------|-----------|--------------|
| `ERR_POS_001` | `symbol` | Empty or missing | "Row {row}: Symbol is required" |
| `ERR_POS_002` | `symbol` | Invalid characters | "Row {row}: Symbol contains invalid characters" |
| `ERR_POS_003` | `symbol` | Too long (>100 chars) | "Row {row}: Symbol too long (max 100 characters)" |
| `ERR_POS_004` | `quantity` | Not a number | "Row {row}: Quantity must be a number, got '{value}'" |
| `ERR_POS_005` | `quantity` | Zero | "Row {row}: Quantity cannot be zero" |
| `ERR_POS_006` | `quantity` | Too many decimal places | "Row {row}: Quantity has too many decimal places (max 6)" |
| `ERR_POS_007` | `entry_price` | Not a number | "Row {row}: Entry price must be a number, got '{value}'" |
| `ERR_POS_008` | `entry_price` | Negative or zero | "Row {row}: Entry price must be positive" |
| `ERR_POS_010` | `entry_date` | Missing | "Row {row}: Entry date is required" |
| `ERR_POS_011` | `entry_date` | Invalid format | "Row {row}: Invalid date format. Expected YYYY-MM-DD, got '{value}'" |
| `ERR_POS_012` | `entry_date` | Future date | "Row {row}: Entry date cannot be in the future" |
| `ERR_POS_013` | `entry_date` | Too old (>100 years) | "Row {row}: Entry date seems unrealistic ({date})" |
| `ERR_POS_014` | `investment_class` | Invalid value | "Row {row}: Investment class must be PUBLIC, OPTIONS, or PRIVATE" |
| `ERR_POS_015` | `investment_subtype` | Invalid for class | "Row {row}: Investment subtype '{value}' not valid for {investment_class}. Allowed subtypes: {allowed_subtypes}" |
| `ERR_POS_016` | `exit_date` | Before entry_date | "Row {row}: Exit date cannot be before entry date" |
| `ERR_POS_017` | `exit_price` | Provided without exit_date | "Row {row}: Exit price requires exit date" |
| `ERR_POS_018` | Options fields | Missing required fields | "Row {row}: Options positions require: Underlying Symbol, Strike Price, Expiration Date, Option Type" |
| `ERR_POS_019` | `strike_price` | Not a number | "Row {row}: Strike price must be a number" |
| `ERR_POS_020` | `expiration_date` | Invalid format | "Row {row}: Expiration date must be YYYY-MM-DD format" |
| `ERR_POS_021` | `option_type` | Invalid value | "Row {row}: Option type must be CALL or PUT" |
| `ERR_POS_022` | Duplicate position | Same symbol+entry_date | "Row {row}: Duplicate position for {symbol} on {entry_date}" |

### 4.4 Portfolio Creation Errors

| Code | Error | Condition | User Message |
|------|-------|-----------|--------------|
| `ERR_PORT_001` | User already has portfolio | `portfolios.user_id` exists | "You already have a portfolio. Each user is limited to one portfolio." |
| `ERR_PORT_002` | Missing portfolio name | `portfolio_name` empty | "Portfolio name is required." |
| `ERR_PORT_003` | Portfolio name too long | Length > 255 chars | "Portfolio name too long (max 255 characters)." |
| `ERR_PORT_004` | Missing equity balance | `equity_balance` not provided | "Starting equity balance is required." |
| `ERR_PORT_005` | Invalid equity balance | Not a number or negative | "Equity balance must be a positive number." |
| `ERR_PORT_006` | Equity balance too large | > $1 billion | "Equity balance seems unrealistic. Please verify." |
| `ERR_PORT_007` | Missing CSV file | No file uploaded | "Please upload a CSV file with your positions." |
| `ERR_PORT_008` | CSV validation failed | Any CSV errors from 4.2/4.3 | "CSV validation failed. Please fix errors and try again." |

### 4.5 Batch Processing Errors

**Note:** These errors follow the graceful degradation pattern used throughout the batch processing system. Portfolio and positions are always created successfully; these errors indicate partial calculation results.

| Code | Error | Condition | User Message |
|------|-------|-----------|--------------|
| `ERR_BATCH_001` | Market data fetch failed | External API errors | "Unable to fetch market data. Portfolio created but calculations incomplete." |
| `ERR_BATCH_002` | Factor analysis failed | Calculation errors | "Factor analysis incomplete. You can view positions but risk metrics unavailable." |
| `ERR_BATCH_003` | Timeout | Batch took >60s | "Portfolio created but calculations are still running. Please refresh in a few minutes." |
| `ERR_BATCH_004` | Database error during batch | DB write failures | "Portfolio created but unable to save calculation results. Please contact support." |

**Design Pattern:** The batch orchestrator (`app/batch/batch_orchestrator.py`) uses exception handling with graceful degradation. These error codes provide user-friendly messages for the onboarding flow while maintaining consistency with the existing batch system's error handling approach.

### 4.6 Admin/Superuser Errors **[PHASE 2]**

**Note:** These errors are for Phase 2 admin endpoints only. Not needed for Phase 1 core onboarding.

| Code | Error | Condition | User Message |
|------|-------|-----------|--------------|
| `ERR_ADMIN_001` | Not a superuser | `is_superuser = FALSE` | "Unauthorized. This endpoint requires superuser access." |
| `ERR_ADMIN_002` | Target user not found | Invalid `user_id` | "User not found." |
| `ERR_ADMIN_003` | Cannot impersonate self | `target_user_id = current_user_id` | "Cannot impersonate yourself." |
| `ERR_ADMIN_004` | Invalid impersonation token | Malformed or expired token | "Invalid impersonation token. Please re-authenticate." |
| `ERR_ADMIN_005` | Invite code generation failed | Database constraints | "Unable to generate invite code. Please try again." |

### 4.7 Error Response Format

All errors follow consistent structure:

```json
{
  "error": {
    "code": "ERR_CSV_007",
    "message": "No valid positions found in CSV. Please fix errors and try again.",
    "details": [
      {
        "row": 8,
        "field": "entry_date",
        "error": "Invalid date format. Expected YYYY-MM-DD, got '01/15/2024'"
      },
      {
        "row": 15,
        "field": "quantity",
        "error": "Quantity must be a number, got 'N/A'"
      }
    ],
    "documentation_url": "https://docs.sigmasight.io/errors/ERR_CSV_007"
  }
}
```

---

## 5. Service Layer Architecture

### 5.1 Service Classes

**Phase 1 Services:**
```
app/services/
├── onboarding_service.py        # Main orchestration
├── invite_code_service.py       # Invite code validation (config-based)
├── csv_parser_service.py        # CSV validation & parsing
├── position_import_service.py   # Position creation from CSV
├── preprocessing_service.py     # Security master + price cache (used by calculate endpoint)
├── security_master_service.py   # Security master enrichment (refactored from seed script)
├── price_cache_service.py       # Price cache bootstrap (refactored from seed script)
└── batch_trigger_service.py     # Batch processing orchestration
```

**Note**: Preprocessing services are used by the `/calculate` endpoint, NOT during portfolio creation. This keeps portfolio creation fast (<5s) and defers data enrichment to the user-triggered calculation step.

**Phase 2 Services:**
```
app/services/
└── impersonation_service.py     # User impersonation (Phase 2 only)
```

### 5.2 OnboardingService

**Responsibilities:**
- User registration with invite code validation
- Portfolio creation orchestration
- Batch processing trigger

**Key Methods:**

```python
class OnboardingService:
    async def register_user(
        self,
        email: str,
        password: str,
        full_name: str,
        invite_code: str
    ) -> User:
        """
        Register new user with invite code validation.

        Steps:
        1. Validate invite code matches config value (settings.BETA_INVITE_CODE)
        2. Create user with hashed password
        3. Return user object

        Note: Phase 1 uses single master code from config - no database tracking needed.

        Raises:
            InviteCodeError: Invalid invite code
            UserExistsError: Email already registered
            ValidationError: Invalid input data
        """

    async def create_portfolio_with_csv(
        self,
        user_id: UUID,
        portfolio_name: str,
        equity_balance: Decimal,
        csv_file: UploadFile,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create portfolio and import positions from CSV.

        Steps:
        1. Validate user has no existing portfolio
        2. Parse and validate CSV
        3. Create portfolio record
        4. Import positions
        5. Return results

        Note: Does NOT trigger batch processing. User must call
        POST /api/v1/portfolio/{portfolio_id}/calculate separately.

        Raises:
            PortfolioExistsError: User already has portfolio
            CSVValidationError: Invalid CSV data
        """
```

### 5.3 InviteCodeService **[SIMPLIFIED FOR PHASE 1]**

```python
class InviteCodeService:
    """
    Simplified invite code validation for Phase 1.

    Uses single master code from config.
    No database operations required.
    """

    def __init__(self):
        self.master_code = settings.BETA_INVITE_CODE

    def validate_invite_code(self, code: str) -> bool:
        """
        Validate invite code matches master code.

        Args:
            code: The invite code to validate

        Returns:
            True if valid, False otherwise

        Example:
            service = InviteCodeService()
            is_valid = service.validate_invite_code(settings.BETA_INVITE_CODE)
            # returns True
        """
        return code.strip().upper() == self.master_code.upper()
```

**Note:** All 50 beta users receive the same invite code. Frontend displays the same code to all users - no "personalization" needed for MVP.

### 5.4 CSVParserService

```python
class CSVParserService:
    def validate_csv(
        self,
        csv_file: UploadFile
    ) -> CSVValidationResult:
        """
        Validate CSV structure and content.

        Checks:
        - File size (max 10MB)
        - File type (.csv)
        - Has header row with required columns
        - All rows have valid data

        Returns:
            CSVValidationResult with errors/warnings

        Does NOT create database records.
        """

    def parse_csv_to_positions(
        self,
        csv_file: UploadFile
    ) -> List[PositionData]:
        """
        Parse validated CSV to position data structures.

        Returns:
            List of PositionData dicts ready for database insert
        """
```

**PositionData Structure:**
```python
@dataclass
class PositionData:
    symbol: str
    quantity: Decimal
    entry_price: Decimal
    entry_date: date
    investment_class: Optional[str] = None  # AUTO if not provided
    investment_subtype: Optional[str] = None
    # Options fields
    underlying_symbol: Optional[str] = None
    strike_price: Optional[Decimal] = None
    expiration_date: Optional[date] = None
    option_type: Optional[str] = None  # CALL or PUT
    # Closed position fields
    exit_date: Optional[date] = None
    exit_price: Optional[Decimal] = None
```

### 5.5 PositionImportService

```python
class PositionImportService:
    async def import_positions(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        user_id: UUID,
        positions: List[PositionData]
    ) -> ImportResult:
        """
        Create position records from parsed CSV data.

        For each position:
        1. Determine position_type (LONG/SHORT for stocks, LC/LP/SC/SP for options)
        2. Auto-classify investment_class if not provided
        3. Create Position record
        4. Apply sector auto-tagging

        Uses deterministic UUIDs (Phase 1) or random UUIDs (Phase 3).

        Returns:
            ImportResult with success/failure counts
        """
```

### 5.6 ImpersonationService **[PHASE 2 ONLY]**

**Note:** This service is part of Phase 2 admin tooling and should be implemented AFTER Phase 1 is working and tested.

```python
class ImpersonationService:
    """
    User impersonation service for superuser testing (Phase 2).

    Allows superusers to generate tokens to act as another user for testing
    and support purposes. See ADMIN_AUTH_SUPPLEMENT.md for complete Phase 2
    implementation details.
    """

    async def create_impersonation_token(
        self,
        superuser_id: UUID,
        target_user_id: UUID
    ) -> ImpersonationToken:
        """
        Create JWT token for impersonating another user.

        Token payload includes:
        - sub: target_user_id (who we're acting as)
        - impersonator_id: superuser_id (who initiated)
        - is_impersonation: true
        - exp: 8 hours from now

        Raises:
            PermissionError: superuser_id is not a superuser
            UserNotFoundError: target_user_id doesn't exist
        """

    async def end_impersonation(
        self,
        impersonation_token: str
    ) -> Dict[str, Any]:
        """
        End impersonation session.

        Returns original user token.
        """
```

**Implementation Priority:** Phase 2 only - not required for core user onboarding.

---

## 6. Database Schema Changes

### 6.1 Phase 1: No Database Changes Required ✅

**Phase 1 uses config-based invite code - no database changes needed!**

The single master invite code (`PRESCOTT-LINNAEAN-COWPERTHWAITE`) is stored in `app/config.py`:

```python
# app/config.py
BETA_INVITE_CODE = "PRESCOTT-LINNAEAN-COWPERTHWAITE"
```

All Phase 1 functionality works with existing User and Portfolio models.

### 6.2 Phase 2: Superuser Column **[PHASE 2 ONLY]**

**Minimal database changes for Phase 2:**

```sql
-- Add superuser flag (Phase 2 only)
ALTER TABLE users ADD COLUMN is_superuser BOOLEAN DEFAULT FALSE NOT NULL;
CREATE INDEX idx_users_is_superuser ON users(is_superuser);
```

**Note:** No `account_type` column needed - demo users identified by `@sigmasight.com` email pattern.

### 6.3 Phase 2: Alembic Migration **[PHASE 2 ONLY]**

**File:** `alembic/versions/xxxx_add_superuser_column.py`

```python
"""Add superuser column

Revision ID: xxxx
Revises: previous_revision
Create Date: 2025-10-28

Phase 2 only - adds is_superuser column for admin authentication.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'xxxx'
down_revision = 'previous_revision'
branch_labels = None
depends_on = None


def upgrade():
    # Add is_superuser column
    op.add_column('users', sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'))

    # Create index
    op.create_index('idx_users_is_superuser', 'users', ['is_superuser'])


def downgrade():
    # Drop index
    op.drop_index('idx_users_is_superuser')

    # Remove column
    op.drop_column('users', 'is_superuser')
```

**Run this migration only in Phase 2, not Phase 1!**

---

## 7. CSV Template Specification

### 7.1 Template File

**Filename:** `sigmasight_portfolio_template.csv`

**Location:** Provided as static file (deferred: API endpoint for Phase 2)

### 7.2 Column Definitions

| Column | Required | Type | Format | Description | Example |
|--------|----------|------|--------|-------------|---------|
| **Symbol** | ✅ Yes | String | Max 50 chars | Stock ticker or option symbol | `AAPL` |
| **Quantity** | ✅ Yes | Decimal | Max 6 decimals | Number of shares (negative for short) | `100` |
| **Entry Price Per Share** | ✅ Yes | Decimal | Max 2 decimals | Average cost basis per share | `158.00` |
| **Entry Date** | ✅ Yes | Date | YYYY-MM-DD | Date position was opened | `2024-01-15` |
| **Investment Class** | No | Enum | PUBLIC/OPTIONS/PRIVATE | Auto-detected if blank | `PUBLIC` |
| **Investment Subtype** | No | String | See 7.3 | For PRIVATE assets only | `PRIVATE_EQUITY` |
| **Underlying Symbol** | Options only | String | Max 10 chars | For options: underlying ticker | `SPY` |
| **Strike Price** | Options only | Decimal | Max 2 decimals | Option strike price | `460.00` |
| **Expiration Date** | Options only | Date | YYYY-MM-DD | Option expiration date | `2025-09-19` |
| **Option Type** | Options only | Enum | CALL/PUT | Type of option | `CALL` |
| **Exit Date** | No | Date | YYYY-MM-DD | Date position was closed | `2024-10-01` |
| **Exit Price Per Share** | No | Decimal | Max 2 decimals | Price at exit | `400.00` |

### 7.3 Investment Subtype Values

**For PRIVATE assets only:**

- `PRIVATE_EQUITY` - Private equity funds
- `VENTURE_CAPITAL` - VC funds
- `HEDGE_FUND` - Hedge funds
- `PRIVATE_REIT` - Private REITs
- `REAL_ESTATE` - Direct real estate
- `CRYPTOCURRENCY` - Crypto holdings
- `ART` - Art & collectibles
- `MONEY_MARKET` - Money market funds
- `TREASURY_BILLS` - Treasury bills
- `CASH` - Cash holdings
- `OTHER` - Other alternatives

### 7.4 Template Content

```csv
Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share
AAPL,100,158.00,2024-01-15,PUBLIC,,,,,,,
MSFT,50,350.00,2024-02-01,PUBLIC,,,,,,,
VOO,20,631.00,2024-03-15,PUBLIC,,,,,,,
SPY250919C00460000,200,7.00,2024-01-10,OPTIONS,,SPY,460.00,2025-09-19,CALL,,
QQQ250815C00420000,150,7.00,2024-01-10,OPTIONS,,QQQ,420.00,2025-08-15,CALL,,
BX_PRIVATE_EQUITY,1,50000.00,2023-06-01,PRIVATE,PRIVATE_EQUITY,,,,,
HOME_EQUITY,1,500000.00,2020-01-01,PRIVATE,REAL_ESTATE,,,,,
CRYPTO_BTC_ETH,1,75000.00,2022-06-01,PRIVATE,CRYPTOCURRENCY,,,,,
CASH_USD,1,25000.00,2024-01-01,PRIVATE,CASH,,,,,
US_TREASURY_BILLS,1,50000.00,2024-01-01,PRIVATE,TREASURY_BILLS,,,,,
NFLX,-100,490.00,2024-01-25,PUBLIC,,,,,,2024-10-15,450.00
```

### 7.5 Parsing Rules

1. **Header Row**: First row must contain column names (case-insensitive matching)
2. **Empty Rows**: Skipped silently
3. **Whitespace**: Trimmed from all values
4. **Quotes**: CSV standard (quotes around values with commas)
5. **Auto-Classification**: If `Investment Class` blank, use `determine_investment_class(symbol)`
6. **Options Detection**: If symbol matches OCC format OR has underlying/strike/expiration, classify as OPTIONS
7. **Negative Quantity**: Interpreted as SHORT position

### 7.6 User Instructions (Include in Template)

**To include in downloadable CSV:**

```csv
# SigmaSight Portfolio Import Template
#
# INSTRUCTIONS:
# 1. Fill in your positions below the header row
# 2. Required columns: Symbol, Quantity, Entry Price Per Share, Entry Date
# 3. For entry_date, use your earliest purchase date for that symbol
# 4. For entry_price, use your broker's Average Cost Basis
# 5. Optional columns can be left blank
# 6. Delete these instruction rows before uploading
#
# For help, see: https://docs.sigmasight.io/csv-import
#
Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share
```

### 7.7 Special Position Types

#### Cash Positions

**Cash, money market funds, and treasury bills** use specific investment classes and subtypes based on whether they have a tradeable ticker symbol:

**Approach 1: Money Market Funds with Ticker Symbols (PUBLIC)**
```csv
SPAXX,8271.36,1.00,2024-01-01,PUBLIC,,,,,,,
VMFXX,10000.00,1.00,2024-01-01,PUBLIC,,,,,,,
VUSXX,5000.00,1.00,2024-01-01,PUBLIC,,,,,,,
```
- Symbol: Actual fund ticker (SPAXX, VMFXX, VUSXX, etc.)
- Quantity: Actual share count
- Entry Price: $1.00 per share (standard NAV for money market funds)
- Investment Class: `PUBLIC` (they have real ticker symbols and can be looked up in market data APIs)
- Investment Subtype: Leave blank (treated as standard PUBLIC positions)

**Why PUBLIC?**
- Money market funds with tickers are actual securities with real-time pricing
- Can query current NAV via market data APIs
- Treated like any other PUBLIC position in the system
- Standard $1.00 NAV means minimal price volatility

**Approach 2: Non-Tickered Money Market Positions (PRIVATE)**
```csv
CASH_MM_FUND,1,25000.00,2024-01-01,PRIVATE,MONEY_MARKET,,,,,
```
- Symbol: Descriptive identifier (no real ticker)
- Quantity: 1
- Entry Price: Total investment amount
- Investment Class: `PRIVATE`
- Investment Subtype: `MONEY_MARKET`

**Use when:**
- Money market fund doesn't have a standard ticker symbol
- Corporate/institutional money market accounts
- Sweep accounts without ticker symbols

**Approach 3: Treasury Bills (PRIVATE)**
```csv
US_TREASURY_BILLS,1,100000.00,2024-01-01,PRIVATE,TREASURY_BILLS,,,,,
T_BILLS_3M,1,50000.00,2024-01-01,PRIVATE,TREASURY_BILLS,,,,,
```
- Symbol: Descriptive identifier
- Quantity: 1
- Entry Price: Total investment amount
- Investment Class: `PRIVATE`
- Investment Subtype: `TREASURY_BILLS`

**Approach 4: Pure Cash Holdings (PRIVATE)**
```csv
CASH_USD,1,50000.00,2024-01-01,PRIVATE,CASH,,,,,
CASH_CHECKING,1,25000.00,2024-01-01,PRIVATE,CASH,,,,,
```
- Symbol: Descriptive identifier
- Quantity: 1
- Entry Price: Total cash amount
- Investment Class: `PRIVATE`
- Investment Subtype: `CASH`

**Decision Tree for Cash Equivalents:**

```
Does the position have a ticker symbol (SPAXX, VMFXX, etc.)?
├─ YES → Use PUBLIC class, leave subtype blank
│         (Treated like any other publicly traded security)
│
└─ NO → Use PRIVATE class with appropriate subtype:
         ├─ Money market fund without ticker → MONEY_MARKET
         ├─ Treasury bills → TREASURY_BILLS
         └─ Pure cash → CASH
```

**Why This Architecture?**
- **PUBLIC for tickered money markets**: Leverages existing market data infrastructure
- **PRIVATE for non-tickered cash**: Prevents failed API lookups
- **Clear separation**: Ticker = PUBLIC, No ticker = PRIVATE
- **Simple rules**: Easy for users to understand and apply

**Calculation Behavior:**
- **PUBLIC money markets**: Standard market data lookups, no Greeks/factors (minimal volatility)
- **PRIVATE cash equivalents**: Skip market data lookups entirely

---

## 8. Frontend UX Flow

### 8.1 Registration Flow

```
Step 1: Landing Page
├─ User clicks "Sign Up"
└─ Navigates to /register

Step 2: Registration Form
├─ Fields:
│   ├─ Email
│   ├─ Password
│   ├─ Confirm Password
│   ├─ Full Name
│   └─ Invite Code (with help text: "Received an invite code? Enter it here")
│
├─ Validation:
│   ├─ Client-side: Email format, password strength
│   └─ Server-side: POST /api/v1/onboarding/register
│
└─ On Success:
    ├─ Show success message: "Account created! Please login."
    └─ Redirect to /login

Step 3: Login
├─ User enters email/password
├─ POST /api/v1/auth/login
└─ Redirect to /onboarding/import-portfolio
```

### 8.2 Portfolio Creation Flow **[UPDATED: Decoupled Architecture]**

**Note:** Portfolio creation and calculations are now separate API calls for better UX and reliability.

```
Step 1: Create Portfolio Form (/onboarding/import-portfolio)
├─ Welcome message: "Let's set up your portfolio"
│
├─ Fields:
│   ├─ Portfolio Name (text input, required)
│   │   └─ Placeholder: "My Trading Portfolio"
│   │
│   ├─ Description (textarea, optional)
│   │   └─ Placeholder: "Main trading account"
│   │
│   ├─ Starting Equity Balance (number input, required)
│   │   ├─ Prefix: "$"
│   │   ├─ Help text: "Enter your account's total equity (after leverage)"
│   │   └─ Tooltip: "What's equity balance?" → Link to FAQ
│   │
│   └─ Upload Positions CSV (file input, required)
│       ├─ Accept: .csv files only
│       ├─ Max size: 10MB
│       └─ Link: "Download CSV Template" (static file)
│
└─ Submit Button: "Create Portfolio"

Step 2: Portfolio Creation (Fast - <5 seconds)
├─ On Submit: POST /api/v1/onboarding/import-portfolio
├─ Show loading spinner: "Creating portfolio and importing positions..."
├─ Quick response (no batch processing yet)
│
└─ Response includes:
    ├─ portfolio_id
    ├─ positions_imported count
    └─ Message: "Use /api/v1/portfolio/{portfolio_id}/calculate to run calculations"

Step 3: Portfolio Created - Trigger Calculations
├─ Show success message:
│   ├─ "✅ Portfolio created successfully!"
│   ├─ "{N} positions imported"
│   └─ "Ready to calculate risk metrics"
│
├─ Display "Calculate Risk Metrics" button
│   └─ Action: POST /api/v1/portfolio/{portfolio_id}/calculate
│
└─ Alternative: Auto-trigger calculations (optional UX choice)
    ├─ Frontend automatically calls calculate endpoint
    └─ Show: "Running calculations... (30-60 seconds)"

Step 4: Calculation Processing (30-60 seconds)
├─ User clicks "Calculate Risk Metrics"
├─ POST /api/v1/portfolio/{portfolio_id}/calculate
├─ Show loading spinner: "Calculating portfolio analytics..."
├─ Progress indicator (if possible):
│   └─ "Fetching market data... (1/3)"
│   └─ "Calculating Greeks... (2/3)"
│   └─ "Analyzing risk factors... (3/3)"
│
└─ Poll calculation status or wait for completion

Step 5: Calculations Complete
├─ Show success message:
│   ├─ "✅ Calculations complete!"
│   ├─ "Your portfolio is ready to view"
│   └─ Display any warnings:
│       └─ "Note: Greeks unavailable for some positions"
│
└─ Redirect to /portfolio (main dashboard)

Step 6: Error Handling
├─ CSV Validation Errors (Step 2):
│   ├─ Show detailed error list
│   ├─ Highlight problematic rows
│   └─ Allow re-upload without losing form data
│
├─ Portfolio Creation Errors (Step 2):
│   ├─ "User already has portfolio" → Redirect to existing portfolio
│   └─ Other errors → Show message, allow retry
│
└─ Calculation Errors (Step 4):
    ├─ Timeout (>60s):
    │   ├─ "Calculations taking longer than expected"
    │   ├─ "You can view positions now, calculations continue in background"
    │   └─ Redirect to portfolio with partial data
    │
    ├─ Market Data Failures:
    │   ├─ "Some market data unavailable"
    │   ├─ "Portfolio created, calculations partially complete"
    │   └─ Allow manual retry: "Retry Calculations" button
    │
    └─ Complete Failure:
        ├─ "Calculations failed. Portfolio saved with positions."
        ├─ "Please contact support or retry later"
        └─ Redirect to portfolio (positions visible, no analytics)
```

**Key UX Improvements from Decoupled Architecture:**

1. **Faster Initial Feedback**: Portfolio creation completes in <5s (was 30-60s)
2. **Better Error Isolation**: CSV errors don't block portfolio creation
3. **Retry Flexibility**: Users can retry calculations without re-uploading CSV
4. **Progressive Enhancement**: View positions immediately, calculations load async
5. **Clearer Progress**: Two distinct phases with separate loading states

### 8.3 Superuser Impersonation Flow **[PHASE 2 ONLY]**

**Note:** This UX flow is part of Phase 2 admin tooling and should be implemented AFTER Phase 1 is working and tested.

```
Superuser Dashboard (/admin)
├─ List all users
├─ For each user:
│   ├─ Email, created date, has_portfolio flag
│   └─ Button: "Impersonate" (to view portfolio, use impersonation)
│
└─ On "Impersonate" click:
    ├─ POST /api/v1/admin/impersonate
    ├─ Store impersonation token
    ├─ Show banner: "🔒 Viewing as user@example.com | Stop Impersonation"
    └─ Navigate to /portfolio (shows that user's data)

While Impersonating:
├─ All API calls use impersonation token
├─ Persistent banner at top of all pages
├─ Button: "Stop Impersonation"
│
└─ On "Stop Impersonation":
    ├─ POST /api/v1/admin/stop-impersonation
    ├─ Restore original token
    └─ Return to /admin
```

**Implementation Priority:** Phase 2 only - not required for core user onboarding (Phase 1).

### 8.4 UI Components Needed

**Phase 1 Pages:**
1. `/register` - Registration form
2. `/onboarding/import-portfolio` - Portfolio creation

**Phase 2 Pages (Admin Tooling):**
3. `/admin` - Superuser dashboard (list users) **[PHASE 2]**
4. `/admin/invite-codes` - Manage invite codes **[PHASE 2]** *(Future feature)*

**Phase 1 Components:**
1. `<InviteCodeInput>` - Formatted input for SIGMA-XXXX-XXXX
2. `<CSVUploader>` - Drag-drop file upload with validation
3. `<EquityBalanceInput>` - Currency input with help tooltip
5. `<CSVValidationResults>` - Display validation errors/warnings

**Phase 2 Components (Admin Tooling):**
4. `<ImpersonationBanner>` - Persistent banner during impersonation **[PHASE 2]**

---

## 9. Security Model

### 9.1 Invite Code Security **[SIMPLIFIED FOR PHASE 1]**

**Phase 1 Design (50-User MVP):**
- Single master code: `PRESCOTT-LINNAEAN-COWPERTHWAITE`
- Stored in config (`app/config.py`), not database
- No expiration, no usage tracking
- Validation: Simple string comparison

**Implementation:**
```python
# app/config.py
import os

BETA_INVITE_CODE = os.getenv(
    "BETA_INVITE_CODE",
    "PRESCOTT-LINNAEAN-COWPERTHWAITE"  # Default for dev/testing
)

# Validation (simple)
def validate_invite_code(code: str) -> bool:
    return code.strip().upper() == settings.BETA_INVITE_CODE.upper()
```

**Security Model:**
- **Shared Secret**: All 50 beta users receive same code via email
- **Access Control**: Code acts as single key for beta access
- **Trust Model**: White-glove support, direct contact with users
- **Leak Mitigation**: Override via environment variable (no code change required)
- **Production Override**: Set `BETA_INVITE_CODE` env var to avoid Git history exposure
- **Emergency Rotation**: Change env var and redeploy (1-2 minutes)

**Why This Works for 50 Users:**
1. **Simple**: No database, no expiration logic, no tracking
2. **Fast**: Config-based validation (no database lookups)
3. **Secure Enough**: Small trusted cohort with white-glove support
4. **Maintainable**: Single code to manage and distribute
5. **Easily Upgradable**: Can add database-backed codes in Phase 3+ if needed

**Rate Limiting:**
- **Phase 1**: None (trust 50 beta users)
- **Phase 3+**: Add rate limiting if abuse occurs
  - Max 5 failed invite code attempts per IP per hour
  - After 5 failures, require CAPTCHA

**User Experience:**
- Users receive code in welcome email: "Your exclusive beta code is: [master code]"
- All users enter the same code for registration
- Simple, clear, no confusion about multiple codes

**Future Enhancement (Phase 3+):**
If scaling beyond 50 users or need cohort tracking, can implement:
- Database-backed invite code table
- Single-use enforcement
- Expiration dates
- Usage tracking
- Multiple codes for different cohorts

### 9.2 Superuser Access Control **[PHASE 2 ONLY]**

**Note:** All superuser functionality is part of Phase 2 admin tooling. See `ADMIN_AUTH_SUPPLEMENT.md` for complete implementation details.

**Identification:**
- Database flag: `users.is_superuser = TRUE`
- Set manually via SQL or admin script (bootstrap script)
- Cannot be self-granted

**Permissions:**
- All regular user endpoints
- All `/api/v1/admin/*` endpoints
- Can impersonate any user
- Can generate invite codes (future feature)
- Can view all users and portfolios

**Impersonation Token:**
```json
{
  "sub": "target-user-uuid",  // Who we're acting as
  "impersonator_id": "superuser-uuid",  // Who initiated
  "is_impersonation": true,
  "exp": 1698768000  // 8 hours from now
}
```

**Audit Logging:**
- Log all impersonation events (application logs)
- Log all admin endpoint access
- Include: who, when, what, target user
- Structured audit trail deferred to production (Phase 3+)

### 9.3 Data Isolation

**User Sandboxing:**
- Users can ONLY access their own portfolio
- Query filters: `WHERE portfolio.user_id = current_user.id`
- No cross-user data leakage
- Exception: Superusers can access all

**Portfolio Constraints:**
- One portfolio per user (database constraint)
- User cannot create multiple portfolios
- User cannot access other users' portfolios

### 9.4 API Authentication

**All endpoints require authentication except:**
- `POST /api/v1/onboarding/register`
- `POST /api/v1/auth/login`

**JWT Token:**
- Standard format (existing auth system)
- 30-day expiration (configurable)
- Refresh token support
- Stored in `localStorage` (frontend)

**Impersonation Token:**
- 8-hour expiration (shorter for security)
- Cannot be refreshed (must re-impersonate)
- Includes `is_impersonation` flag

### 9.5 Rate Limiting **[PHASE 3+ ONLY]**

**Note:** No rate limiting for Phase 1 MVP. Implement in Phase 3+ if abuse occurs.

**Proposed Rate Limits (Phase 3+ if needed):**

**Registration:**
- Max 50 accounts per IP per day (permissive for testing)
- Max 100 registration attempts per IP per hour

**CSV Upload:**
- Max 50 uploads per user per hour (permissive for testing/iterating)
- Max 10MB file size (hard limit)

**API Calls (General):**
- 1000 requests per minute per user (very permissive)
- 10000 requests per hour per user

**Admin Endpoints:**
- No rate limiting for superusers (trusted)

**Rationale for High Limits:**
- Allow extensive testing and iteration during onboarding
- 50 beta users with white-glove support unlikely to abuse
- Can tighten limits in production if needed

---

## 10. Implementation Phases

### **Phase 1: Core Onboarding** (~1.5 weeks)

**Goals:**
- User registration with invite codes
- Portfolio creation with CSV import
- Get real users onboarded ASAP

**Database:**
- No new tables (invite code is config value)
- No changes to users table (no `is_superuser` column yet)
- Use existing User and Portfolio models

**Services:**
1. InviteCodeService (simple validation against config)
2. CSV parser service
3. Position import service
4. Onboarding service orchestration

**API Endpoints (3):**
- `POST /api/v1/onboarding/register`
- `POST /api/v1/onboarding/import-portfolio` (no automatic batch trigger)
- `POST /api/v1/portfolio/{portfolio_id}/calculate` (user-triggered calculations)

**Additional Work:**
- Error handling (~35 error codes)
- CSV template (static file)
- Batch processing integration
- Testing with real user workflows

**Success Criteria:**
- ✅ User can register with invite code `PRESCOTT-LINNAEAN-COWPERTHWAITE`
- ✅ User can upload CSV and create portfolio
- ✅ Portfolio created with positions imported (fast, <5s)
- ✅ User can trigger calculations via separate endpoint
- ✅ Batch processing runs when triggered (30-60s)
- ✅ Position data and calculation results appear in database
- ✅ Validation errors are clear and actionable
- ✅ Can test by creating actual accounts directly (no impersonation needed)

**Testing Strategy:**
- Create test accounts like demo accounts (just login directly)
- Ask beta users for screenshots/screen shares for support
- No admin tooling needed yet

**UUID Strategy:** Deterministic (for testing)

**Status:** ✅ COMPLETED (October 30, 2025)

---

### **Phase 2: Multi-Portfolio Support** (~2 days) 🔄 IN PROGRESS

**Goals:**
- Enable users to import multiple portfolios via CSV
- Update CSV import endpoint to support account metadata
- Integrate with existing multi-portfolio CRUD APIs
- Support family office use cases (multiple accounts per user)

**Database:**
- No schema changes (multi-portfolio migration already complete)
- Use existing `account_name`, `account_type`, `is_active` columns added in migration `9b0768a49ad8`

**Services:**
- No new services needed
- Update existing OnboardingService to support account metadata
- Update CSV parser to validate account_type values

**API Endpoint Updates:**
1. Update `POST /api/v1/onboarding/import-portfolio`:
   - Add required `account_name` field
   - Add required `account_type` field (9 valid types)
   - Remove "one portfolio per user" validation
   - Update response schema to include account metadata

2. Update `GET /api/v1/onboarding/csv-template`:
   - Add account type guidance to template documentation

**Documentation Tasks:**
3. Document portfolio selection patterns (after login with multiple portfolios)
4. Document relationship between CSV import flow and CRUD flow
5. Update error codes (ERR_PORT_001 no longer "already has portfolio")

**Integration:**
- CSV import creates portfolios compatible with `/api/v1/portfolios` CRUD endpoints
- Multi-portfolio aggregate analytics work automatically with imported portfolios
- Both flows use same PortfolioService and PositionService

**Success Criteria:**
- ✅ User can import 1st portfolio with account_name and account_type
- ✅ User can import 2nd+ portfolios (no single-portfolio restriction)
- ✅ Response includes account_name and account_type fields
- ✅ CSV template documents account type field
- ✅ Documentation explains CSV import vs CRUD flows
- ✅ Validation prevents duplicate account names for same user
- ✅ Multi-portfolio aggregate analytics work with imported portfolios

**Testing Strategy:**
- Import 2 portfolios for same user (taxable + IRA)
- Verify aggregate analytics endpoints work
- Test error for duplicate account names
- Verify account_type validation (reject invalid types)

**Effort:** ~10-12 hours (1-2 days)

**Status:** 🔄 IN PROGRESS

---

### **Phase 3: Admin & Superuser Tooling** (~1 week) *Implement after Phase 2 is working and tested*

**Goals:**
- Superuser authentication system
- User impersonation for testing
- Admin dashboard functionality

**Database:**
- Add `is_superuser` column to users table
- Create bootstrap script for first superuser

**All work from `ADMIN_AUTH_SUPPLEMENT.md`:**
1. Database migration (`users.is_superuser` column)
2. Bootstrap script (`scripts/admin/create_first_superuser.py`)
3. JWT token modifications (add `is_superuser` claim)
4. Auth dependencies (`get_current_superuser()`)
5. Login response updates (include user info)

**Services:**
- ImpersonationService (token generation, switching)

**API Endpoints (3):**
- `POST /api/v1/admin/impersonate`
- `POST /api/v1/admin/stop-impersonation`
- `GET /api/v1/admin/users`

**Testing:**
- Bootstrap first superuser
- Test impersonation flow
- Test admin endpoint access control
- Verify regular users cannot access admin endpoints

**Success Criteria:**
- ✅ Bootstrap script creates first superuser
- ✅ Superuser can list all users
- ✅ Superuser can impersonate any user
- ✅ Impersonation token works correctly
- ✅ JWT tokens include `is_superuser` claim
- ✅ Regular users get 403 on admin endpoints

---

### Phase 4: Production Hardening (Optional - Future)

**Goals:**
- Security improvements
- UUID migration from deterministic to random
- Rate limiting
- Monitoring

**Tasks:**

#### 1. UUID Migration Strategy

**Current State (Phase 1 & 2):**
- All users: Deterministic UUIDs based on email hash
- Rationale: Enables thorough testing and easy identification

**Target State (Phase 3):**
- Demo users (`@sigmasight.com`): Keep deterministic UUIDs
- Real users: Random UUIDs (uuid4)

**Implementation:**

**Step 1: Add UUID Generation Strategy**

```python
# app/core/uuid_strategy.py
from uuid import UUID, uuid4, uuid5, NAMESPACE_DNS
from typing import Optional

class UUIDStrategy:
    """
    UUID generation strategy supporting hybrid approach.

    Phase 1/2: All deterministic (for testing)
    Phase 3: Demo deterministic, real users random
    """

    @staticmethod
    def generate_user_uuid(email: str, use_deterministic: Optional[bool] = None) -> UUID:
        """
        Generate UUID for user based on email and strategy.

        Args:
            email: User email address
            use_deterministic: Override strategy (None = auto-detect)

        Returns:
            UUID object

        Strategy:
        - Demo users (@sigmasight.com): Always deterministic
        - Real users: Deterministic (Phase 1/2), Random (Phase 3+)
        - Override: Explicit use_deterministic parameter
        """
        # Check if demo user (always deterministic)
        is_demo = email.endswith('@sigmasight.com')

        # Determine strategy
        if use_deterministic is not None:
            should_use_deterministic = use_deterministic
        elif is_demo:
            should_use_deterministic = True
        else:
            # Check config (Phase 3: switch to False for production)
            from app.config import settings
            should_use_deterministic = getattr(settings, 'USE_DETERMINISTIC_UUIDS', True)

        if should_use_deterministic:
            # Deterministic: uuid5(NAMESPACE_DNS, email)
            return uuid5(NAMESPACE_DNS, email.lower())
        else:
            # Random: uuid4()
            return uuid4()
```

**Step 2: Configuration**

```python
# app/config.py
class Settings(BaseSettings):
    # ... existing settings ...

    # UUID Strategy (Phase 3)
    USE_DETERMINISTIC_UUIDS: bool = True  # Phase 1/2: True, Phase 3: False
```

**Step 3: Migration Path**

```sql
-- Phase 3 Migration Script
-- Note: Existing users keep their UUIDs
-- Only NEW users after Phase 3 get random UUIDs

-- No data migration needed! Just config change:
-- Change USE_DETERMINISTIC_UUIDS from True to False

-- Demo users (@sigmasight.com) automatically remain deterministic
-- Real users created after Phase 3 get random UUIDs
```

**Step 4: Backward Compatibility**

```python
# Existing demo seeding scripts work unchanged
# Demo users always get deterministic UUIDs regardless of config

async def seed_demo_portfolios(db: AsyncSession):
    for email in DEMO_USERS:
        # These always get deterministic UUIDs (email ends with @sigmasight.com)
        user_id = UUIDStrategy.generate_user_uuid(email)
        # ... rest of seeding logic
```

**Testing Strategy:**

1. **Phase 1/2 (Deterministic):**
   - Set `USE_DETERMINISTIC_UUIDS=True`
   - Create test users → verify same UUID for same email
   - Test all features with deterministic UUIDs

2. **Phase 3 Testing (Staging):**
   - Set `USE_DETERMINISTIC_UUIDS=False` in staging
   - Create new real users → verify random UUIDs (uuid4)
   - Create new demo users → verify deterministic UUIDs (uuid5)
   - Verify existing users unaffected

3. **Phase 3 Production:**
   - Deploy with `USE_DETERMINISTIC_UUIDS=False`
   - Monitor new user registrations
   - Verify demo seeding still works

**When to Migrate:**
- After 50+ real users successfully onboarded (Phase 1/2 complete)
- After thorough testing with deterministic UUIDs
- When ready for production-grade security

**Benefits of Hybrid Approach:**
- ✅ Demo users remain testable (same UUID every time)
- ✅ Real users get production-grade random UUIDs
- ✅ No data migration needed (just config change)
- ✅ Backward compatible with existing demo seeding
- ✅ Can test both strategies in staging

#### 2. Rate Limiting

**After UUID migration is stable:**
- Implement per-endpoint limits
- Add Redis for distributed rate limiting (optional)
- Add CAPTCHA for invite code validation

#### 3. Monitoring

**Add metrics for:**
- Registration attempts
- CSV upload success/failure rates
- Batch processing duration
- Impersonation events
- Set up alerts for anomalies

#### 4. Security Audit

- Review all endpoints for auth bypass
- Test user isolation
- Verify no SQL injection vectors
- Check file upload security

#### 5. Documentation

- API documentation (Swagger/ReDoc)
- User guide for CSV import
- Admin guide for superuser management

**Success Criteria:**
- ✅ Demo users keep deterministic UUIDs (testable)
- ✅ New real users get random UUIDs (secure)
- ✅ Existing users unaffected by migration
- ✅ Rate limits prevent abuse
- ✅ Monitoring dashboards show key metrics
- ✅ Security audit passes
- ✅ Documentation complete

---

### Phase 4: Production Launch (Week 5)

**Goals:**
- Deploy to production
- Monitor closely
- Support first users

**Tasks:**
1. **Pre-Launch:**
   - Generate initial batch of invite codes (20-30)
   - Set up production monitoring
   - Prepare support documentation
   - Test end-to-end in production environment

2. **Launch:**
   - Deploy backend changes
   - Deploy frontend changes
   - Send invite codes to first cohort (5-10 users)
   - Monitor registration and portfolio creation

3. **Post-Launch:**
   - Gather user feedback
   - Fix any critical bugs
   - Monitor batch processing performance
   - Generate additional invite codes as needed

**Success Criteria:**
- ✅ 5+ users successfully onboarded
- ✅ No critical bugs in production
- ✅ Batch processing completes within 60s
- ✅ User feedback positive

---

## 11. Migration Plan

### 11.1 Unified Pipeline Strategy

**Current State:**
- Demo users: `DEMO_PORTFOLIOS` constant → `seed_demo_portfolios.py`
- Real users: CSV upload → New onboarding service

**Desired State (Future):**
- Both use same code path
- Demo users: Auto-generated CSV → Same import service
- Real users: User-uploaded CSV → Same import service

**Migration Approach (Phase 1: Hybrid):**

**Keep Separate:**
- Demo seeding script unchanged
- New onboarding service for real users
- Separate code paths for now

**Share Common Utilities:**
```python
# app/services/position_creation_service.py
class PositionCreationService:
    """Shared logic for creating positions from data"""

    async def create_position_from_data(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        user_id: UUID,
        position_data: PositionData
    ) -> Position:
        """
        Create position record (used by both demo seeding and CSV import).

        Handles:
        - Position type determination
        - Investment class auto-detection
        - Tag creation
        - Sector auto-tagging
        """
```

**Usage:**
```python
# Demo seeding (existing)
from app.services.position_creation_service import PositionCreationService

async def seed_demo_portfolios(db):
    service = PositionCreationService(db)

    for portfolio_data in DEMO_PORTFOLIOS:
        # ... create portfolio ...
        for pos_data in portfolio_data["positions"]:
            position = await service.create_position_from_data(
                db, portfolio.id, user.id, pos_data
            )

# CSV import (new)
from app.services.position_creation_service import PositionCreationService

async def import_positions(db, portfolio_id, user_id, csv_positions):
    service = PositionCreationService(db)

    for pos_data in csv_positions:
        position = await service.create_position_from_data(
            db, portfolio_id, user_id, pos_data
        )
```

### 11.2 Future Refactoring (Phase 5+)

**When to unify:**
- After 50+ real users successfully onboarded
- When confidence in CSV import is high
- When demo seeding needs major changes

**Unified Approach:**
```python
# Step 1: Convert DEMO_PORTFOLIOS to CSV files
# scripts/database/generate_demo_csvs.py

DEMO_CSVS = {
    "individual": "/data/demo_individual.csv",
    "hnw": "/data/demo_hnw.csv",
    "hedge_fund": "/data/demo_hedge_fund.csv"
}

# Step 2: Use onboarding service for demo seeding
async def seed_demo_portfolios(db):
    service = OnboardingService(db)

    for email, csv_path in DEMO_USERS.items():
        # Create user
        user = await service.register_user(
            email=email,
            password="demo12345",
            full_name=...,
            invite_code="DEMO-INTERNAL-CODE",
            account_type="DEMO"
        )

        # Create portfolio
        with open(csv_path) as f:
            result = await service.create_portfolio_with_csv(
                user_id=user.id,
                portfolio_name=...,
                equity_balance=...,
                csv_file=f
            )
```

**Benefits:**
- Single code path (easier to maintain)
- Demo seeding tests real import logic
- CSV changes automatically apply to both

**Risks:**
- Demo seeding more fragile (depends on CSV import)
- Breaking changes affect demos
- Need CSV files in repository

**Recommendation:**
- Stick with hybrid approach (Phase 1-4)
- Revisit after production launch
- Only unify if clear benefits outweigh risks

---

## 12. Testing Strategy

Testing is separated by implementation phase, with each phase building on the previous one.

---

### **Phase 1 Testing: Core Onboarding**

Test the MVP functionality: registration, CSV import, portfolio creation.

#### 12.1.1 Unit Tests (Phase 1)

**Services:**
- `test_invite_code_service.py`
  - Validate invite code matches config value
  - Case-insensitive validation
  - Whitespace handling
  - Invalid code rejection

- `test_csv_parser_service.py`
  - Valid CSV parsing (all 12 columns)
  - Invalid CSV detection (all error codes from Section 4.2/4.3)
  - Edge cases (empty rows, special characters, quotes)
  - Investment class auto-detection
  - Options symbol parsing (OCC format)
  - Cash position subtypes (MONEY_MARKET, TREASURY_BILLS, CASH)

- `test_position_import_service.py`
  - Position creation from parsed data
  - Investment class validation
  - Position type determination (LONG/SHORT, options types)
  - Deterministic UUID generation
  - Sector auto-tagging

- `test_onboarding_service.py`
  - User registration flow with config-based invite code
  - Portfolio creation orchestration
  - Error handling for duplicate users/portfolios
  - Graceful degradation for batch processing errors

#### 12.1.2 Integration Tests (Phase 1)

**Registration Flow:**
```python
async def test_registration_with_valid_invite_code():
    """Test user registration with master invite code."""
    response = await client.post("/api/v1/onboarding/register", json={
        "email": "test@example.com",
        "password": "SecurePass123!",
        "full_name": "Test User",
        "invite_code": "PRESCOTT-LINNAEAN-COWPERTHWAITE"  # Master code from config
    })

    assert response.status_code == 201
    assert response.json()["user_id"] is not None
    assert response.json()["email"] == "test@example.com"


async def test_registration_with_invalid_invite_code():
    """Test registration fails with invalid code."""
    response = await client.post("/api/v1/onboarding/register", json={
        "email": "test@example.com",
        "password": "SecurePass123!",
        "full_name": "Test User",
        "invite_code": "WRONG-CODE-HERE"
    })

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ERR_INVITE_001"
```

**Portfolio Creation:**
```python
async def test_create_portfolio_with_csv():
    """Test portfolio creation with CSV upload (no batch trigger)."""
    # Register and login
    token = await register_and_login()

    # Upload CSV
    with open("test_data/valid_positions.csv", "rb") as f:
        response = await client.post(
            "/api/v1/onboarding/import-portfolio",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "portfolio_name": "Test Portfolio",
                "description": "Test portfolio for integration testing",
                "equity_balance": "500000.00"
            },
            files={"csv_file": f}
        )

    assert response.status_code == 201
    assert response.json()["positions_imported"] > 0
    assert "portfolio_id" in response.json()
    # Verify message about using calculate endpoint
    assert "calculate" in response.json()["message"]


async def test_user_triggered_batch_calculations():
    """Test user can trigger batch calculations for their portfolio."""
    # Create portfolio first
    portfolio_id = await create_test_portfolio()

    # Trigger calculations
    response = await client.post(
        f"/api/v1/portfolio/{portfolio_id}/calculate",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 202
    assert response.json()["status"] == "started"
    assert response.json()["batch_run_id"] is not None
```

**CSV Validation:**
```python
async def test_csv_validation_errors():
    """Test CSV validation catches all error types."""
    token = await register_and_login()

    # Test with invalid CSV (bad dates)
    with open("test_data/invalid_dates.csv", "rb") as f:
        response = await client.post(
            "/api/v1/onboarding/import-portfolio",
            headers={"Authorization": f"Bearer {token}"},
            data={"portfolio_name": "Test", "equity_balance": "500000.00"},
            files={"csv_file": f}
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "ERR_CSV_007"
    assert len(response.json()["error"]["details"]) > 0
```

#### 12.1.3 End-to-End Tests (Phase 1)

**Full Onboarding Flow:**
```python
async def test_complete_onboarding_flow():
    """Test complete user journey from registration to portfolio view."""
    # Step 1: Register user with master invite code
    register_response = await client.post("/api/v1/onboarding/register", json={
        "email": "e2e_test@example.com",
        "password": "SecurePass123!",
        "full_name": "E2E Test User",
        "invite_code": "PRESCOTT-LINNAEAN-COWPERTHWAITE"
    })
    assert register_response.status_code == 201

    # Step 2: Login
    login_response = await client.post("/api/v1/auth/login", json={
        "email": "e2e_test@example.com",
        "password": "SecurePass123!"
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Step 3: Create portfolio with CSV
    with open("test_data/valid_full.csv", "rb") as f:
        portfolio_response = await client.post(
            "/api/v1/onboarding/import-portfolio",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "portfolio_name": "E2E Test Portfolio",
                "equity_balance": "500000.00"
            },
            files={"csv_file": f}
        )
    assert portfolio_response.status_code == 201
    portfolio_id = portfolio_response.json()["portfolio_id"]

    # Step 4: Trigger batch calculations
    calc_response = await client.post(
        f"/api/v1/portfolio/{portfolio_id}/calculate",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert calc_response.status_code == 202

    # Step 5: Verify positions in database
    async with get_async_session() as db:
        positions = await db.execute(
            select(Position).where(Position.portfolio_id == portfolio_id)
        )
        position_list = positions.scalars().all()
        assert len(position_list) > 0

    # Step 6: Verify portfolio accessible via API
    portfolio_get = await client.get(
        "/api/v1/data/portfolio/complete",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert portfolio_get.status_code == 200
    assert portfolio_get.json()["portfolio"]["id"] == portfolio_id
```

**Cash Position Handling:**
```python
async def test_cash_position_classification():
    """Test PUBLIC money markets vs PRIVATE cash handling."""
    token = await register_and_login()

    # CSV with both tickered and non-tickered cash
    csv_content = """Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share
SPAXX,10000.00,1.00,2024-01-01,PUBLIC,,,,,,,
VMFXX,5000.00,1.00,2024-01-01,PUBLIC,,,,,,,
CASH_USD,1,50000.00,2024-01-01,PRIVATE,CASH,,,,,
US_TREASURY_BILLS,1,100000.00,2024-01-01,PRIVATE,TREASURY_BILLS,,,,,
"""

    with open("test_data/cash_positions.csv", "w") as f:
        f.write(csv_content)

    with open("test_data/cash_positions.csv", "rb") as f:
        response = await client.post(
            "/api/v1/onboarding/import-portfolio",
            headers={"Authorization": f"Bearer {token}"},
            data={"portfolio_name": "Cash Test", "equity_balance": "165000.00"},
            files={"csv_file": f}
        )

    assert response.status_code == 201
    assert response.json()["positions_imported"] == 4

    # Verify classification in database
    portfolio_id = response.json()["portfolio_id"]
    async with get_async_session() as db:
        positions = await db.execute(
            select(Position).where(Position.portfolio_id == portfolio_id)
        )
        position_list = positions.scalars().all()

        # Tickered money markets should be PUBLIC
        spaxx = next(p for p in position_list if p.symbol == "SPAXX")
        assert spaxx.investment_class == "PUBLIC"

        vmfxx = next(p for p in position_list if p.symbol == "VMFXX")
        assert vmfxx.investment_class == "PUBLIC"

        # Non-tickered cash should be PRIVATE
        cash = next(p for p in position_list if p.symbol == "CASH_USD")
        assert cash.investment_class == "PRIVATE"
        assert cash.investment_subtype == "CASH"

        t_bills = next(p for p in position_list if p.symbol == "US_TREASURY_BILLS")
        assert t_bills.investment_class == "PRIVATE"
        assert t_bills.investment_subtype == "TREASURY_BILLS"
```

---

### **Phase 2 Testing: Admin & Superuser**

Test admin tooling functionality after Phase 1 is working and tested.

#### 12.2.1 Unit Tests (Phase 2)

**Services:**
- `test_impersonation_service.py`
  - Token generation for impersonation
  - Original user restoration
  - Expiration handling
  - Permission checks

**Dependencies:**
- `test_get_current_superuser.py`
  - Verify superuser flag checked
  - Regular users rejected
  - Token validation

#### 12.2.2 Integration Tests (Phase 2)

**Impersonation Flow:**
```python
async def test_superuser_impersonation():
    """Test complete impersonation workflow."""
    # Create superuser
    superuser_token = await bootstrap_superuser("admin@sigmasight.io")

    # Create regular user
    user_id = await create_regular_user("user@example.com")

    # Start impersonation
    impersonate_response = await client.post(
        "/api/v1/admin/impersonate",
        headers={"Authorization": f"Bearer {superuser_token}"},
        json={"target_user_id": user_id}
    )
    assert impersonate_response.status_code == 200
    impersonation_token = impersonate_response.json()["impersonation_token"]

    # Verify can access user's data
    portfolio_response = await client.get(
        "/api/v1/data/portfolio/complete",
        headers={"Authorization": f"Bearer {impersonation_token}"}
    )
    assert portfolio_response.status_code == 200

    # Stop impersonation
    stop_response = await client.post(
        "/api/v1/admin/stop-impersonation",
        headers={"Authorization": f"Bearer {impersonation_token}"}
    )
    assert stop_response.status_code == 200
    assert "original_token" in stop_response.json()


async def test_regular_user_cannot_impersonate():
    """Test that regular users cannot impersonate."""
    regular_token = await login_regular_user()

    response = await client.post(
        "/api/v1/admin/impersonate",
        headers={"Authorization": f"Bearer {regular_token}"},
        json={"target_user_id": "some-uuid"}
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ERR_ADMIN_001"
```

**Admin User Listing:**
```python
async def test_list_all_users():
    """Test superuser can list all users."""
    superuser_token = await bootstrap_superuser()

    response = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {superuser_token}"}
    )

    assert response.status_code == 200
    assert "users" in response.json()
    assert len(response.json()["users"]) >= 3  # At least 3 demo users
```

---

### **Phase 3 Testing: Production Hardening**

Test production-ready features (UUID migration, rate limiting).

#### 12.3.1 UUID Migration Tests

```python
async def test_hybrid_uuid_strategy():
    """Test UUID generation strategy."""
    from app.core.uuid_strategy import UUIDStrategy

    # Demo user - always deterministic
    demo_uuid_1 = UUIDStrategy.generate_user_uuid("demo@sigmasight.com")
    demo_uuid_2 = UUIDStrategy.generate_user_uuid("demo@sigmasight.com")
    assert demo_uuid_1 == demo_uuid_2  # Same UUID every time

    # Real user - depends on config
    # Phase 1/2: deterministic
    real_uuid_1 = UUIDStrategy.generate_user_uuid("user@example.com", use_deterministic=True)
    real_uuid_2 = UUIDStrategy.generate_user_uuid("user@example.com", use_deterministic=True)
    assert real_uuid_1 == real_uuid_2

    # Phase 3: random
    real_uuid_3 = UUIDStrategy.generate_user_uuid("user@example.com", use_deterministic=False)
    real_uuid_4 = UUIDStrategy.generate_user_uuid("user@example.com", use_deterministic=False)
    assert real_uuid_3 != real_uuid_4  # Different UUIDs
```

---

### 12.4 CSV Test Files

**Phase 1 Test Files** (12-column template):
- `valid_basic.csv` - Minimal valid CSV (4 required columns, 10 rows)
- `valid_full.csv` - All 12 columns, mixed asset types (50 rows)
- `valid_cash_positions.csv` - PUBLIC money markets + PRIVATE cash
- `valid_options.csv` - Options positions (OCC format + separate fields)
- `valid_private.csv` - Private assets (PE, VC, real estate, crypto)
- `invalid_dates.csv` - Bad date formats (01/15/2024 instead of 2024-01-15)
- `invalid_numbers.csv` - Non-numeric quantities/prices ("N/A", "TBD")
- `invalid_symbols.csv` - Symbols >100 chars, invalid characters
- `missing_required.csv` - Missing symbols/dates/quantities
- `duplicate_positions.csv` - Same symbol+entry_date twice
- `empty_file.csv` - Empty file (0 rows)
- `no_header.csv` - Missing header row

**Broker Format Test Files** (for compatibility testing):
- `schwab_export.csv` - Real Schwab positions export
- `fidelity_export.csv` - Real Fidelity positions export
- `vanguard_export.csv` - Real Vanguard positions export

**Phase 2 Test Files** (edge cases):
- `max_positions.csv` - 1000 positions (performance testing)
- `unicode_symbols.csv` - Positions with unicode characters
- `mixed_errors.csv` - Multiple error types in one file (ERR_POS_003, ERR_POS_011, ERR_POS_015)

---

## Appendix A: Sample CSV Files

This appendix provides 6 realistic CSV examples: 3 broker-exported formats with common errors, and 3 error-free SigmaSight template CSVs.

---

### **Broker Format Examples (With Intentional Errors)**

These examples show actual broker export formats and highlight common mistakes users make when converting to our template.

#### A.1 Schwab Positions Export (❌ Has Errors)

**Example snippet from Schwab's "Positions" download:**

```csv
Symbol,Description,Qty,Price,Cost Basis,Gain $,Gain %,% of Acct,Security Type
AAPL,APPLE INC,100,$225.00,$15800.00,$6700.00,42.41%,13.88%,Stocks
CMF,ISHARES CA MUNI,54,$57.61,$2984.33,$126.41,4.24%,1.92%,ETFs
Cash & Cash Investments,--,--,--,$16073.35,--,--,9.92%,Cash
```

**Common Errors When Converting:**
1. ❌ **Missing Entry Date**: Schwab exports don't include purchase dates - users must add manually
2. ❌ **Cost Basis is Total, Not Per-Share**: Shows $15,800 total instead of $158/share
3. ❌ **Cash Row Has Dashes**: "Cash & Cash Investments" row is unusable without manual editing
4. ❌ **Column Names Don't Match**: Uses "Qty" instead of "Quantity", "Cost Basis" instead of "Entry Price Per Share"

**What Users Must Do:**
- Calculate per-share cost basis: Total Cost Basis ÷ Quantity (e.g., $15,800 ÷ 100 = $158.00)
- Look up purchase dates from transaction history or broker statements
- Convert cash row to proper format (symbol, quantity, price)
- Match column names to SigmaSight template

---

#### A.2 Fidelity Positions Export (❌ Has Errors)

**Example snippet from Fidelity's "Positions" CSV:**

```csv
Account Number,Account Name,Symbol,Description,Quantity,Last Price,Current Value,Total Gain/Loss Dollar,Total Gain/Loss Percent,Cost Basis Total,Average Cost Basis,Type
Z43122858,Trust,AAPL,APPLE INC,100,$225.00,$22500.00,+$6700.00,+42.41%,$15800.00,$158.00,Cash
Z43122858,Trust,MSFT,MICROSOFT CORP,50,$350.00,$17500.00,+$2500.00,+16.67%,$15000.00,$300.00,Cash
Z43122858,Trust,SPAXX**,FIDELITY GOVT MMF,8271.36,$1.00,$8271.36,$0.00,0.00%,$8271.36,$1.00,Cash
```

**Common Errors When Converting:**
1. ❌ **Missing Entry Date**: Users must add manually from transaction history
2. ❌ **Extra Columns**: Account Number, Account Name, Description not needed
3. ❌ **Money Market Symbol Has Asterisks**: SPAXX** needs cleaning to SPAXX
4. ❌ **Column Name Mismatch**: "Average Cost Basis" vs "Entry Price Per Share"

**What Users Must Do:**
- Remove extra columns (Account Number, Account Name, Description)
- Add Entry Date column with actual purchase dates
- Clean up money market symbol (SPAXX** → SPAXX)
- Remember: SPAXX with ticker should be PUBLIC class, not PRIVATE

---

#### A.3 Vanguard Positions Export (❌ Has Errors)

**Example snippet from Vanguard's "Holdings" CSV:**

```csv
Account Number,Investment Name,Symbol,Shares,Share Price,Total Value
20796525,VANGUARD TARGET RETIREMENT 2030,VTHRX,7711.87,$43.96,$339013.81
20796525,VANGUARD FEDERAL MONEY MARKET,VMFXX,8271.36,$1.00,$8271.36
20796525,VANGUARD TOTAL STOCK MKT IDX,VTSAX,125.50,$125.00,$15687.50
```

**Common Errors When Converting:**
1. ❌ **Share Price is CURRENT Price, Not Cost Basis**: $43.96 is today's price, not what user paid
2. ❌ **Missing Entry Date**: Not included in Vanguard exports
3. ❌ **Missing Cost Basis Entirely**: Vanguard doesn't export average cost basis in this format
4. ❌ **Extra Columns**: Account Number, Investment Name not needed

**⚠️ Critical Limitation:** Vanguard positions exports do NOT include cost basis. Users must:
- Use Vanguard's "Cost Basis" report instead, OR
- Manually look up purchase prices from transaction history

**What Users Must Do:**
- Download Vanguard's separate "Cost Basis" report to get Entry Price Per Share
- Add Entry Date from transaction history
- Remove extra columns
- Use oldest purchase date if multiple purchases

---

### **SigmaSight Template Examples (✅ Error-Free)**

These examples show properly formatted CSVs ready for import.

#### A.4 Mixed Portfolio (Stocks, ETFs, Cash) - ✅ Valid

**Demonstrates:** PUBLIC stocks/ETFs, PUBLIC money markets with tickers, PRIVATE cash subtypes

```csv
Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share
AAPL,100,158.00,2024-01-15,PUBLIC,,,,,,,
MSFT,50,350.00,2024-02-01,PUBLIC,,,,,,,
VOO,20,631.00,2024-03-15,PUBLIC,,,,,,,
SPAXX,10000.00,1.00,2024-01-01,PUBLIC,,,,,,,
VMFXX,5000.00,1.00,2024-01-01,PUBLIC,,,,,,,
CASH_USD,1,25000.00,2024-01-01,PRIVATE,CASH,,,,,
US_TREASURY_BILLS,1,50000.00,2024-01-01,PRIVATE,TREASURY_BILLS,,,,,
```

**Requirements:**
- 4 required columns: Symbol, Quantity, Entry Price Per Share, Entry Date
- Date format: YYYY-MM-DD
- Money markets WITH tickers (SPAXX, VMFXX) → PUBLIC class
- Cash equivalents WITHOUT tickers → PRIVATE class with subtype
- Investment Class optional (will auto-detect PUBLIC for stocks/ETFs)

---

#### A.5 Options Portfolio - ✅ Valid

**Demonstrates:** Long/short options using OCC symbol format

```csv
Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share
SPY250919C00460000,200,7.00,2024-01-10,OPTIONS,,SPY,460.00,2025-09-19,CALL,,
SPY250919P00400000,-150,6.50,2024-01-10,OPTIONS,,SPY,400.00,2025-09-19,PUT,,
QQQ250815C00420000,150,7.00,2024-01-10,OPTIONS,,QQQ,420.00,2025-08-15,CALL,,
AAPL250620C00180000,100,12.50,2024-01-15,OPTIONS,,AAPL,180.00,2025-06-20,CALL,,
```

**Requirements:**
- Symbol can be OCC format (e.g., SPY250919C00460000) OR simple ticker with separate columns
- OPTIONS class requires: Underlying Symbol, Strike Price, Expiration Date, Option Type
- Negative quantity indicates short position (sold options)
- Entry Price Per Share is premium paid/received per contract

---

#### A.6 Alternative Assets Portfolio - ✅ Valid

**Demonstrates:** PRIVATE assets including all 3 cash subtypes

```csv
Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share
BX_PRIVATE_EQUITY,1,500000.00,2023-06-01,PRIVATE,PRIVATE_EQUITY,,,,,
HOME_REAL_ESTATE,1,750000.00,2020-01-01,PRIVATE,REAL_ESTATE,,,,,
CRYPTO_BTC_ETH,1,125000.00,2022-06-01,PRIVATE,CRYPTOCURRENCY,,,,,
ART_COLLECTION,1,250000.00,2021-03-15,PRIVATE,ART,,,,,
CASH_MM_FUND,1,50000.00,2024-01-01,PRIVATE,MONEY_MARKET,,,,,
T_BILLS_6M,1,100000.00,2024-01-01,PRIVATE,TREASURY_BILLS,,,,,
CASH_CHECKING,1,75000.00,2024-01-01,PRIVATE,CASH,,,,,
```

**Requirements:**
- PRIVATE class requires Investment Subtype
- Quantity typically 1 for non-divisible assets
- Entry Price = total investment amount (not per-unit)
- Symbol is descriptive identifier (no real ticker)
- **3 Cash Subtypes**:
  - `MONEY_MARKET` - Money market funds WITHOUT ticker symbols
  - `TREASURY_BILLS` - Treasury bills and bonds
  - `CASH` - Pure cash holdings (checking, savings)
- Money markets WITH tickers (SPAXX, VMFXX, etc.) should use PUBLIC class instead

---

### **Key Conversion Rules**

**From Broker CSV → SigmaSight Template:**

1. **Entry Date** - Not included in most broker exports
   - Solution: Look up from transaction history or broker statements
   - Use earliest purchase date if multiple buys

2. **Entry Price Per Share** - Often shown as "Total Cost Basis"
   - Solution: Divide total cost basis by quantity
   - Example: $15,800 total ÷ 100 shares = $158.00 per share

3. **Cash Positions**
   - Money markets WITH tickers (SPAXX, VMFXX, VUSXX) → PUBLIC class
   - Money markets WITHOUT tickers → PRIVATE class, MONEY_MARKET subtype
   - Treasury bills → PRIVATE class, TREASURY_BILLS subtype
   - Pure cash → PRIVATE class, CASH subtype

4. **Investment Class**
   - Can leave blank for stocks/ETFs (auto-detects PUBLIC)
   - Must specify for OPTIONS and PRIVATE
   - Decision tree: Has ticker symbol? Use PUBLIC. No ticker? Use PRIVATE.

---

## Appendix B: FAQ for Users

### Q: What is "Starting Equity Balance"?

**A:** Your portfolio's total equity after accounting for leverage.

**Example:**
- Account Value: $500,000
- Margin Loan: $100,000
- Equity Balance: $400,000 ✅ (Use this)

For most users without margin/leverage, Equity Balance = Account Value.

### Q: What date should I use for "Entry Date"?

**A:** Use the **earliest purchase date** for that position.

If you bought AAPL in multiple trades:
- Jan 15: 50 shares @ $150
- Mar 20: 30 shares @ $170
- Jun 10: 20 shares @ $160

Use **Jan 15, 2024** as Entry Date.

### Q: What price should I use for "Entry Price Per Share"?

**A:** Use your broker's **Average Cost Basis** per share.

Your broker shows:
- Total Cost Basis: $15,800
- Quantity: 100 shares
- Average Cost Basis: $158/share ✅ (Use this)

### Q: Can I import my broker's CSV directly?

**A:** No, you must use our standardized template.

We're working on supporting direct imports from:
- Schwab
- Fidelity
- Vanguard

For now, please download our template and manually transfer your position data.

### Q: What if I have options positions?

**A:** Include these additional columns:
- Underlying Symbol (e.g., SPY)
- Strike Price (e.g., 460.00)
- Expiration Date (e.g., 2025-09-19)
- Option Type (CALL or PUT)

You can use either:
- OCC symbol format: `SPY250919C00460000`
- OR separate columns

### Q: Can I import closed positions?

**A:** Yes! Include:
- Exit Date
- Exit Price Per Share

This allows tracking historical performance.

### Q: What happens if my CSV has errors?

**A:** The entire import will be rejected. Fix all errors and try again.

We validate every row to ensure data quality. Use the "Validate CSV" button to check before submitting.

---

## Appendix C: Decision Log

| Date | Decision | Rationale | Approver |
|------|----------|-----------|----------|
| 2025-10-28 | Single aggregated position per symbol | Simpler than tax lots, matches broker CSVs | User |
| 2025-10-28 | CSV required for portfolio creation | Ensure data quality | User |
| 2025-10-28 | Synchronous batch processing | Simpler for MVP, 30-60s acceptable | User |
| 2025-10-28 | Strict CSV validation (all-or-nothing) | Data quality over convenience | User |
| 2025-10-28 | Single-use invite codes | Security and tracking | User |
| 2025-10-28 | Impersonation for superuser access | Realistic testing | User |
| 2025-10-28 | Account types: DEMO, REAL only | Simplicity (no TEST type) | User |
| 2025-10-28 | Hybrid approach for demo seeding | Don't break existing system | User |
| 2025-10-28 | Phased UUID strategy | Test deterministic, migrate to random | User |

---

## Document Approval

**Pending Approval From:**
- [ ] Partner review (database schema changes)
- [ ] Security team (invite code system, impersonation)
- [ ] Product team (UX flow, CSV template)

**Next Steps:**
1. Partner reviews schema changes (Section 6)
2. Approve Phase 1 implementation plan
3. Generate initial batch of invite codes
4. Begin development (Week 1)

---

**End of Document**
