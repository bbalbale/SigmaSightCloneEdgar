# Other Folders Documentation

This document covers: `_docs/`, `_archive/`, `_guides/`, `analysis/`, `data/`, `test_portfolios/`

---

## Directory: `_docs/` - Main Documentation

### Root-Level Documentation Files

| File | Purpose |
|------|---------|
| `AGENT_HANDOFF_ARCHITECTURE_V2.md` | AI agent handoff systems and conversation flows |
| `ALEMBIC_MULTIPLE_HEADS_INVESTIGATION.md` | Resolution guide for Alembic multiple migration heads |
| `CODE_REVIEW_*.md` | Various code review findings (7 files) |
| `MULTI_PORTFOLIO_API_REFERENCE.md` | API reference for multi-portfolio operations |
| `ONBOARDING_GUIDE.md` | Comprehensive onboarding guide |
| `SESSION_SUMMARY_*.md` | Session summaries from investigations |

### `_docs/reference/`

| File | Purpose |
|------|---------|
| `API_REFERENCE_V1.5.0.md` | Complete API endpoint reference (59 endpoints, most current) |

### `_docs/requirements/`

| File | Purpose |
|------|---------|
| `USER_PORTFOLIO_ONBOARDING_DESIGN.md` | Comprehensive onboarding design (106KB) |
| `PHASE_8.1_API_SCHEMA_INVENTORY.md` | API schemas for Phase 8.1 |
| `PHASE_9_RAILWAY_COMPANY_PROFILE_INTEGRATION.md` | Railway company profile integration |
| `SAMPLE_CSV_FORMAT.md` | Required CSV format for uploads |
| `STRESS_TESTING_BEST_PRACTICES_REVIEW.md` | Stress testing best practices |
| Additional files... | 5 more requirement specs |

### `_docs/guides/`

| File | Purpose |
|------|---------|
| `RAILWAY_DATA_DOWNLOAD_GUIDE.md` | Step-by-step guide for Railway data download |

### `_docs/generated/`

| File | Purpose |
|------|---------|
| `Calculation_Engine_White_Paper.md` | Auto-generated calculation engine white paper |

---

## Directory: `_guides/` - Setup & Development Guides

| File | Purpose |
|------|---------|
| `BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md` | Comprehensive daily workflow guide (29KB) |
| `BACKEND_INITIAL_COMPLETE_WORKFLOW_GUIDE.md` | Initial setup guide (13KB) |
| `MAC_INSTALL_GUIDE.md` | macOS installation guide (30KB) |
| `WINDOWS_SETUP_GUIDE.md` | Windows installation guide (11KB) |
| `README.md` | Overview and index for guides |

---

## Directory: `_archive/` - Archived Files

Contains archived files no longer actively used but preserved for reference. Last updated 2025-11-28.

### Major Subdirectories

| Directory | Purpose |
|-----------|---------|
| `todos/` | Historical TODO files (TODO1-5.md) from phases 1-3 |
| `debug/` | One-time debug scripts (check_*.py, test_*.py) |
| `code-reviews/` | Code review documentation and findings |
| `guides/` | Historical guides (superseded by current) |
| `incidents/` | Incident reports and fix documentation |
| `planning/` | Historical planning documents (39+ files) |
| `deprecated_services/` | Superseded service files |
| `scripts/` | Old diagnostic scripts |
| `legacy_scripts_for_reference_only/` | Old implementations for reference |
| `migration_2025_10_29/` | October 29 PostgreSQL migration reference |
| `migration-scripts/` | Position→tagging migration scripts |
| `tagging-project/` | October 2025 tagging project planning |
| `config/` | Historical configuration documentation |
| `data-providers/` | Data provider research (Polygon, etc.) |

---

## Directory: `analysis/` - Data Analysis Files

| File | Purpose |
|------|---------|
| `dgs10_ir_results.json` | Information Ratio results for DGS10 (10-year Treasury) |
| `ir_method_comparison.txt` | Comparison of IR calculation methods |
| `tlt_ir_results.json` | Information Ratio results for TLT (Treasury bond ETF) |

---

## Directory: `data/` - Sample Data Files

| File | Purpose |
|------|---------|
| `target_prices_import.csv` | Sample CSV for bulk target price imports |

---

## Directory: `test_portfolios/` - Test & Demo Portfolio CSVs

### Portfolio Files

| File | Description | Purpose |
|------|-------------|---------|
| `Conservative-Retiree-Portfolio.csv` | INTENTIONAL ERROR TESTING - 11 validation errors | Validation testing |
| `Tech-Focused-Professional.csv` | ~$2.01M tech sector concentration | Growth/Tech strategy testing |
| `Contrarian-Value-Trader.csv` | Long/short with 1.5x leverage, $2.02M equity | Leveraged strategy testing |
| `Diversified-Growth-Investor.csv` | 43% NVDA concentration + 52 holdings | Concentration testing |
| `Test-Schwab-Robo-Advisor.csv` | Robo-advisor style portfolio | Robo-advisor testing |
| `Universe_Test_*.csv` | Symbol universe validation files (Alpha, Beta, Gamma) | Universe validation |

### Python Scripts

| File | Purpose |
|------|---------|
| `create_test_portfolios.py` | Programmatically create test portfolio files |
| `check_symbol_universe.py` | Verify symbol universe across portfolios |
| `README.md` | Comprehensive documentation (7.3KB) |

### Key Portfolio Specifications

- **Tech-Focused-Professional**: $2,013,000 equity (no leverage)
- **Contrarian-Value-Trader**: $2,019,000 equity (1.5x leverage, $3.03M gross)
- **Diversified-Growth-Investor**: $5,800,000 equity (43% NVDA concentration)

---

## Quick Navigation Guide

| Need | Location |
|------|----------|
| Setting Up Development | `_guides/README.md` → OS-specific guide |
| API Implementation | `_docs/reference/API_REFERENCE_V1.5.0.md` |
| Product Requirements | `_docs/requirements/` directory |
| Railway Deployment | `_docs/guides/RAILWAY_DATA_DOWNLOAD_GUIDE.md` |
| Portfolio Testing | `test_portfolios/` with README.md |
| Historical Context | `_archive/README.md` |
