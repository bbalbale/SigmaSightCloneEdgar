# WESTON Server Idea — Shared Dev Database on Boston Host

Document status: Proposal for discussion (no scaffolding to implement yet)
Last updated: 2025-09-08

## Objective
- Provide a shared development PostgreSQL instance on the Boston host so all devs see the same data and we accumulate history beyond the provider’s 180‑day limit.
- Keep our current fast Phase 0 workflow (frontend `npm run dev`, backend `uv run python run.py`) and only centralize the database.
- Make migration to Railway in ~2–3 months low‑friction.

## Scope & Assumptions
- Data: Daily OHLCV only for ~750 symbols (current portfolio universe); ticker/universe metadata; splits/dividends as available.
- Security: Private network only (no public 5432), per‑user access, auditable changes via migrations.
- Reliability: Stable power/network on Boston host; nightly backups with periodic restore tests.
- Team: 2 devs now; possibly +1 in 2–3 months.

## Comprehensive Storage Analysis (2025-09-08)

**Complete SigmaSight System for 750 symbols × 180 days: 0.018 GB (18 MB)**

Storage breakdown including all 8 calculation engines and batch processing:
- Market data cache (daily prices): 1.6 MB
- Factor exposures (daily calculations): 2.6 MB  
- Risk metrics & stress testing: 1.0 MB
- Portfolio snapshots (daily): 0.5 MB
- Position Greeks (options): 0.6 MB
- Other calculation data: 1.0 MB
- **Total with database overhead: 18 MB**

**Railway Volume Impact**: Storage requirements make Railway's volume constraints (single volume, no replicas, deployment downtime) operationally irrelevant rather than technical blockers.

**Cost**: $0.003/month on Railway ($0.15/GB × 0.018 GB)

**Growth Projections**: Even 10x growth (0.18 GB) still fits comfortably in Railway's Free/Trial plan (0.5 GB limit).

## Architecture Overview (Dev, Next 2–3 Months)
- Boston host (Ubuntu LTS recommended):
  - PostgreSQL 15 in Docker with a named volume.
  - ETL container(s) scheduled nightly to ingest daily bars and corporate actions.
  - Backup pipeline to S3‑compatible object storage (see “Backups & Retention”).
  - Optional observability sidecars: `postgres_exporter` and `node_exporter`.
- Networking: WireGuard overlay (Tailscale) across the team’s machines and the Boston host.
- Developer laptops (Los Altos, Boston): keep current dev loop; point `DATABASE_URL` to the Boston Postgres over VPN.

## Data Model (Initial)
- `securities(symbol PK, name, exchange, sector, industry, listed_date, delisted_date, updated_at, …)`
- `prices_daily(symbol FK, date, open, high, low, close, volume, provider, adjusted?, vwap?, updated_at, PRIMARY KEY(symbol, date))`
- `splits(symbol FK, date, numerator, denominator, PRIMARY KEY(symbol, date))`
- `dividends(symbol FK, ex_date, amount, currency, PRIMARY KEY(symbol, ex_date))`
- `etl_run(run_id PK, job_name, started_at, finished_at, window_start, window_end, status, rows_loaded, error)`

Partitioning & indexing:
- Range partition `prices_daily` by month on `date` for efficient retention and vacuum.
- Cluster or routinely `VACUUM (ANALYZE)`; primary access via `(symbol, date)`.

## Security & Networking
- Use Tailscale for a private, encrypted mesh; disable public exposure of Postgres entirely.
- Firewall (UFW): allow Postgres only on `tailscale0`; block WAN 5432.
- Postgres auth:
  - Roles: `app_rw` (backend), `app_ro` (read‑only), `etl_writer` (ETL), `dba` (admin). No superuser for apps.
  - `pg_hba.conf` restricted to Tailscale device IPs or tailnet subnet.
- Secrets: store locally in developer keychains or `.env.local` (dev only); rotate quarterly.

## ETL / Batch Ingestion (Daily OHLCV)
- Schedule: one nightly run after provider windows are stable; stagger API calls, respect rate limits.
- Idempotency: upsert keyed by `(symbol, date)`; corporate actions keyed by `(symbol, date)`.
- Provenance: record each job in `etl_run` with counts and error message; retries on transient failures.
- Backfill strategy: rolling collection from “today − 180d” forward ensures accumulation of longer history over time.

