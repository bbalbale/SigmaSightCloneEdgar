# Dockerization and Deployment Plan v1.3

Document Version: 1.3
Date: 2025-09-08
Status: Updated with minor enhancements
Target Platform: Railway.app

## Executive Summary

This revision simplifies our approach to match current needs (speed now, low‑friction move to Railway soon).

- Phase 1 — Active Development (current): frontend `npm run dev`, backend `uv run python run.py`, local Postgres in Docker.
- Phase 2 — Shared Dev DB on Railway (Backend Local): keep FE/BE local with hot reload; move only Postgres to Railway Dev. Single-writer ETL via Cron Job; SSL and migration guardrails.
- Phase 3 — Dev on Railway (Backend + Postgres): deploy Backend + Postgres to Railway (dev env), keep frontend local. Add structured logging and request correlation for remote debugging.
- Phase 4 — Backend Dockerization (if/when needed): switch backend from Nixpacks to a Dockerfile when we require tighter control, size, or security.

Key defaults:
- Use Nixpacks for backend on Railway Dev initially. Revisit a Dockerfile later.
- Keep frontend local for fast hot‑reload; point it at the Railway backend URL.
- Implement logging + correlation IDs to make "local FE → Railway BE" development pleasant.

## Cost Breakdown
- **Current Infrastructure**: ~$168/month (FMP $139 + Polygon $29)
- **Railway Platform**: ~$20/month (Postgres $5 + Backend $5 + margin)
- **Total Monthly Cost**: ~$188/month (significantly less than self-hosted infrastructure complexity)

## Phase 1 — Active Development (Local)

Commands (unchanged):
```bash
# Frontend with hot reload
cd frontend && npm run dev

# Backend with auto-reload
cd backend && uv run python run.py

# Database (Dockerized locally)
cd backend && docker-compose up -d postgres
```

When to move to Phase 2
- Need a shared dev DB immediately while keeping full hot reload locally.
- Expect to add another engineer and want consistent data.
- Want built‑in backups/observability without running our own infra.

## Phase 2 — Shared Dev DB on Railway (Backend Local)

Goal: Use a managed, persistent Postgres on Railway Dev while keeping both frontend and backend running locally with hot reload.

### Setup
- Provision Railway Postgres (v15) in the Dev environment; enable scheduled backups. Reference: https://docs.railway.com/reference/backups
- Backend local config
  - Keep using `uv run python run.py` locally.
  - Set `DATABASE_URL` in `backend/.env.local` to the Railway URL (include `?sslmode=require`).
  - SQLAlchemy engine: `create_async_engine(url, pool_pre_ping=True, connect_args={"ssl": "require"}, pool_recycle=1800, pool_timeout=30)`.
  - Alembic: run migrations against the Railway DB: `alembic upgrade head` (use Railway shell once if preferred).
- Quick test before full deployment:
  ```bash
  # Test Railway Postgres with local backend
  railway run uv run python run.py
  ```
- Frontend local config remains unchanged (`npm run dev`).

### ETL (Daily OHLCV)
- Make Railway the single writer: run the ETL as a Cron Job service that upserts by `(symbol, date)` and exits. Reference: https://docs.railway.com/guides/cron-jobs
- Record runs in an `etl_run` table; add retry/backoff to respect provider limits.

### Guardrails
- Migration discipline: designate a migration owner or require migrations only after merge to `main`.
- SSL required (`sslmode=require`), least‑privilege DB roles for app vs. admin.
- Latency: expect higher latency vs. local DB; avoid chatty queries in dev paths.

### When to move to Phase 3
- You want to validate backend deploy/runtime (CORS/auth/healthchecks) on Railway.
- You want centralized logs/rollbacks for API changes or to share a stable API URL with external testers.

## Phase 3 — Dev on Railway (Backend + Postgres)

Goal: Stand up a shared dev backend and database on Railway while keeping the frontend local for speed.

### Services on Railway (Dev Environment)
- Postgres (v15)
  - Prefer managed Postgres on Railway for low ops.
  - Enable scheduled backups. Reference: https://docs.railway.com/reference/backups
- Backend (FastAPI)
  - Builder: Nixpacks (default). Root directory: `backend/`.
  - Start command (Railway): `alembic upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
    - Note: This ensures migrations run safely on each deployment.
    - Local remains `uv run python run.py` for fast dev.
  - Variables: `DATABASE_URL=${{Postgres.DATABASE_URL}}` plus provider keys.
  - Healthcheck: `/api/v1/health` (current implementation) or `/health` (if simplified endpoint added).
- Networking
  - Use Railway private networking for service‑to‑service: https://docs.railway.com/reference/private-networking

### Frontend (Local) → Backend (Railway)
- Set `NEXT_PUBLIC_BACKEND_API_URL=https://<backend>.railway.app` in `frontend/.env.local`.
- For local frontend development pointing to Railway backend:
  ```bash
  # Run frontend locally against Railway backend
  NEXT_PUBLIC_BACKEND_API_URL=https://sigmasight-backend.railway.app npm run dev
  ```
