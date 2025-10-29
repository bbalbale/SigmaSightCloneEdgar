# User & Portfolio Onboarding - Backend Design Document

**Version**: 1.0
**Date**: 2025-10-28
**Status**: Draft - Pending Partner Approval
**Author**: AI Assistant (Claude)

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

**Phase 1: Core Onboarding (MVP)**
- API endpoints for user registration and portfolio creation
- CSV parsing for broker-exported position data
- Invite code security system (config-based single code)
- Full batch processing integration
- Synchronous portfolio creation flow

**Phase 2: Admin & Superuser Tooling** (Separate Implementation)
- Superuser authentication and authorization
- User impersonation for testing
- Admin dashboard endpoints

**Out of Scope:**
- Frontend implementation details (FE team responsibility)
- Tax lot tracking (future feature)
- Multi-account support (future feature)
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
| **Portfolio Limit** | 1 portfolio per user | Existing constraint, simplifies state |
| **Portfolio Init** | CSV required | Ensure data quality, skip empty portfolios for MVP |
| **Position Model** | Single aggregated position per symbol | Simpler than tax lots, matches broker CSVs |
| **Entry Date** | Required in standardized CSV | Necessary for calculations |
| **UUID Strategy** | Hybrid: deterministic for testing → random | Test thoroughly, maintain demos |
| **Invite Codes** | Single master code (config-based) | No database, looks unique to users |
| **Batch Processing** | Synchronous (30-60s timeout) | Simpler for MVP |
| **Superuser Access** | *Phase 2 only* | Not needed for core onboarding |
| **Equity Balance** | Separate API field | Handle leverage correctly |
| **CSV Validation** | All-or-nothing (strict) | Data quality |
| **Demo Seeding** | Keep separate, share utilities | Don't break existing system |
| **Rate Limiting** | None | Trust 50 beta users |
| **Audit Logging** | Application logs only | Sufficient for small scale |
| **Account Types** | None (identify by email) | Unnecessary for MVP |
| **Error Codes** | ~35 essential codes | Balanced detail |

---

## 3. API Endpoint Specifications

### **Phase 1: Core Onboarding - 3 Endpoints**

These are the MVP endpoints for user onboarding and portfolio creation:

1. `POST /api/v1/onboarding/register` - User registration with single invite code
2. `POST /api/v1/onboarding/create-portfolio` - Portfolio creation with CSV (no automatic batch trigger)
3. `POST /api/v1/portfolio/{portfolio_id}/calculate` - User-triggered portfolio calculations (in analytics file)

### **Phase 2: Admin & Superuser - 3 Endpoints** *(Separate Implementation)*

These admin tooling endpoints will be implemented after Phase 1 is working and tested:

3. `POST /api/v1/admin/impersonate` - Start impersonation
4. `POST /api/v1/admin/stop-impersonation` - End impersonation
5. `GET /api/v1/admin/users` - List all users

**Note:** Phase 2 also includes all work from `ADMIN_AUTH_SUPPLEMENT.md` (superuser authentication, JWT modifications, bootstrap script, etc.)

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

#### `POST /api/v1/onboarding/create-portfolio`

**Description:** Create portfolio and import positions from CSV. Does NOT automatically trigger batch processing (use separate calculate endpoint).

**Request:**
```
Content-Type: multipart/form-data

Fields:
- portfolio_name: string (required)
- description: string (optional)
- equity_balance: decimal (required, e.g., 500000.00)
- csv_file: file (required, .csv format)
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/onboarding/create-portfolio \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -F "portfolio_name=My Trading Portfolio" \
  -F "description=Main trading account at Schwab" \
  -F "equity_balance=500000.00" \
  -F "csv_file=@positions.csv"
```

**Response (201 Created):**
```json
{
  "portfolio_id": "a3209353-9ed5-4885-81e8-d4bbc995f96c",
  "name": "My Trading Portfolio",
  "description": "Main trading account at Schwab",
  "equity_balance": "500000.00",
  "positions_imported": 45,
  "created_at": "2025-10-28T10:35:00Z",
  "message": "Portfolio created successfully. Use /api/v1/portfolio/{portfolio_id}/calculate to run calculations."
}
```

