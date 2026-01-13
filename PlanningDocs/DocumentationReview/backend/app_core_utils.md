# App Core Utilities Documentation

This document covers: `core/`, `db/`, `telemetry/`, `utils/`, `reports/`

---

## Directory: `core/` - Core Framework & Utilities

### Authentication & Authorization

#### `auth.py`
Provides JWT token generation and validation utilities for user authentication, including password hashing (bcrypt), JWT creation/verification, and token response formatting with guaranteed portfolio_id inclusion. Used by authentication endpoints, dependencies, and Clerk auth.

#### `dependencies.py`
FastAPI dependency injection utilities for user authentication supporting dual auth methods (Bearer token + Cookie fallback for SSE), portfolio ownership validation, and default portfolio resolution. Used by all protected endpoints.

#### `clerk_auth.py`
Clerk-based authentication module providing JWKS verification with TTL caching (1-hour), RS256 JWT validation, Just-In-Time user provisioning, and dual auth support. Used by Phase 2 endpoints.

#### `admin_auth.py`
Admin-specific JWT token generation with shorter expiry (8 hours vs 24 hours), admin token type discrimination. Used by admin dependencies and login endpoints.

#### `admin_dependencies.py`
FastAPI dependencies for admin user authentication and authorization, including dual auth support and role-based access control. Used by admin API endpoints.

### Logging & Configuration

#### `logging.py`
Configures application-wide logging with environment-aware formatters (JSON for production, human-readable for dev), rotating file handlers (10MB max, 5 backups), and module-specific loggers. Used by application startup and all modules.

#### `database.py`
Database connection management providing async engine creation, session factories, dependency injection, and context managers. Used by all database operations.

### Data & Time Handling

#### `datetime_utils.py`
UTC ISO 8601 standardization functions for consistent datetime formatting across API responses with Z suffix. Used by API response serialization.

#### `uuid_strategy.py`
Flexible UUID generation supporting both deterministic (uuid5) and random (uuid4) modes for development/production. Used by user, portfolio, and position creation.

### Data Validation & Error Handling

#### `onboarding_errors.py`
Structured error framework for user onboarding with 30+ error codes, exception classes, and standardized error responses. Used by registration, import, and admin operations.

#### `startup_validation.py`
Validates system prerequisites at startup (8 factor definitions, 18 stress test scenarios) with environment-aware enforcement. Used by main.py startup hook.

#### `db_utils.py`
Database utilities for sync operations in Railway environments, providing psycopg2 connections and SQLAlchemy sync sessions. Used by Railway scripts.

#### `trading_calendar.py`
US stock market trading day determination using hardcoded holiday sets (2024-2026) and market close time tracking. Used by batch processing and snapshot creation.

#### `retry_decorator.py`
Exponential backoff retry decorator supporting async and sync functions with configurable retries and jitter. Used by API calls and database operations.

---

## Directory: `db/` - Database Utilities & Seeding

#### `seed_demo_portfolios.py`
Creates 4 demo portfolios with 63 total positions using June 30, 2025 market prices with deterministic UUIDs. Used by reset_and_seed.py.

#### `seed_factors.py`
Seeds 13 factor definitions into database (Market Beta, IR Beta, 5-factor ridge, 4-factor spreads). Used by seeding scripts.

#### `seed_security_master.py`
Enriches demo portfolio symbols with sector, industry, market cap data for 36 symbols. Used by seeding scripts.

#### `seed_initial_prices.py`
Bootstraps 180 days of real historical price data from YFinance for all demo symbols. Used by seeding scripts.

#### `fetch_historical_data.py`
Shared module for fetching/storing historical market data with batch processing and upsert logic. Used by seed_initial_prices and refresh operations.

#### `verify_schema.py`
Verification script checking database schema and seeded data counts. Used for diagnostics.

#### `snapshot_helpers.py`
Database helpers retrieving latest portfolio snapshots and factor exposures with staleness detection (72-hour threshold). Used by analytics endpoints.

---

## Directory: `telemetry/` - Metrics & Observability

#### `metrics.py`
Lightweight telemetry sink for batch processing metrics forwarding events to logging with structured envelope. Used by batch orchestrator for phase events.

---

## Directory: `utils/` - Utility Modules

#### `json_utils.py`
Custom JSON encoder handling non-standard types: Decimal → float, datetime → ISO string, UUID → string. Used by API serialization.

#### `llm_provider_base.py`
Abstract base class for multi-LLM provider support (Phase 10.3) defining universal interfaces for ID generation, tool formatting, and SSE events. Used by OpenAI provider implementation.

#### `llm_providers/openai_provider.py`
OpenAI-specific LLM provider implementation extending LLMProviderBase with OpenAI ID formats and tool call formatting. Used by OpenAI service.

#### `trading_calendar.py` (in utils/)
pandas_market_calendars-based trading day validator for NYSE using cached schedule lookups. Used by batch scheduling.

---

## Directory: `reports/` - Report Generation

Contains report generation utilities for portfolio analysis outputs. Used by analytics and export functionality.

---

## Summary Table

| Module | Purpose | Primary Consumers |
|--------|---------|-------------------|
| `auth.py` | JWT token management | Auth endpoints, dependencies |
| `dependencies.py` | FastAPI auth injection | All protected endpoints |
| `clerk_auth.py` | Clerk JWKS verification | Clerk-enabled endpoints |
| `logging.py` | App-wide logging setup | Startup, all modules |
| `database.py` | Connection management | All DB operations |
| `datetime_utils.py` | UTC ISO 8601 formatting | API responses |
| `uuid_strategy.py` | Flexible UUID generation | Entity creation |
| `onboarding_errors.py` | Structured error handling | Onboarding workflows |
| `trading_calendar.py` | Holiday calendar | Batch processing |
| `retry_decorator.py` | Exponential backoff | API calls, DB ops |
| `seed_*.py` | Demo data creation | Database seeding |
| `metrics.py` | Telemetry events | Batch orchestrator |
| `json_utils.py` | Custom JSON encoding | Serialization |
