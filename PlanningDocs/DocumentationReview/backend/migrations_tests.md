# Migrations and Tests Documentation

This document describes files in `migrations_core/`, `migrations_ai/`, and `tests/`.

---

## Directory: `migrations_core/versions/` - Core Database Migrations

Total: **47 migration files** covering the full evolution from initial baseline through Phase 3.

### Key Migrations by Phase

#### Initial Setup
| Filename | Purpose |
|----------|---------|
| `2a4b9bc52cd9_initial_baseline_with_all_current_models.py` | Initial baseline - establishes migration chain starting point |
| `9b0768a49ad8_add_multi_portfolio_support.py` | Multi-portfolio support - allows users to have multiple portfolios |

#### Batch Processing & Analytics
| Filename | Purpose |
|----------|---------|
| `714625d883d9_add_batch_jobs_tables_for_section_1_6.py` | Adds batch_jobs table for tracking job executions |
| `40680fc5a516_add_position_correlation_tables.py` | Creates correlation calculation storage tables |
| `b033266c0376_add_position_factor_exposures_table_for_.py` | Creates position-level factor exposure storage |
| `a1b2c3d4e5f6_create_position_market_betas.py` | Creates position-level market beta storage |

#### Position Tagging (October 2025)
| Filename | Purpose |
|----------|---------|
| `bade83d52960_add_position_tags_junction_table.py` | Position tags junction table for M:N relationships |
| `a766488d98ea_remove_strategy_system.py` | Complete removal of legacy strategy system |

#### Target Prices (Phase 8)
| Filename | Purpose |
|----------|---------|
| `35e1888bea0_add_portfolio_target_price_fields.py` | Target price tracking fields |
| `1dafe8c1dd84_add_portfolio_target_prices_table.py` | Dedicated target_prices table |

#### Risk & Analytics
| Filename | Purpose |
|----------|---------|
| `5c561b79e1f3_add_market_risk_scenarios_tables.py` | Market risk scenario storage |
| `7003a3be89fe_add_sector_exposure_and_concentration_.py` | Sector exposure and concentration metrics |
| `b56aa92cde75_create_missing_stress_test_tables.py` | Stress test scenario result tables |
| `d2e3f4g5h6i7_create_position_volatility_table.py` | Position-level volatility storage |

#### Company & Market Data
| Filename | Purpose |
|----------|---------|
| `129542220fba_add_company_profiles_table.py` | Company profiles table (50+ fields) |
| `580582693ef8_add_company_metadata_fields_to_market_.py` | Metadata fields for market data |

#### Admin & AI
| Filename | Purpose |
|----------|---------|
| `o1p2q3r4s5t6_add_admin_user_tables.py` | Admin user tables |
| `p2q3r4s5t6u7_add_user_activity_events.py` | User activity event logging |
| `q3r4s5t6u7v8_add_ai_request_metrics.py` | AI request metrics logging |
| `f8g9h0i1j2k3_add_ai_insights_tables.py` | AI insights storage tables |

#### Performance & Indexes
| Filename | Purpose |
|----------|---------|
| `i6j7k8l9m0n1_add_composite_indexes_for_performance.py` | Composite indexes for query optimization |
| `j7k8l9m0n1o2_add_priority_performance_indexes.py` | Priority indexes on critical paths |

---

## Directory: `migrations_ai/versions/` - AI Database Migrations

Total: **2 migration files** for the AI database with pgvector.

| Filename | Purpose |
|----------|---------|
| `0001_initial_ai_schema.py` | Creates initial AI database schema with pgvector - ai_kb_documents (RAG with HNSW vector index), ai_memories, ai_feedback tables (Dec 19, 2025) |
| `0002_add_admin_annotations.py` | Adds ai_admin_annotations table for admin tuning of AI responses (Dec 22, 2025) |

---

## Directory: `tests/` - Test Suite

Total: **15 test files** across unit, integration, E2E, and batch categories.

### Root Test Files

| Filename | Purpose |
|----------|---------|
| `conftest.py` | Pytest configuration and shared fixtures - provides mock_market_data_services fixture, event loop setup |
| `reproduce_crash.py` | One-time reproduction script for debugging specific errors |

### `tests/batch/` - Batch Processing Tests

| Filename | Purpose |
|----------|---------|
| `test_batch_pragmatic.py` | Fast smoke tests for batch orchestrator v3 API compatibility (<2 min) |
| `test_batch_reality_check.py` | Tests what was actually implemented vs documented |
| `test_pnl_calculator_multiplier.py` | Tests P&L calculation with option contract multiplier (100x) |

### `tests/unit/` - Unit Tests

| Filename | Purpose |
|----------|---------|
| `test_csv_parser_service.py` | Unit tests for CSV validation (35+ error codes) |
| `test_invite_code_service.py` | Unit tests for beta invite code validation |
| `test_market_data_valuation.py` | Unit tests for market data valuation including option multiplier |
| `test_position_import_service.py` | Unit tests for position import logic (signed quantity, option fields, UUID) |
| `test_position_service_realized_pnl.py` | Unit tests for realized P&L calculations on exits |
| `test_uuid_strategy.py` | Unit tests for UUIDStrategy (deterministic vs random) |

### `tests/integration/` - Integration Tests

| Filename | Purpose |
|----------|---------|
| `test_onboarding_api.py` | Integration tests for complete onboarding flow with real database |
| `test_position_import.py` | Integration tests for position import with real database |

### `tests/e2e/` - End-to-End Tests

| Filename | Purpose |
|----------|---------|
| `test_onboarding_flow.py` | E2E tests for complete user journey - registration through analytics |

### `tests/fixtures/` - Test Data

| Filename | Purpose |
|----------|---------|
| `greeks_fixtures.py` | Test fixtures for Greeks calculations (TEST_MARKET_DATA, TEST_POSITIONS) |

---

## Summary Statistics

**Migrations:**
- Core Database: 47 migration files
- AI Database: 2 migration files
- Total: 49 migration files

**Tests:**
- Unit Tests: 6 files
- Integration Tests: 2 files
- E2E Tests: 1 file
- Batch Tests: 3 files
- Fixtures: 1 file
- Config: 1 file
- Total: 15 test files

---

## Migration Evolution Phases

1. **Phase 0-1** (Aug 2025): Initial baseline and multi-portfolio
2. **Phase 2** (Aug-Sep 2025): Batch processing, calculations, snapshots
3. **Phase 3** (Sep-Oct 2025): Analytics, betas, factors, Greeks, target prices
4. **October 2025 Breaking Change**: Strategy system removed, position tagging introduced
5. **Post-October 2025**: Stress testing, company profiles, performance indexes
6. **December 2025**: AI database with pgvector, RAG knowledge base