**Error Responses:**
- `400` - CSV validation failed (see section 4.2)
- `409` - User already has a portfolio
- `413` - File too large (>10MB)
- `415` - Invalid file type (not .csv)
- `422` - Missing required fields

---

### 3.3 User-Triggered Portfolio Calculations

#### `POST /api/v1/portfolio/{portfolio_id}/calculate`

**File Location:** `app/api/v1/analytics/portfolio.py`

**Description:** Trigger batch calculations for user's portfolio. Users can only trigger calculations for portfolios they own.

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
  "message": "Portfolio calculations started. This will take 30-60 seconds.",
  "poll_url": "/api/v1/portfolio/a3209353-9ed5-4885-81e8-d4bbc995f96c/calculation-status"
}
```

**Error Responses:**
- `403` - Portfolio not owned by user
- `404` - Portfolio not found
- `409` - Calculations already running for this portfolio

**Architecture Notes:**
- This endpoint provides user-facing access to batch processing
- Uses same underlying `batch_orchestrator.run_daily_batch_sequence()` as admin endpoint
- Validates portfolio ownership before triggering calculations
- Returns immediately with batch_run_id for status tracking
- Separate from `POST /admin/batch/run` which is admin-only and can process all portfolios

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

**Description:** List all users (superuser only).

**Query Parameters:**
- `account_type` (optional): `DEMO`, `REAL`, `all` (default: `all`)
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
      "account_type": "REAL",
      "has_portfolio": true,
      "invited_by_code": "SIGMA-A3F9-2K8L",
      "created_at": "2025-10-28T10:30:00Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

---

## 4. Error Conditions Catalog

### 4.1 Registration Errors

| Code | Error | Condition | User Message |
|------|-------|-----------|--------------|
| `ERR_INVITE_001` | Invalid invite code format | Code doesn't match `SIGMA-XXXX-XXXX` pattern | "Invalid invite code format. Expected format: SIGMA-XXXX-XXXX" |
| `ERR_INVITE_002` | Invite code not found | Code doesn't exist in database | "Invalid invite code. Please check and try again." |
| `ERR_INVITE_003` | Invite code expired | `expires_at < now()` | "This invite code expired on {date}. Please request a new code." |
| `ERR_INVITE_004` | Invite code already used | `used_by IS NOT NULL` | "This invite code has already been used." |
| `ERR_INVITE_005` | Invite code inactive | `is_active = FALSE` | "This invite code is no longer active." |
| `ERR_USER_001` | Email already exists | Duplicate email in database | "An account with this email already exists. Please login instead." |
| `ERR_USER_002` | Invalid email format | Email fails regex validation | "Please provide a valid email address." |
| `ERR_USER_003` | Password too weak | Password < 8 chars or missing requirements | "Password must be at least 8 characters with uppercase, lowercase, and number." |
| `ERR_USER_004` | Full name required | `full_name` is empty | "Please provide your full name." |

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
| `ERR_POS_003` | `symbol` | Too long (>50 chars) | "Row {row}: Symbol too long (max 50 characters)" |
| `ERR_POS_004` | `quantity` | Not a number | "Row {row}: Quantity must be a number, got '{value}'" |
| `ERR_POS_005` | `quantity` | Zero | "Row {row}: Quantity cannot be zero" |
| `ERR_POS_006` | `quantity` | Too many decimal places | "Row {row}: Quantity has too many decimal places (max 6)" |
| `ERR_POS_007` | `entry_price` | Not a number | "Row {row}: Entry price must be a number, got '{value}'" |
| `ERR_POS_008` | `entry_price` | Negative or zero | "Row {row}: Entry price must be positive" |
| `ERR_POS_009` | `entry_price` | Unrealistic (>$1M/share) | "Row {row}: Entry price seems unrealistic. Please verify." |
| `ERR_POS_010` | `entry_date` | Missing | "Row {row}: Entry date is required" |
| `ERR_POS_011` | `entry_date` | Invalid format | "Row {row}: Invalid date format. Expected YYYY-MM-DD, got '{value}'" |
| `ERR_POS_012` | `entry_date` | Future date | "Row {row}: Entry date cannot be in the future" |
| `ERR_POS_013` | `entry_date` | Too old (>100 years) | "Row {row}: Entry date seems unrealistic ({date})" |
| `ERR_POS_014` | `investment_class` | Invalid value | "Row {row}: Investment class must be PUBLIC, OPTIONS, or PRIVATE" |
| `ERR_POS_015` | `investment_subtype` | Invalid for class | "Row {row}: Investment subtype '{value}' not valid for {investment_class}" |
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

| Code | Error | Condition | User Message |
|------|-------|-----------|--------------|
| `ERR_BATCH_001` | Market data fetch failed | External API errors | "Unable to fetch market data. Portfolio created but calculations incomplete." |
| `ERR_BATCH_002` | Factor analysis failed | Calculation errors | "Factor analysis incomplete. You can view positions but risk metrics unavailable." |
| `ERR_BATCH_003` | Timeout | Batch took >60s | "Portfolio created but calculations are still running. Please refresh in a few minutes." |
| `ERR_BATCH_004` | Database error during batch | DB write failures | "Portfolio created but unable to save calculation results. Please contact support." |

### 4.6 Admin/Superuser Errors

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

```
app/services/
├── onboarding_service.py        # Main orchestration
├── invite_code_service.py       # Invite code management
├── csv_parser_service.py        # CSV validation & parsing
├── position_import_service.py   # Position creation from CSV
├── impersonation_service.py     # User impersonation
└── batch_trigger_service.py     # Batch processing integration
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
        1. Validate invite code (exists, not used, not expired)
        2. Create user with hashed password
        3. Mark invite code as used
        4. Return user object

        Raises:
            InviteCodeError: Invalid, expired, or used code
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

