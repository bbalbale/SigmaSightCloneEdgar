# Dockerization and Deployment Plan v1.4

Document Version: 1.4
Date: 2025-10-04
Status: Simplified deployment plan
Target Platform: Railway.app

## Executive Summary

This revision simplifies our approach to focus on the essential deployment path.

- Phase 1 — Active Development (current): frontend `npm run dev`, backend `uv run python run.py`, local Postgres in Docker.
- Phase 2 — Dev on Railway (Backend + Postgres): deploy Backend + Postgres to Railway (dev env), keep frontend local. Add structured logging and request correlation for remote debugging.

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

When to move to Phase 2:
- Want to validate backend deploy/runtime (CORS/auth/healthchecks) on Railway.
- Want centralized logs/rollbacks for API changes or to share a stable API URL with external testers.
- Need managed Postgres with built-in backups/observability.

## Phase 2 — Dev on Railway (Backend + Postgres)

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

Status: Simplified (v1.4)

Proposed next steps:
1. Create Railway Dev project: Postgres + Backend (Nixpacks) with `/api/v1/health` and env vars.
2. Point local frontend to the Railway backend; configure CORS.
3. Add structured logging + `X-Request-ID` middleware; verify logs in Railway.
4. Decide later whether to move backend to a Dockerfile if needed.

## Version History
- v1.4 (2025-10-04): Simplified to 2 phases - removed Phase 2 (Shared Dev DB) and Phase 4 (Backend Dockerization)
- v1.3 (2025-09-08): Added cost breakdown, migration safety in start command, quick test command, frontend dev clarity, and health check path specification
- v1.2 (2025-09-08): Initial Railway-focused revision
- v1.1: Original Docker-first approach
