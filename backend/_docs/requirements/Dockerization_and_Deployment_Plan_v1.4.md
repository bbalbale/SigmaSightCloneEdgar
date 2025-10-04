# Dockerization and Deployment Plan v1.4

Document Version: 1.4
Date: 2025-10-04
Status: Focused on Frontend Dockerization
Target Platform: Railway.app (Future)

## Executive Summary

This revision focuses on immediate frontend containerization for consistent development environments, with a clear path to Railway deployment.

- Phase 1 — Active Development (current): Frontend `npm run dev`, Backend `uv run python run.py`, local Postgres in Docker
- Phase 2 — Frontend Dockerization: Containerize Next.js frontend for consistent dev/prod environments
- Phase 3 — Backend Dockerization (future): Backend containerization when needed for Railway deployment

Key priorities:
- **Immediate**: Dockerize frontend for development consistency and deployment readiness
- **Future**: Backend remains local with `uv run python run.py` until Railway deployment is required
- **Deferred**: Railway deployment planned but not immediate

## Cost Breakdown
- **Current Infrastructure**: ~$168/month (FMP $139 + Polygon $29)
- **Railway Platform (Future)**: ~$20/month (Postgres $5 + Backend $5 + Frontend $10)
- **Total Projected Cost**: ~$188/month (when deployed to Railway)

## Phase 1 — Active Development (Local)

Current workflow (unchanged):
```bash
# Frontend with hot reload
cd frontend && npm run dev

# Backend with auto-reload
cd backend && uv run python run.py

# Database (Dockerized locally)
cd backend && docker-compose up -d postgres
```

When to move to Phase 2:
- Need consistent frontend environment across team members
- Preparing for production deployment
- Want to test containerized frontend before Railway deployment

## Phase 2 — Frontend Dockerization

**Goal**: Containerize the Next.js frontend for development consistency and deployment readiness.

### Why Frontend First?

1. **Development Consistency**: Eliminates "works on my machine" issues across team
2. **Deployment Ready**: Container can be deployed to Railway, Vercel, or any platform
3. **Environment Parity**: Dev, staging, and production use identical configurations
4. **Simpler Stack**: Frontend has fewer dependencies than backend (no DB, no API keys)

### Implementation Plan

#### 2.1 Create Multi-Stage Dockerfile

**Location**: `frontend/Dockerfile`

```dockerfile
# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --only=production

# Stage 2: Builder
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 3: Runner
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV production

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy necessary files
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3005

ENV PORT 3005
ENV HOSTNAME "0.0.0.0"

CMD ["node", "server.js"]
```

#### 2.2 Next.js Configuration

**Update**: `frontend/next.config.js`

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone', // Enable standalone output for Docker
  env: {
    NEXT_PUBLIC_BACKEND_API_URL: process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000',
  },
  // ... rest of config
}

module.exports = nextConfig
```

#### 2.3 Docker Compose for Local Development

**Location**: `frontend/docker-compose.yml`

```yaml
version: '3.8'

services:
  frontend:
    build:
      context: .
      dockerfile: Dockerfile
      target: runner
    ports:
      - "3005:3005"
    environment:
      - NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000
      - NODE_ENV=production
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:3005/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

#### 2.4 Environment Variables

**Create**: `frontend/.env.docker`

```bash
# Backend API endpoint
NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000

# Production build
NODE_ENV=production

# Optional: Analytics, feature flags, etc.
```

#### 2.5 Development vs Production Modes

**Development** (unchanged):
```bash
cd frontend
npm run dev
# Runs on http://localhost:3005 with hot reload
```

**Docker Development** (testing container locally):
```bash
cd frontend
docker-compose up --build
# Runs containerized app on http://localhost:3005
```

**Production** (Railway/deployment):
```bash
# Railway automatically detects Dockerfile and builds
railway up
# Or manual build:
docker build -t sigmasight-frontend .
docker run -p 3005:3005 sigmasight-frontend
```

#### 2.6 .dockerignore

**Create**: `frontend/.dockerignore`

```
node_modules
.next
.git
.gitignore
.env.local
.env*.local
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.DS_Store
*.pem
coverage
.vercel
```

### Testing Frontend Container

```bash
# 1. Build the image
cd frontend
docker build -t sigmasight-frontend .

# 2. Run the container
docker run -d -p 3005:3005 \
  -e NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000 \
  --name frontend \
  sigmasight-frontend

# 3. Verify health
curl http://localhost:3005/api/health

# 4. Test in browser
open http://localhost:3005

# 5. Stop and remove
docker stop frontend && docker rm frontend
```