### 5.3 InviteCodeService

```python
class InviteCodeService:
    async def validate_invite_code(self, code: str) -> InviteCode:
        """
        Validate invite code is usable.

        Checks:
        - Code exists
        - Not expired (expires_at > now)
        - Not used (used_by IS NULL)
        - Active (is_active = TRUE)

        Raises:
            InviteCodeError: Any validation failure
        """

    async def mark_as_used(
        self,
        code: str,
        user_id: UUID
    ) -> InviteCode:
        """Mark invite code as used by user."""

    async def generate_invite_code(
        self,
        expires_at: datetime,
        created_by: UUID
    ) -> InviteCode:
        """
        Generate new invite code (superuser only).

        Format: SIGMA-{4 chars}-{4 chars}
        Example: SIGMA-X7Y2-9M4P

        Character set: A-Z, 0-9 (no confusing chars: O/0, I/1, etc.)
        """
```

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
    tags: List[str] = field(default_factory=list)
    notes: Optional[str] = None
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
        4. Create tags (if any)
        5. Apply sector auto-tagging

        Uses deterministic UUIDs (Phase 1) or random UUIDs (Phase 3).

        Returns:
            ImportResult with success/failure counts
        """
```

### 5.6 ImpersonationService

```python
class ImpersonationService:
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

---

## 6. Database Schema Changes

### 6.1 New Table: `invite_codes`

```sql
CREATE TABLE invite_codes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(50) UNIQUE NOT NULL,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    used_by UUID REFERENCES users(id),
    used_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    note TEXT  -- Internal note about this code
);

CREATE INDEX idx_invite_codes_code ON invite_codes(code);
CREATE INDEX idx_invite_codes_expires_at ON invite_codes(expires_at);
CREATE INDEX idx_invite_codes_used_by ON invite_codes(used_by);
```

### 6.2 Modify `users` Table

```sql
-- Add superuser flag
ALTER TABLE users ADD COLUMN is_superuser BOOLEAN DEFAULT FALSE;

-- Track which invite code was used
ALTER TABLE users ADD COLUMN invited_by_code VARCHAR(50);

-- Account type (DEMO or REAL)
ALTER TABLE users ADD COLUMN account_type VARCHAR(20) DEFAULT 'REAL';

-- Add check constraint
ALTER TABLE users ADD CONSTRAINT check_account_type
    CHECK (account_type IN ('DEMO', 'REAL'));

-- Add indexes
CREATE INDEX idx_users_is_superuser ON users(is_superuser);
CREATE INDEX idx_users_account_type ON users(account_type);
```

### 6.3 Alembic Migration

**File:** `alembic/versions/xxxx_add_onboarding_schema.py`

```python
"""Add onboarding schema