## Backups & Retention
- Primary: S3‑compatible object storage via `wal-g` or `pgBackRest` for point‑in‑time recovery (PITR).
  - Retention: e.g., 14 days WAL + weekly full backups; adjust with growth.
  - Restore tests: monthly, into an ephemeral container, with documented steps.
- Secondary: nightly logical dump with `pg_dump` for portability (schema + data) retained 14–30 days.
- Alignment with future Railway:
  - Railway provides built‑in volume backups you can enable per service after migration.
  - To stay portable across providers, favor S3‑compatible storage for Boston backups now (AWS S3, Cloudflare R2, or Backblaze B2). Choose AWS S3 if you want the most “default” target for future platform tooling.

## Observability & Ops
- Metrics: `postgres_exporter` (connections, bloat, WAL, vacuum, slow queries), optional `node_exporter`.
- Alerts (email/Slack): DB down >1m, backup/WAL failure, disk >80%, autovacuum lag, p95 query latency.
- Capacity: NVMe SSD; keep 30–40% free space; UPS recommended.

## Developer Workflow
- Keep Phase 0: frontend and backend run locally with hot reload; only the DB is remote.
- `DATABASE_URL=postgresql://app_rw:<secret>@<tailscale-ip>:5432/sigmasight_dev_shared`.
- Migrations:
  - Alembic remains the single source of truth for schema.
  - Pre‑migration snapshot (logical dump) and quick rollback note in PRs touching schema.
- Optional isolation:
  - Per‑dev scratch DBs for experiments; shared DB holds canonical historical market data.

## Migration Plan to Railway (Target: 2–3 Months)
1. Freeze schema changes for a short window; ensure Alembic is current.
2. Run a clean `pg_dump` from Boston; import into Railway Postgres (v15) and verify.
3. Switch dev `DATABASE_URL` to Railway Postgres; keep Boston as read‑only fallback for a week.
4. After confidence week, decommission Boston writer or repurpose as staging mirror.
5. On Railway: enable built‑in backups; optionally retain the S3 backup job for belt‑and‑suspenders.

## Team Growth (Add 1 Engineer)
- Onboarding steps: add Tailscale device, assign Postgres role (`app_ro` or `app_rw`), share `.env.local` template.
- Access policy: default read‑only; promote to `app_rw` after initial onboarding.

## Alternatives Considered
- Managed dev Postgres now (Railway/Neon/Supabase): lowest ops but earlier cost; easiest if you want zero Boston ops.
- SSH port‑forwarding instead of VPN: simpler setup, but brittle and less secure for daily use; not recommended for shared dev.

## Risks & Mitigations
- Shared DB human error → Backups + PITR + pre‑migration snapshots and restore runbook.
- Home/office host fragility → UPS + auto‑reboot on power recovery; monitor WAN uptime; keep recent dumps locally.
- Provider rate limits → ETL throttling, retries, and partial‑window backfills.

## Open Questions
- Which S3‑compatible provider do we prefer for Boston backups (S3, R2, B2)? If undecided, default to AWS S3 `us-east-1`.
- Exact nightly ETL time window to minimize provider load and avoid partial data.

## Decision Record (Not Yet Approved)
- This document records a feasible approach that preserves developer velocity now and enables a clean move to Railway later. No implementation should start until we agree on the open questions above.

---

## Comparison: Weston Server vs. Dev‑Only Railway

This section contrasts hosting the shared dev DB on the Boston “Weston Server” versus running a dev‑only stack on Railway (backend + Postgres, optional ETL as a Cron Job). Links below point to Railway documentation for the referenced features.

### Quick Decision Checklist

- Lowest ops burden today → choose Dev‑Only Railway.
- Ready for team infrastructure (60% APIs complete) → **both options viable now** ✅
- **Storage requirements**: Complete system needs only **0.018 GB** (18 MB) → **Railway volume constraints irrelevant**
- Want to leverage existing market data system (no ETL rebuild) → **Weston preferred** (proven architecture).
- Adding 1 engineer soon and prefer easy onboarding/access → Dev‑Only Railway (environments, variables) edges out Weston (VPN + roles).
- Want to avoid any DB migration in 2–3 months → start on Dev‑Only Railway now.

### Option A — Weston Server (Boston host)

