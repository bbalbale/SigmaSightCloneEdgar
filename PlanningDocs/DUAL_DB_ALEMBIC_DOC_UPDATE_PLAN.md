# Dual Database Alembic Documentation Fix Plan

**Purpose**: Align all developer-facing docs with the dual-database migration setup (Core + AI) so contributors always run and create migrations for both chains.

**Scope**: Documentation only. No code or config changes in this plan. Applies to root docs and backend guides listed below.

**Updated**: 2025-12-22

---

## Current Gaps

- **Root CLAUDE.md** shows single `uv run alembic upgrade head` in Quick Start commands and references old `alembic/` folder in project structure.
- Root quick start only runs a single migration and still references `alembic/` (see `README.md` quick start and project structure).
- Backend quick start and migration guidance only show `uv run alembic upgrade head` for one DB (`backend/README.md`).
- Backend AI agent instructions still list a single migration in Quick Start (`backend/CLAUDE.md`).
- Setup guides point to a non-existent `scripts/setup_dev_database_alembic.py` and single-DB flow (`backend/_guides/README.md`, `backend/_guides/WINDOWS_SETUP_GUIDE.md`, `backend/_guides/MAC_INSTALL_GUIDE.md`).
- Daily workflow and Railway data download guides instruct single-chain migrations (`backend/_guides/BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md`, `backend/_docs/guides/RAILWAY_DATA_DOWNLOAD_GUIDE.md`).
- Railway deploy guidance needs verification: `railway.toml` startCommand may already include dual migrations (per CLEAN_REBUILD_IMPLEMENTATION.md Phase 8.8), but docs should confirm this.

---

## Canonical Migration Commands (to propagate)

### Running Migrations

```bash
# Core DB only
uv run alembic -c alembic.ini upgrade head

# AI DB only
uv run alembic -c alembic_ai.ini upgrade head

# Both (local setup - RECOMMENDED)
uv run alembic -c alembic.ini upgrade head && uv run alembic -c alembic_ai.ini upgrade head
```

### Creating New Migrations

```bash
# Core DB (portfolios, positions, market data, chat, etc.)
uv run alembic -c alembic.ini revision --autogenerate -m "<msg>"

# AI DB (ai_kb_documents, ai_memories, ai_feedback)
uv run alembic -c alembic_ai.ini revision --autogenerate -m "<msg>"
```

### Environment Variables Required

| Variable | Database | Required For |
|----------|----------|--------------|
| `DATABASE_URL` | Core (gondola) | All features |
| `AI_DATABASE_URL` | AI (metro) | AI chat, RAG, memories, feedback |

**Fallback Behavior (Local Dev Only)**: If `AI_DATABASE_URL` is not set, code falls back to `DATABASE_URL`. This is a **local development convenience only** - production must always have both URLs configured separately.

---

## Update Targets & Planned Edits

### 1) Root CLAUDE.md (NEW)
- Update "Common Development Commands" section: replace single migration with dual commands.
- Update "High-Level Architecture" project structure: change `alembic/` to `migrations_core/` and add `migrations_ai/`.
- Update "Environment Variables" section to show both `DATABASE_URL` and `AI_DATABASE_URL`.

### 2) Root README
- Quick start: require both DB URLs; add dual upgrade command; update project structure to `migrations_core/` and `migrations_ai/` instead of `alembic/`.
- Mention AI DB as prerequisite for AI features/RAG.

### 3) Backend README
- Quick start + "Updating environment" sections: show both upgrade commands.
- Note that seeding/fixtures target core DB; AI DB has no seed step yet.

### 4) Backend CLAUDE.md
- Quick Start commands: replace single migration with dual chain commands.
- Add reminder to create revisions per DB (`-c alembic_ai.ini`).
- Keep dual-session guidance; link migration commands to that section.

### 5) Backend Guides (`_guides/README.md`, `WINDOWS_SETUP_GUIDE.md`, `MAC_INSTALL_GUIDE.md`)
- Remove/replace references to missing `scripts/setup_dev_database_alembic.py` with explicit dual Alembic commands.
- Update step-by-step setup to include both migrations and AI DB URL.

### 6) Daily Workflow Guide (`_guides/BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md`)
- Daily post-pull checklist: run both upgrade commands; optionally add a combined snippet.

### 7) Railway Data Download Guide (`_docs/guides/RAILWAY_DATA_DOWNLOAD_GUIDE.md`)
- Schema creation step: require both migrations before imports/pg_dump restore.
- Clarify which DB the import targets (core) and that AI DB migrations still must run.

### 8) Railway Deploy Note (`backend/railway.toml`)
- **First**: Verify current `startCommand` - per CLEAN_REBUILD_IMPLEMENTATION.md it should already be:
  ```toml
  startCommand = "alembic -c alembic.ini upgrade head && alembic -c alembic_ai.ini upgrade head && uvicorn ..."
  ```
- If correct, update comment block to document this behavior.
- If missing, add dual migration to startCommand.

---

## Acceptance Criteria

- [x] Every user-facing doc that instructs running migrations shows both Core and AI commands (or a combined one-liner).
- [x] Project structure sections reference `migrations_core/` and `migrations_ai/` (not `alembic/`).
- [x] All setup guides list both `DATABASE_URL` and `AI_DATABASE_URL` as required inputs.
- [x] No references remain to the missing `scripts/setup_dev_database_alembic.py` or single-DB-only migration steps.
- [x] Railway deployment guidance clearly states when/how both migration chains run.
- [x] Fallback behavior documented as local-dev-only convenience.

---

## Execution Checklist

- [x] Update root CLAUDE.md Quick Start, project structure, and env vars.
- [x] Update root README quick start + structure.
- [x] Update backend README migration sections.
- [x] Update backend CLAUDE.md Quick Start and migration instructions.
- [x] Update backend guides (README, Windows, Mac) to dual commands.
- [x] Update BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md to dual commands.
- [x] Update RAILWAY_DATA_DOWNLOAD_GUIDE.md migration step to dual commands.
- [x] Verify railway.toml startCommand; update comment block accordingly.
- [x] Self-review for lingering single-DB references and the missing setup script callouts.

**Status**: COMPLETED on 2025-12-22

---

## Optional Enhancement

Consider adding a convenience script for developers who frequently run both migrations:

```bash
# scripts/migrate_all.sh (or migrate_all.bat for Windows)
#!/bin/bash
uv run alembic -c alembic.ini upgrade head && uv run alembic -c alembic_ai.ini upgrade head
```

This is **optional** - the dual command one-liner is sufficient, but a script reduces typos.