Revision ID: xxxx
Revises: previous_revision
Create Date: 2025-10-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'xxxx'
down_revision = 'previous_revision'
branch_labels = None
depends_on = None


def upgrade():
    # Create invite_codes table
    op.create_table(
        'invite_codes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(50), nullable=False, unique=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('used_at', sa.DateTime(timezone=True)),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('note', sa.Text())
    )

    # Create indexes
    op.create_index('idx_invite_codes_code', 'invite_codes', ['code'])
    op.create_index('idx_invite_codes_expires_at', 'invite_codes', ['expires_at'])
    op.create_index('idx_invite_codes_used_by', 'invite_codes', ['used_by'])

    # Modify users table
    op.add_column('users', sa.Column('is_superuser', sa.Boolean(), server_default='false'))
    op.add_column('users', sa.Column('invited_by_code', sa.String(50)))
    op.add_column('users', sa.Column('account_type', sa.String(20), server_default='REAL'))

    # Add check constraint
    op.create_check_constraint(
        'check_account_type',
        'users',
        "account_type IN ('DEMO', 'REAL')"
    )

    # Create indexes
    op.create_index('idx_users_is_superuser', 'users', ['is_superuser'])
    op.create_index('idx_users_account_type', 'users', ['account_type'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_users_account_type')
    op.drop_index('idx_users_is_superuser')

    # Drop check constraint
    op.drop_constraint('check_account_type', 'users')

    # Remove columns
    op.drop_column('users', 'account_type')
    op.drop_column('users', 'invited_by_code')
    op.drop_column('users', 'is_superuser')

    # Drop invite_codes indexes
    op.drop_index('idx_invite_codes_used_by')
    op.drop_index('idx_invite_codes_expires_at')
    op.drop_index('idx_invite_codes_code')

    # Drop table
    op.drop_table('invite_codes')
```

### 6.4 Manual Script: Seed Invite Codes

**File:** `scripts/database/seed_invite_codes.py`

```python
"""
Manual script to generate invite codes.

Usage:
    uv run python scripts/database/seed_invite_codes.py --count 10 --expires 2026-12-31
"""
import asyncio
import argparse
from datetime import datetime
from app.database import get_async_session
from app.services.invite_code_service import InviteCodeService

async def main(count: int, expires_at: datetime):
    async with get_async_session() as db:
        service = InviteCodeService(db)

        print(f"Generating {count} invite codes (expires: {expires_at})...")

        for i in range(count):
            code = await service.generate_invite_code(
                expires_at=expires_at,
                created_by=None  # System-generated
            )
            print(f"{i+1}. {code.code}")

        await db.commit()
        print(f"\n✅ Generated {count} invite codes")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--expires", type=str, required=True, help="YYYY-MM-DD")
    args = parser.parse_args()

    expires_at = datetime.strptime(args.expires, "%Y-%m-%d")
    asyncio.run(main(args.count, expires_at))
```

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
| **Tags** | No | String | Comma-separated | User-defined tags | `"Tech,Core"` |
| **Notes** | No | Text | Max 1000 chars | Free-text description | `"My largest position"` |
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
- `OTHER` - Other alternatives

### 7.4 Template Content

```csv
Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Tags,Notes,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share
AAPL,100,158.00,2024-01-15,PUBLIC,,"Tech,Core","My largest position",,,,,
MSFT,50,350.00,2024-02-01,PUBLIC,,Tech,,,,,,
VOO,20,631.00,2024-03-15,PUBLIC,,"Index,Core",,,,,,
SPY250919C00460000,200,7.00,2024-01-10,OPTIONS,,Options,,SPY,460.00,2025-09-19,CALL,,
QQQ250815C00420000,150,7.00,2024-01-10,OPTIONS,,Options,,QQQ,420.00,2025-08-15,CALL,,
BX_PRIVATE_EQUITY,1,50000.00,2023-06-01,PRIVATE,PRIVATE_EQUITY,Alternatives,"Blackstone PE fund",,,,,
HOME_EQUITY,1,500000.00,2020-01-01,PRIVATE,REAL_ESTATE,"Real Estate","Primary residence",,,,,
CRYPTO_BTC_ETH,1,75000.00,2022-06-01,PRIVATE,CRYPTOCURRENCY,Crypto,"Mixed BTC/ETH holdings",,,,,
NFLX,-100,490.00,2024-01-25,PUBLIC,,"Short Positions",,,,,,2024-10-15,450.00
```

### 7.5 Parsing Rules

1. **Header Row**: First row must contain column names (case-insensitive matching)
2. **Empty Rows**: Skipped silently
3. **Whitespace**: Trimmed from all values
4. **Quotes**: CSV standard (quotes around values with commas)
5. **Tags**: Split on comma, trimmed, duplicates removed
6. **Auto-Classification**: If `Investment Class` blank, use `determine_investment_class(symbol)`
7. **Options Detection**: If symbol matches OCC format OR has underlying/strike/expiration, classify as OPTIONS
8. **Negative Quantity**: Interpreted as SHORT position

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
Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Tags,Notes,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share
```

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
└─ Redirect to /onboarding/create-portfolio
```

### 8.2 Portfolio Creation Flow

```
Step 1: Create Portfolio Form (/onboarding/create-portfolio)
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

Step 2: Processing
├─ On Submit: POST /api/v1/onboarding/create-portfolio
├─ Show loading spinner: "Creating portfolio and running calculations..."
├─ Progress indicator (if possible):
│   └─ "Importing positions... (1/3)"
│   └─ "Running calculations... (2/3)"
│   └─ "Finalizing... (3/3)"
│
└─ Wait for response (30-60s timeout)

Step 3: Success
├─ Show success message:
│   ├─ "Portfolio created successfully!"
│   ├─ "{N} positions imported"
│   └─ "Calculations complete"
│
├─ Display any warnings:
│   └─ "Note: Greeks unavailable for some positions"
│
└─ Redirect to /portfolio (main dashboard)

Step 4: Error Handling
├─ If CSV validation fails:
│   ├─ Show error list
│   ├─ Highlight problematic rows
│   └─ Allow re-upload
│
├─ If timeout:
│   ├─ "Portfolio created but calculations still running"
│   └─ "Refresh page in a few minutes"
│
└─ If other error:
    ├─ Show user-friendly message
    └─ Allow retry
```

### 8.3 Superuser Impersonation Flow

```
Superuser Dashboard (/admin)
├─ List all users
├─ For each user:
│   ├─ Email, account type, created date, has_portfolio flag
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

### 8.4 UI Components Needed

**New Pages:**
1. `/register` - Registration form
2. `/onboarding/create-portfolio` - Portfolio creation
3. `/admin` - Superuser dashboard (list users)
4. `/admin/invite-codes` - Manage invite codes

**New Components:**
1. `<InviteCodeInput>` - Formatted input for SIGMA-XXXX-XXXX
2. `<CSVUploader>` - Drag-drop file upload with validation
3. `<EquityBalanceInput>` - Currency input with help tooltip
4. `<ImpersonationBanner>` - Persistent banner during impersonation
5. `<CSVValidationResults>` - Display validation errors/warnings

---

## 9. Security Model

### 9.1 Invite Code Security

**Design:**
- Single-use codes only (prevent sharing/abuse)
- Fixed expiration dates (prevent indefinite access)
- Trackable (audit who used which code)
- Manual generation only (no self-service)

**Code Format:**
- Pattern: `SIGMA-XXXX-XXXX`
- Character set: `ABCDEFGHJKLMNPQRSTUVWXYZ23456789` (30 chars)
  - Excludes: O/0, I/1 (confusing)
  - Uppercase only for consistency
- Total combinations: 30^8 = 656 billion possible codes

**Validation Checks:**
1. Code exists in database
2. Not expired (`expires_at > now()`)
3. Not used (`used_by IS NULL`)
4. Active (`is_active = TRUE`)

**Rate Limiting:**
- Max 5 failed invite code attempts per IP per hour
- After 5 failures, require CAPTCHA

### 9.2 Superuser Access Control

**Identification:**
- Database flag: `users.is_superuser = TRUE`
- Set manually via SQL or admin script
- Cannot be self-granted

**Permissions:**
- All regular user endpoints
- All `/api/v1/admin/*` endpoints
- Can impersonate any user
- Can generate invite codes
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
- Log all impersonation events
- Log all admin endpoint access
- Include: who, when, what, target user

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

### 9.5 Rate Limiting

**Registration:**
- Max 3 accounts per IP per day
- Max 10 registration attempts per IP per hour

**CSV Upload:**
- Max 5 uploads per user per hour
- Max 10MB file size

**API Calls (General):**
- 100 requests per minute per user
- 500 requests per hour per user

**Admin Endpoints:**
- No rate limiting for superusers (trusted)

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
- `POST /api/v1/onboarding/create-portfolio` (no automatic batch trigger)
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

---

### **Phase 2: Admin & Superuser Tooling** (~1 week) *Implement after Phase 1 is working and tested*

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

### Phase 3: Production Hardening (Optional - Future)

**Goals:**
- Security improvements
- UUID migration
- Rate limiting
- Monitoring

**Tasks:**
1. **UUID Migration:**
   - Add `uuid_generation_strategy` config
   - Implement hybrid approach:
     ```python
     if account_type == 'DEMO':
         uuid = generate_deterministic_uuid(email)
     else:
         uuid = uuid4()  # Random for real users
     ```
   - Test thoroughly in staging

2. **Rate Limiting:**
   - Implement per-endpoint limits
   - Add Redis for distributed rate limiting (optional)
   - Add CAPTCHA for invite code validation

3. **Monitoring:**
   - Add metrics for:
     - Registration attempts
     - CSV upload success/failure rates
     - Batch processing duration
     - Impersonation events
   - Set up alerts for anomalies

4. **Security Audit:**
   - Review all endpoints for auth bypass
   - Test user isolation
   - Verify no SQL injection vectors
   - Check file upload security

5. **Documentation:**
   - API documentation (Swagger/ReDoc)
   - User guide for CSV import
   - Admin guide for invite codes

**Success Criteria:**
- ✅ All new users get random UUIDs
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

### 12.1 Unit Tests

**Services:**
- `test_invite_code_service.py`
  - Validate invite code (all edge cases)
  - Generate invite code (format, uniqueness)
  - Mark as used

- `test_csv_parser_service.py`
  - Valid CSV parsing
  - Invalid CSV detection (all error codes)
  - Edge cases (empty rows, special characters)

- `test_position_import_service.py`
  - Position creation
  - Investment class auto-detection
  - Tag handling

**Models:**
- `test_invite_code_model.py`
  - Expiration logic
  - Uniqueness constraints

### 12.2 Integration Tests

**Registration Flow:**
```python
async def test_registration_with_valid_invite_code():
    # Create invite code
    code = await create_invite_code(expires_at=future_date)

    # Register user
    response = await client.post("/api/v1/onboarding/register", json={
        "email": "test@example.com",
        "password": "SecurePass123!",
        "full_name": "Test User",
        "invite_code": code.code
    })

    assert response.status_code == 201
    assert code.used_by is not None
```

**Portfolio Creation:**
```python
async def test_create_portfolio_with_csv():
    # Login
    token = await login_user()

    # Upload CSV
    with open("test_positions.csv", "rb") as f:
        response = await client.post(
            "/api/v1/onboarding/create-portfolio",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "portfolio_name": "Test Portfolio",
                "equity_balance": "500000.00"
            },
            files={"csv_file": f}
        )

    assert response.status_code == 201
    assert response.json()["positions_imported"] > 0
```

### 12.3 End-to-End Tests

**Full Onboarding Flow:**
1. Generate invite code
2. Register user
3. Login
4. Upload CSV
5. Create portfolio
6. Verify batch processing completed
7. Verify positions in database
8. Login to frontend and view portfolio

**Impersonation Flow:**
1. Create test user
2. Superuser impersonates
3. Verify can access user's portfolio
4. Stop impersonation
5. Verify back to original user

### 12.4 CSV Test Files

**Create test CSVs:**
- `valid_basic.csv` - Minimal valid CSV (4 columns, 10 rows)
- `valid_full.csv` - All 14 columns, mixed asset types (50 rows)
- `invalid_dates.csv` - Bad date formats
- `invalid_numbers.csv` - Non-numeric quantities/prices
- `missing_required.csv` - Missing symbols/dates
- `duplicate_positions.csv` - Same symbol+date twice
- `options_positions.csv` - Options-specific fields
- `private_positions.csv` - Private assets
- `schwab_export.csv` - Real Schwab CSV format
- `fidelity_export.csv` - Real Fidelity CSV format
- `vanguard_export.csv` - Real Vanguard CSV format

---

## Appendix A: Sample CSV Files

### A.1 Schwab Positions CSV

```csv
Symbol,Description,Qty (Quantity),Price,Price Chng $,Price Chng %,Mkt Val (Market Value),Day Chng $,Day Chng %,Cost Basis,Gain $,Gain %,% of Acct,Security Type
CMF,ISHARES CALIFORNIA MUNI BOND ETF,54,$57.6063,-$0.0137,-0.02%,$3110.74,-$0.74,-0.02%,$2984.33,$126.41,4.24%,1.92%,ETFs
AAPL,APPLE INC,100,$225.00,$1.50,0.67%,$22500.00,$150.00,0.67%,$15800.00,$6700.00,42.41%,13.88%,Stocks
Cash & Cash Investments,--,--,--,--,--,$16073.35,$0.00,0%,--,--,--,9.92%,Cash
```

**Mapping to our template:**
- Symbol → Symbol
- Qty → Quantity
- Cost Basis / Qty → Entry Price Per Share
- Use upload date as Entry Date (missing in Schwab export)

### A.2 Fidelity Positions CSV

```csv
Account Number,Account Name,Symbol,Description,Quantity,Last Price,Current Value,Total Gain/Loss Dollar,Total Gain/Loss Percent,Cost Basis Total,Average Cost Basis,Type
Z43122858,Trust,AAPL,APPLE INC,100,$225.00,$22500.00,+$6700.00,+42.41%,$15800.00,$158.00,Cash
Z43122858,Trust,SPAXX**,HELD IN MONEY MARKET,,,,$31780.61,,,,,Cash
```

**Mapping to our template:**
- Symbol → Symbol
- Quantity → Quantity
- Average Cost Basis → Entry Price Per Share
- Use upload date as Entry Date

### A.3 Vanguard Positions CSV

```csv
Account Number,Investment Name,Symbol,Shares,Share Price,Total Value
20796525,VANGUARD TARGET RETIREMENT 2030,VTHRX,7711.87,43.96,339013.81
20796525,VANGUARD FEDERAL MONEY MARKET,VMFXX,8271.36,1,8271.36
```

**Mapping to our template:**
- Symbol → Symbol
- Shares → Quantity
- Share Price → Entry Price Per Share (current price, not cost basis!)
- Use upload date as Entry Date

**⚠️ Limitation:** Vanguard positions CSV doesn't include cost basis, so users must calculate Entry Price themselves or use transaction history.

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