- CORS in FastAPI: allow `http://localhost:3000` (and/or `3005`).
- Auth
  - Token auth (Authorization: Bearer) is simplest for dev.
  - For cookies, set `SameSite=None; Secure` and test over HTTPS.

### Migrations, Seeding, and ETL
- Migrations: Alembic is the only path for schema changes. Automatically run via start command: `alembic upgrade head && python -m uvicorn...`
- Migration Safety: The start command ensures migrations complete before the app starts, preventing version mismatches.
- Seeding: run one‑off scripts using Railway shell.
- Daily OHLCV ETL: add a Cron Job service that runs and exits on schedule. Reference: https://docs.railway.com/guides/cron-jobs

### Logging, Correlation, and Remote Debugging
- Structured logs (JSON)
  - Fields: `ts`, `level`, `request_id`, `method`, `path`, `status`, `duration_ms`, `user_id` (if known).
  - Set `LOG_LEVEL=INFO` in Dev; DEBUG locally.
- Correlation ID (`X-Request-ID`)
  - Frontend: generate a UUID per action/API call; send `X-Request-ID`.
  - Backend: middleware reads/creates `request_id`, logs it, and echoes it in the response header.
  - Result: copy the value from FE console → filter Railway logs to trace a single request end‑to‑end.
- Observability on Railway
  - Logs and filtering: https://docs.railway.com/guides/logs
  - Monitoring and restarts: https://docs.railway.com/guides/monitoring and https://docs.railway.com/guides/deployments

### Workflow
- Frontend targets the Railway backend by default; switch to local backend only for deep debugging.
- Auto‑deploy backend to Dev on merges to `main` to keep FE/BE in sync.
- Use Railway Environments and Variables. References: https://docs.railway.com/reference/environments and https://docs.railway.com/guides/variables

### Open Question — Nixpacks vs Dockerfile
- Default to Nixpacks in Dev for minimal friction.
- Revisit Dockerfile when we need image hardening/size control or custom system deps.
  - Dockerfiles on Railway: https://docs.railway.com/reference/dockerfiles

## Phase 4 — Backend Dockerization (If/When Needed)

Triggers
- Need to pin base image/OS libs, reduce attack surface (alpine/distroless).
- Image size/perf tuning (multi‑stage, wheel caching, no build tools in runtime).
- Security posture (non‑root user, read‑only FS, dropped capabilities) and image scanning.

Tasks
- Author `backend/Dockerfile` (multi‑stage: builder + slim runtime) with non‑root user, `HEALTHCHECK`, `CMD`.
- Switch Railway backend service to Dockerfile builder.
- Validate: health checks, structured logs, migrations, rollbacks.

Rollback
- Use Railway "Rollback to this deployment" to revert to the last good Nixpacks build during transition. Reference: https://docs.railway.com/deploy/deployments

## Migration and Rollback Plan (Dev → Staging/Prod)

1) Migrations
- Alembic is source of truth; no ad‑hoc schema changes.
- Pre‑deploy: ensure `alembic upgrade head` passes in Dev.

2) Data
- Separate Postgres per environment (Dev/Staging/Prod); do not share DBs/volumes.
- If promoting data, `pg_dump`/restore into Staging; validate; then promote to Prod as needed.

3) Deployments and Rollbacks
- Auto‑deploy Dev on merge to `main`. Promote images or re‑build for Staging/Prod.
- Use Railway rollbacks to return to a prior good deployment.

## Security Considerations

- Secrets: keep per‑environment variables in Railway; rotate keys; never commit secrets.
- Network: keep DB private (Railway internal networking); only backend has public endpoints with CORS configured.
- Access: use least‑privilege DB roles for app vs. admin tasks.

## References and Resources

- Railway Private Networking: https://docs.railway.com/reference/private-networking
- Railway Backups: https://docs.railway.com/reference/backups
- Railway Environments: https://docs.railway.com/reference/environments
- Railway Variables/Secrets: https://docs.railway.com/guides/variables
- Railway Cron Jobs: https://docs.railway.com/guides/cron-jobs
- Railway Logs/Monitoring/Deployments: https://docs.railway.com/guides/logs • https://docs.railway.com/guides/monitoring • https://docs.railway.com/guides/deployments
- Dockerfiles on Railway: https://docs.railway.com/reference/dockerfiles
- FastAPI Deployment: https://fastapi.tiangolo.com/deployment/

## Document Status and Next Steps

Status: Updated (v1.3) with minor enhancements

Proposed next steps
1. Create Railway Dev project: Postgres + Backend (Nixpacks) with `/api/v1/health` and env vars.
2. Point local frontend to the Railway backend; configure CORS.
3. Add structured logging + `X-Request-ID` middleware; verify logs in Railway.
4. Decide later whether to move backend to a Dockerfile (Phase 4 triggers).

## Version History
- v1.3 (2025-09-08): Added cost breakdown, migration safety in start command, quick test command, frontend dev clarity, and health check path specification
- v1.2 (2025-09-08): Initial Railway-focused revision
- v1.1: Original Docker-first approach