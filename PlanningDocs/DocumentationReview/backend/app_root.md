# App Root Files Documentation

This document describes all files in the `backend/app/` root directory.

---

## Core Application Files

### `__init__.py`
Empty package initializer that marks `app/` as a Python package. Used by Python's import system for package recognition.

### `main.py`
FastAPI application entry point that creates the app instance, configures CORS, registers routes, and defines health endpoints. Used by `run.py` and `uvicorn` to start the server; imported by tests for test client creation.

### `config.py`
Pydantic settings class defining all application configuration (database URLs, API keys, feature flags, timeouts). Used by nearly every module in the application (~50+ importers) including services, batch processing, API endpoints, and agent components.

### `database.py`
SQLAlchemy async engine and session management for dual database architecture (Core + AI databases). Used by all database operations throughout the application (~40+ importers) including models, services, batch processing, and API endpoints.

---

## File Details

### `main.py` (8.5KB)
- Creates FastAPI app with title "SigmaSight Backend API"
- Configures CORS middleware with allowed origins from settings
- Registers API router at `/api` prefix
- Defines health endpoints: `/`, `/health`, `/health/live`, `/health/ready`, `/health/status`, `/health/prerequisites`
- Startup events: system validation, V2 cache initialization, KB document seeding
- Custom exception handler for OnboardingException

**Key Dependencies:**
- `app.config.settings` - Application configuration
- `app.api.v1.router.api_router` - Main API router
- `app.core.logging` - Logging setup
- `app.core.onboarding_errors` - Custom exceptions
- `app.database` - Database sessions

**Used By:**
- `run.py` - Development server
- `railway.toml` - Production deployment
- `tests/` - Test client creation

### `config.py` (15.6KB)
Settings organized into sections:
- **Application**: APP_NAME, VERSION, DEBUG, ENVIRONMENT, LOG_LEVEL
- **Database**: DATABASE_URL, AI_DATABASE_URL (dual database architecture)
- **Market Data**: POLYGON_API_KEY, FMP_API_KEY, FRED_API_KEY, YFinance settings
- **OpenAI Agent**: OPENAI_API_KEY, MODEL_DEFAULT, smart routing, SSE streaming
- **RAG**: RAG_ENABLED, RAG_DOC_LIMIT, RAG_MAX_CHARS
- **Anthropic**: ANTHROPIC_API_KEY, ANTHROPIC_MODEL (analytical reasoning layer)
- **Authentication**: SECRET_KEY, JWT settings, Clerk integration
- **CORS**: ALLOWED_ORIGINS list
- **Batch Processing**: V2 architecture settings, timeouts, concurrency limits

**Used By:**
- Virtually every module (50+ files) - configuration is the central source of truth

### `database.py` (8.2KB)
Dual database architecture implementation:
- **Core Engine** (`core_engine`): High-throughput for portfolios, positions, market data, chat
- **AI Engine** (`ai_engine`): Lower throughput for RAG, memories, feedback with pgvector
- **Session Factories**: `CoreSessionLocal`, `AISessionLocal`
- **FastAPI Dependencies**: `get_db()`, `get_ai_db()`
- **Context Managers**: `get_core_session()`, `get_ai_session()`
- **Backward Compatibility**: `engine`, `AsyncSessionLocal`, `get_async_session()`
- **Lifecycle**: `init_db()`, `close_db()`, connection test functions

**Used By:**
- All models via Base class
- All services for database operations
- All API endpoints via dependency injection
- Batch processing for data operations
- Scripts for standalone database access

---

## Subdirectories (documented separately)

| Directory | Purpose | Doc File |
|-----------|---------|----------|
| `agent/` | AI agent system (OpenAI Responses API) | `app_agent.md` |
| `api/` | REST API endpoints (v1) | `app_api.md` |
| `auth/` | Authentication utilities | `app_auth.md` |
| `batch/` | Batch processing orchestration | `app_batch.md` |
| `cache/` | Caching layer (V2 symbol cache) | `app_cache.md` |
| `calculations/` | Financial calculation engines | `app_calculations.md` |
| `clients/` | External API clients | `app_clients.md` |
| `config/` | Additional configuration | `app_config_dir.md` |
| `constants/` | Application constants | `app_constants.md` |
| `core/` | Core utilities (auth, logging, errors) | `app_core.md` |
| `db/` | Database utilities and seeding | `app_db.md` |
| `models/` | SQLAlchemy ORM models | `app_models.md` |
| `reports/` | Report generation | `app_reports.md` |
| `schemas/` | Pydantic request/response schemas | `app_schemas.md` |
| `services/` | Business logic layer | `app_services.md` |
| `telemetry/` | Metrics and telemetry | `app_telemetry.md` |
| `utils/` | Utility functions | `app_utils.md` |
