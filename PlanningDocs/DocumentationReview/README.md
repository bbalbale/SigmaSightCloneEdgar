# SigmaSight Codebase Documentation Review

This directory contains comprehensive documentation of every file in the SigmaSight codebase, organized by directory.

**Generated**: January 13, 2026

---

## Backend Documentation (`backend/`)

| File | Coverage | Files Documented |
|------|----------|------------------|
| [backend_root.md](backend/backend_root.md) | Root configuration files | 30+ files (pyproject.toml, alembic.ini, docker-compose.yml, etc.) |
| [app_root.md](backend/app_root.md) | Core FastAPI application | 3 files (main.py, config.py, database.py) |
| [app_agent.md](backend/app_agent.md) | AI agent system | 16+ files across 7 subdirectories |
| [app_api.md](backend/app_api.md) | REST API endpoints | 59+ endpoints across 9 categories |
| [app_batch.md](backend/app_batch.md) | Batch processing framework | Orchestrator + 4 calculation phases |
| [app_calculations.md](backend/app_calculations.md) | Financial calculation engines | 18+ calculation modules |
| [app_smaller_dirs.md](backend/app_smaller_dirs.md) | auth/, cache/, clients/, config/, constants/ | 15+ utility files |
| [app_core_utils.md](backend/app_core_utils.md) | core/, db/, telemetry/, utils/, reports/ | 20+ core utility files |
| [app_models.md](backend/app_models.md) | SQLAlchemy ORM models | 19 model files, 45+ models |
| [app_schemas_services.md](backend/app_schemas_services.md) | Pydantic schemas & services | 19 schemas + 45+ services |
| [scripts.md](backend/scripts.md) | Utility scripts | 80+ scripts across 8 directories |
| [migrations_tests.md](backend/migrations_tests.md) | Database migrations & tests | 47 core + 2 AI migrations, 15 tests |
| [other_folders.md](backend/other_folders.md) | Documentation & data folders | _docs/, _archive/, _guides/, analysis/, data/ |

---

## Frontend Documentation (`frontend/`)

| File | Coverage | Files Documented |
|------|----------|------------------|
| [frontend_root.md](frontend/frontend_root.md) | Root configuration files | 19 files (package.json, next.config.js, etc.) |
| [app_pages.md](frontend/app_pages.md) | Next.js App Router pages | 28 page files across 12 routes |
| [components.md](frontend/components.md) | React components | 163 components across 22 directories |
| [containers.md](frontend/containers.md) | Page containers | 11 container components |
| [hooks.md](frontend/hooks.md) | Custom React hooks | 35 hooks for data fetching & state |
| [services.md](frontend/services.md) | API service layer | 28 service files |
| [stores_lib_types.md](frontend/stores_lib_types.md) | Zustand stores, lib, types | 6 stores + 21 lib files + 5 type files |
| [other_folders.md](frontend/other_folders.md) | Docs, tests, scripts | _docs/, tests/, scripts/, public/ |

---

## Quick Reference

### By Technology
- **FastAPI Backend**: [app_root.md](backend/app_root.md), [app_api.md](backend/app_api.md)
- **SQLAlchemy Models**: [app_models.md](backend/app_models.md)
- **Next.js Pages**: [app_pages.md](frontend/app_pages.md)
- **React Components**: [components.md](frontend/components.md)
- **Zustand State**: [stores_lib_types.md](frontend/stores_lib_types.md)

### By Feature
- **AI/Chat System**: [app_agent.md](backend/app_agent.md), [components.md](frontend/components.md) (ai-chat/, copilot/)
- **Batch Processing**: [app_batch.md](backend/app_batch.md), [app_calculations.md](backend/app_calculations.md)
- **Risk Analytics**: [app_calculations.md](backend/app_calculations.md), [components.md](frontend/components.md) (risk/, risk-metrics/)
- **Authentication**: [app_smaller_dirs.md](backend/app_smaller_dirs.md), [services.md](frontend/services.md)

### By Task
- **Adding API Endpoint**: [app_api.md](backend/app_api.md) → [app_schemas_services.md](backend/app_schemas_services.md)
- **Adding UI Component**: [components.md](frontend/components.md) → [containers.md](frontend/containers.md)
- **Database Changes**: [app_models.md](backend/app_models.md) → [migrations_tests.md](backend/migrations_tests.md)
- **Running Scripts**: [scripts.md](backend/scripts.md)

---

## Summary Statistics

| Category | Count |
|----------|-------|
| **Backend Files Documented** | ~400+ |
| **Frontend Files Documented** | ~350+ |
| **Total Documentation Files** | 21 |
| **Backend Directories Covered** | 25+ |
| **Frontend Directories Covered** | 30+ |

---

## Document Format

Each documentation file contains tables with:
- **File**: The filename
- **Purpose**: One sentence explaining what the file does
- **Usage**: One sentence explaining where/how the file is used (traced from actual imports)