- Pros
  - Keeps the current fast local dev loop (hot reload for frontend/backend), with only DB traffic remote.
  - **Storage is a non-issue**: 0.018 GB requirement means any solution works.
  - **Leverages existing market data architecture**: Can extend proven multi-provider system (FMP→Polygon→Mock) without rebuilding ETL.
  - Lower immediate platform cost; you pay only for the Boston host and object storage for backups.
  - Full control of Postgres settings, extensions, partitioning for time-series data, and PITR design.
- Cons
  - You own ops: hardening, backups/restore drills, monitoring/alerts, and host maintenance.
  - Single physical location risk (power/ISP/hardware); requires UPS and disciplined backups.
  - Adds a migration step in 2–3 months (dump/restore or brief logical replication) to Railway.
  - Access is limited to VPN members; sharing temporary access with contractors is more overhead.

### Option B — Dev‑Only on Railway

- Pros
  - Managed persistence with Volumes and scheduled Backups from the UI (daily/weekly/monthly). See Volumes and Backups.  
    References: Volumes, Backups.
  - Built‑in environments to isolate dev/staging and keep prod clean.  
    Reference: Environments.
  - Private networking with internal DNS (`<service>.railway.internal`) for service‑to‑service comms (IPv6).  
    Reference: Private Networking.
  - Variables/secrets management at service or shared scope; reference variables for cross‑service values.  
    Reference: Using Variables.
  - Cron Jobs (Scheduled Jobs) for daily ETL with 5‑minute granularity; cloud‑hosted and visible in UI.  
    References: Cron Jobs (reference, guide).
  - Observability: central logs/metrics and notifications; easy rollbacks between deployments.  
    References: Monitoring, Logging, Deployments.
  - Build/deploy from GitHub with zero‑config builders (Railpack/Nixpacks) or your Dockerfile when you’re ready.  
    References: Builds, Build Configuration, Dockerfiles.
- Cons / Caveats
  - Iteration cycle can slow if you place backend in the cloud during active dev; local hot‑reload remains fastest.
  - **Volume constraints irrelevant**: 0.018 GB requirement fits comfortably in Free/Trial plan (0.5 GB).  
    Reference: Volumes.
  - **May require ETL adaptation**: Existing market data system might need modification to work with Railway's cron job constraints.
  - Backup restores are scoped to the same project+environment; manual backup size limits apply.  
    Reference: Backups.
  - Private networking is IPv6‑only and not active during build; apps must bind to `::`.  
    Reference: Private Networking.
  - Cron Jobs require tasks to exit cleanly; overlapping runs are skipped; minimum 5‑minute interval.  
    References: Cron Jobs (reference, guide).

### Which to choose for the next 2–3 months?

**Storage is no longer a deciding factor** — 0.018 GB requirement makes Railway's volume limits irrelevant.

- **Choose Weston** if you want to leverage your existing market data architecture without any modification, prefer full operational control, and are comfortable owning ops on one stable host.
- **Choose Dev‑Only Railway** if you prioritize zero ops burden, easier team onboarding with managed services, and are willing to adapt your ETL system to Railway's cron job constraints (5-minute intervals, clean exits).

## Railway Documentation References

- Private Networking (internal DNS, IPv6)  
  https://docs.railway.com/reference/private-networking  
  https://docs.railway.com/guides/private-networking
- Volumes (persistent storage)  
  https://docs.railway.com/reference/volumes
- Backups (manual/scheduled snapshots for volumes)  
  https://docs.railway.com/reference/backups
- Environments (dev/staging/prod isolation)  
  https://docs.railway.com/reference/environments
- Variables and Secrets  
  https://docs.railway.com/guides/variables
- Cron Jobs (Scheduled Jobs)  
  Reference: https://docs.railway.com/reference/cron-jobs  
  Guide: https://docs.railway.com/guides/cron-jobs
- Monitoring / Logs / Deployments  
  Monitoring: https://docs.railway.com/guides/monitoring  
  Logs: https://docs.railway.com/guides/logs  
  Deployments: https://docs.railway.com/guides/deployments
- Builds and Dockerfiles  
  Builds overview: https://docs.railway.com/guides/builds  
  Build configuration (Railpack/Nixpacks): https://docs.railway.com/guides/build-configuration  
  Dockerfiles: https://docs.railway.com/reference/dockerfiles  

Notes
- If we deploy Postgres as a Railway service, attach a Volume and enable Backups for automated snapshots; for ETL, use a Cron‑scheduled service that terminates after completion.
- Keep Postgres at v15 to match our current design; ensure Alembic migrations remain the single source of truth across both options.