### Image Optimization

- **Size**: Multi-stage build reduces image from ~1GB to ~150MB
- **Security**: Non-root user (nextjs:nodejs)
- **Caching**: Separate dependency and build layers for faster rebuilds
- **Standalone**: Next.js standalone output includes only necessary files

### Integration with Backend

Frontend container connects to backend via environment variable:

```bash
# Development (local backend)
NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000

# Docker network (if backend also containerized)
NEXT_PUBLIC_BACKEND_API_URL=http://backend:8000

# Railway (future deployment)
NEXT_PUBLIC_BACKEND_API_URL=https://sigmasight-backend.railway.app
```

### Railway Deployment (Future)

When ready to deploy frontend to Railway:

```bash
# 1. Create Railway project
railway init

# 2. Set environment variables
railway variables set NEXT_PUBLIC_BACKEND_API_URL=https://backend.railway.app

# 3. Deploy
railway up

# Railway automatically:
# - Detects Dockerfile
# - Builds multi-stage image
# - Deploys to custom domain
# - Provides HTTPS
```

### Monitoring and Debugging

```bash
# View container logs
docker logs -f frontend

# Exec into container
docker exec -it frontend sh

# Check environment variables
docker exec frontend env | grep NEXT_PUBLIC

# Monitor resource usage
docker stats frontend
```

### When to Move to Phase 3

- Planning to deploy backend to Railway
- Need backend containerization for consistency
- Require full-stack Docker Compose orchestration

## Phase 3 — Backend Dockerization (Future)

**Status**: Deferred until Railway deployment is planned

### Brief Overview

Backend will remain running locally with `uv run python run.py` for now. When backend containerization is needed:

**Triggers**:
- Railway deployment required
- Need environment consistency across team
- Production deployment planning

**Quick Implementation**:
```dockerfile
# backend/Dockerfile (when needed)
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Not a Priority**: Backend local development with `uv run python run.py` works well. Containerization will be implemented when Railway deployment is scheduled.

## Migration Path

### Current State
```
Frontend: npm run dev (port 3005)
Backend: uv run python run.py (port 8000)
Database: docker-compose up -d postgres
```

### After Phase 2
```
Frontend: docker-compose up frontend (port 3005) OR npm run dev
Backend: uv run python run.py (port 8000)
Database: docker-compose up -d postgres
```

### Future (Phase 3 + Railway)
```
Frontend: Railway (https://sigmasight.railway.app)
Backend: Railway (https://sigmasight-backend.railway.app)
Database: Railway Postgres (managed)
```

## Security Considerations

### Frontend Container
- Non-root user (nextjs:nodejs, UID 1001)
- Read-only file system (Next.js standalone)
- No secrets in image (runtime environment variables only)
- Minimal attack surface (alpine base, production dependencies only)

### Environment Variables
- Never commit `.env.local` or `.env.production` files
- Use Railway environment variables for production secrets
- Separate configs per environment (dev, staging, prod)

## References and Resources

### Next.js Docker
- Next.js Deployment: https://nextjs.org/docs/deployment
- Next.js Docker Example: https://github.com/vercel/next.js/tree/canary/examples/with-docker
- Next.js Standalone Output: https://nextjs.org/docs/advanced-features/output-file-tracing

### Railway
- Railway Dockerfiles: https://docs.railway.com/reference/dockerfiles
- Railway Environments: https://docs.railway.com/reference/environments
- Railway Variables: https://docs.railway.com/guides/variables

### Docker Best Practices
- Multi-stage builds: https://docs.docker.com/build/building/multi-stage/
- Node.js Docker best practices: https://github.com/nodejs/docker-node/blob/main/docs/BestPractices.md

## Document Status and Next Steps

**Status**: Phase 2 (Frontend Dockerization) Ready for Implementation

**Immediate Next Steps**:
1. Create `frontend/Dockerfile` with multi-stage build
2. Update `next.config.js` with standalone output
3. Create `frontend/docker-compose.yml` for local testing
4. Test containerized frontend locally
5. Document team workflow for Docker vs npm dev

**Future Considerations**:
- Backend containerization (Phase 3) when Railway deployment is scheduled
- Full-stack docker-compose orchestration
- CI/CD pipeline integration

## Version History
- v1.4 (2025-10-04): Focused on Frontend Dockerization; removed Phase 2 (Shared Dev DB); expanded Frontend implementation plan; simplified Backend to brief future section
- v1.3 (2025-09-08): Added cost breakdown, migration safety, Railway focus
- v1.2 (2025-09-08): Initial Railway-focused revision
- v1.1: Original Docker-first approach
