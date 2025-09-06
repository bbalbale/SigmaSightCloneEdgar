# Dockerization and Deployment Plan v1.1

**Document Version**: 1.1  
**Date**: 2025-09-06  
**Status**: Implementation Ready  
**Target Platform**: Railway.app

## Executive Summary

This document outlines the complete Dockerization strategy for both local development and production deployment of the SigmaSight platform. The system consists of three containerized services: Frontend (Next.js), Backend (FastAPI), and Database (PostgreSQL). 

### Recommended Development Approach

**Important**: We recommend a pragmatic, phased approach to Docker adoption:

**Phase 0** (Current - Active Development): Continue using traditional tools (npm/uv) for maximum productivity
**Phase 1** (Deferred): Local Docker Development Environment when team/complexity grows
**Phase 2** (Pre-Production): Backend Dockerization for production readiness
**Phase 3** (Production): Full Docker deployment on Railway

**Key Insight**: Railway.app's automatic containerization eliminates the traditional need for development Docker as a stepping stone to production. Railway can build optimized containers directly from your npm/Python code, making the dev Docker → production Docker progression unnecessary for small teams.

This approach prioritizes developer productivity during active feature development while leveraging Railway's capabilities for production deployment.

### Implementation Timeline

0. **Phase 0**: Traditional Development (npm/uv) - **ACTIVE NOW**
1. **Phase 1**: Local Docker Development Environment - **DEFERRED until needed**
2. **Phase 2**: Backend Production Dockerization - **Priority when approaching deployment**
3. **Phase 3**: Railway Production Deployment - **Final step**

Currently, the frontend has production Docker support only (no development Docker), and the backend requires containerization for both development and production use.

## 🚀 Current Recommended Workflow

### For Active Development (NOW)
```bash
# Frontend - with hot reload
cd frontend && npm run dev

# Backend - with auto-reload
cd backend && uv run python run.py

# Database - already in Docker
docker-compose up -d postgres
```

**This approach provides:**
- ✅ Instant hot reload for frontend changes
- ✅ Fast backend restarts on code changes
- ✅ Maximum developer productivity
- ✅ Proven, working setup

### For Production Testing (LATER)
```bash
# Only when verifying production builds
cd frontend
docker build -t sigmasight-frontend .
docker run -p 3005:3005 sigmasight-frontend
```

### When to Switch to Full Docker
- 2-4 weeks before production deployment
- When team size exceeds 3 developers
- When environment inconsistencies cause issues

## Table of Contents

1. [Current State of Dockerization](#1-current-state-of-dockerization)
2. [Phase 0: Traditional Development (ACTIVE)](#2-phase-0-traditional-development-active)
3. [Phase 1: Local Docker Development Environment (DEFERRED)](#3-phase-1-local-docker-development-environment-deferred)
4. [Phase 2: Backend Production Dockerization](#4-phase-2-backend-production-dockerization)
5. [Phase 3: Railway Deployment Strategy](#5-phase-3-railway-deployment-strategy)
6. [Migration and Rollback Plan](#6-migration-and-rollback-plan)
7. [Testing Checklist](#7-testing-checklist)
8. [Cost Estimation](#8-cost-estimation)
9. [Monitoring and Maintenance](#9-monitoring-and-maintenance)
10. [Security Considerations](#10-security-considerations)
11. [References and Resources](#11-references-and-resources)

## 1. Current State of Dockerization

### Understanding Production vs Development Docker

**Production Docker** focuses on:
- **Optimized image size** (smaller = faster deployment)
- **Static builds** (code compiled/bundled at build time)
- **Security** (non-root users, minimal attack surface)
- **Immutability** (container never changes after build)
- **Performance** (no development tools or hot reload overhead)

**Development Docker** focuses on:
- **Hot reload** (instant code updates without rebuild)
- **Volume mounting** (local files sync to container)
- **Development tools** (debuggers, linters, test runners)
- **Convenience** (all dependencies in container)
- **Consistency** (same environment for all developers)

### Current Implementation Status

| Component | **Production Docker** | **Development Docker** | **Notes** |
|-----------|----------------------|----------------------|--------|
| **Frontend** | ✅ Implemented | ❌ Not Implemented | Production-optimized (~210MB) |
| **Backend** | ❌ Not Implemented | ❌ Not Implemented | Runs via `uv run python run.py` |
| **PostgreSQL** | ✅ Implemented | ✅ Implemented | Standalone container only |
| **Unified Stack** | ❌ Not Implemented | ❌ Not Implemented | No docker-compose for full stack |

### 1.1 Database (PostgreSQL) - ✅ Containerized (Development & Production)

**Current Implementation**:
```yaml
# backend/docker-compose.yml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: sigmasight
      POSTGRES_PASSWORD: sigmasight_dev
      POSTGRES_DB: sigmasight_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

**Status**: 
- ✅ Running in Docker locally via docker-compose
- ✅ Health checks configured
- ✅ Persistent volume for data
- ✅ Ready for both development and production
- ⚠️ **Isolated** - not integrated with frontend/backend in unified stack

### 1.2 Frontend (Next.js) - ✅ Production Docker Only

**Current Production Implementation** (`frontend/Dockerfile`):
```dockerfile
# Multi-stage production build
FROM node:18-alpine AS deps      # Install dependencies
FROM node:18-alpine AS builder    # Build static assets
FROM node:18-alpine AS runner     # Minimal runtime
```

**Production Features**:
- ✅ Multi-stage build optimization (~210MB image)
- ✅ Standalone Next.js output (pre-compiled)
- ✅ Health check endpoint at `/api/health`
- ✅ Non-root user execution (security)
- ✅ Ready for Railway/Render deployment

**Development Limitations**:
- ❌ **No hot reload** - requires full rebuild for code changes
- ❌ **No volume mounting** - can't sync local files
- ❌ **Static build** - `npm run build` baked into image
- ❌ **Not suitable for development** - 5-10 minute rebuild cycles

### 1.3 Backend (FastAPI) - ❌ No Docker Implementation

**Current State**:
- 🔧 Runs via `uv run python run.py` (local Python)
- ❌ No Dockerfile exists (neither production nor development)
- 📦 Dependencies managed by uv/pip locally
- ⚠️ Requires containerization for both development and deployment

### 1.4 Current Developer Workflow (Non-Docker)

```bash
# What developers do today (mixed environment):
cd backend && docker-compose up -d    # Step 1: PostgreSQL in Docker
cd backend && uv run python run.py    # Step 2: Backend on host machine
cd frontend && npm run dev            # Step 3: Frontend on host machine

# Problems with this approach:
# - Requires local Python installation
# - Requires local Node.js installation
# - Version conflicts between developers
# - "Works on my machine" issues
# - Different behavior Mac vs Windows
```

### 1.5 Gap Analysis

**What's Missing for Development**:
- `docker-compose.dev.yml` - Unified stack orchestration
- `frontend/Dockerfile.dev` - Development container with hot reload
- `backend/Dockerfile.dev` - Development container with auto-restart
- Platform-specific scripts (Mac/Windows setup)
- Developer convenience tools (Makefile, scripts)

**What's Missing for Production**:
- `backend/Dockerfile` - Production-optimized backend container
- `docker-compose.prod.yml` - Production stack orchestration
- Environment-specific configurations
- Security hardening
- Monitoring integration

## 2. Phase 0: Traditional Development (ACTIVE)

### Current Approach

**Status**: ✅ **ACTIVE** - This is our current development workflow

**Tools in Use**:
- **Frontend**: `npm run dev` (Next.js with hot reload)
- **Backend**: `uv run python run.py` (FastAPI with auto-reload)
- **Database**: Docker PostgreSQL container

### Why This Approach Works Now

1. **Maximum Productivity**:
   - Instant hot reload for frontend changes
   - Fast backend restarts (~2 seconds)
   - No Docker rebuild delays (2-3 minutes saved per change)

2. **Proven Setup**:
   - All features working correctly
   - Established debugging workflows
   - Familiar tooling for the team

3. **Suitable for Current Scale**:
   - Single/small developer team
   - Consistent development machines (Mac primary)
   - No cross-platform issues yet

### Quick Start Commands

```bash
# Terminal 1: Database
cd backend
docker-compose up -d postgres

# Terminal 2: Backend
cd backend
uv run python run.py

# Terminal 3: Frontend
cd frontend
npm run dev
```

### When to Move Beyond Phase 0

Consider transitioning to Docker development when:
- **Team Growth**: More than 3 developers join
- **Platform Issues**: "Works on my machine" becomes frequent
- **CI/CD Requirements**: Pipeline needs Docker parity
- **Timeline**: 2-4 weeks before production deployment

## 3. Phase 1: Local Docker Development Environment (DEFERRED)

### Why This Phase is Deferred

**Current Recommendation**: Continue using npm/uv for local development until approaching production deployment.

**Primary Rationale - Railway Simplifies Everything**:

Railway.app provides automatic containerization, which fundamentally changes the Docker equation:

1. **Railway Auto-Builds Containers**: Railway detects your framework and builds optimized containers automatically
   - No need to learn Docker networking, volumes, or multi-stage builds
   - Railway handles Python/Node.js detection and optimization
   - Production containers are created from your code, not your Dockerfiles

2. **Traditional Docker Path** (without Railway):
   - Dev Docker → Learn patterns → Write production Docker → Deploy
   - Total time: 5-7 days of Docker work
   
3. **Railway Path** (our approach):
   - Skip dev Docker → Continue npm/uv → Railway auto-containerizes → Deploy
   - Total time: 1 day configuration

**Additional Reasons to Defer**:
1. **Hot Reload is Critical**: Current Docker setup lacks hot reload, causing 2-3 minute rebuild cycles per change
2. **Productivity Impact**: Docker development would reduce iteration speed by 10-20x
3. **Working Solution Exists**: npm run dev + uv run python run.py is proven and fast
4. **Small Team**: Environment consistency less critical with 1-2 developers

**When to Implement Docker Development**:
- When team grows beyond 3 developers
- When "works on my machine" issues become frequent
- When preparing for production deployment (2-4 weeks before)
- When CI/CD pipeline requires Docker parity

### 2.1 Objectives (When Implemented)

- **Cross-Platform Development**: Single setup for Mac, Windows, and Linux developers
- **Zero Local Dependencies**: No need to install Python, Node.js, or PostgreSQL locally
- **Hot Reload**: Instant code updates without container rebuilds
- **Team Consistency**: Identical development environment for all team members
- **Quick Onboarding**: New developers productive in < 10 minutes

### 2.2 Development Docker Compose Configuration

Create `docker-compose.dev.yml` in project root:

```yaml
# docker-compose.dev.yml - Complete Local Development Stack
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3005:3005"
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    environment:
      - NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000
      - NODE_ENV=development
      - WATCHPACK_POLLING=true  # For Windows file watching
    networks:
      - sigmasight-dev
    command: npm run dev

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - backend_venv:/app/.venv  # Persist Python packages
    environment:
      - DATABASE_URL=postgresql+asyncpg://sigmasight:sigmasight_dev@postgres:5432/sigmasight_db
      - PYTHONDONTWRITEBYTECODE=1
      - PYTHONUNBUFFERED=1
      - SECRET_KEY=local-development-secret-key
      - ENVIRONMENT=development
      - LOG_LEVEL=DEBUG
    networks:
      - sigmasight-dev
    depends_on:
      postgres:
        condition: service_healthy
    command: >
      sh -c "
      alembic upgrade head &&
      uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
      "

  postgres:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=sigmasight
      - POSTGRES_PASSWORD=sigmasight_dev
      - POSTGRES_DB=sigmasight_db
    volumes:
      - postgres_dev_data:/var/lib/postgresql/data
      - ./backend/scripts/init_dev.sql:/docker-entrypoint-initdb.d/01-init.sql
      - ./backend/scripts/seed_dev.sql:/docker-entrypoint-initdb.d/02-seed.sql
    networks:
      - sigmasight-dev
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sigmasight -d sigmasight_db"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_dev_data:
    name: sigmasight_postgres_dev
  backend_venv:
    name: sigmasight_backend_venv

networks:
  sigmasight-dev:
    name: sigmasight_development
    driver: bridge
```

### 2.3 Development Dockerfiles

#### Frontend Development Dockerfile

Create `frontend/Dockerfile.dev`:

```dockerfile
# frontend/Dockerfile.dev - Development with Hot Reload
FROM node:18-alpine

WORKDIR /app

# Install dependencies for better compatibility
RUN apk add --no-cache libc6-compat

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Expose port
EXPOSE 3005

# Development server with hot reload
CMD ["npm", "run", "dev"]
```

#### Backend Development Dockerfile

Create `backend/Dockerfile.dev`:

```dockerfile
# backend/Dockerfile.dev - Development with Hot Reload
FROM python:3.11

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python package manager
RUN pip install --upgrade pip uv

# Copy dependency files
COPY pyproject.toml uv.lock* requirements.txt* ./

# Install Python dependencies
RUN uv pip install --system -r requirements.txt || \
    pip install -r requirements.txt

# Install development dependencies
RUN pip install watchdog[watchmedo]

# Expose port
EXPOSE 8000

# Default command (overridden by docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### 2.4 Platform-Specific Setup

#### Mac/Linux Setup

```bash
#!/bin/bash
# scripts/dev-setup.sh

echo "🚀 Setting up SigmaSight development environment..."

# Check Docker installation
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker Desktop first."
    echo "   Visit: https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed."
    exit 1
fi

# Start services
echo "📦 Building and starting services..."
docker-compose -f docker-compose.dev.yml up --build -d

# Wait for services
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Run migrations
echo "🔄 Running database migrations..."
docker-compose -f docker-compose.dev.yml exec backend alembic upgrade head

# Seed database
echo "🌱 Seeding database with demo data..."
docker-compose -f docker-compose.dev.yml exec backend python scripts/seed_database.py

echo "✅ Development environment ready!"
echo "   Frontend: http://localhost:3005"
echo "   Backend:  http://localhost:8000"
echo "   Database: postgresql://localhost:5432/sigmasight_db"
```

#### Windows Setup

```powershell
# scripts/dev-setup.ps1

Write-Host "🚀 Setting up SigmaSight development environment..." -ForegroundColor Green

# Check Docker Desktop
$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
    Write-Host "❌ Docker Desktop is not installed." -ForegroundColor Red
    Write-Host "   Please install from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# Check WSL2
$wsl = wsl --list --quiet 2>$null
if (-not $wsl) {
    Write-Host "⚠️  WSL2 is recommended for better performance." -ForegroundColor Yellow
    Write-Host "   Install guide: https://docs.microsoft.com/en-us/windows/wsl/install" -ForegroundColor Yellow
}

# Set environment variable for Windows paths
$env:COMPOSE_CONVERT_WINDOWS_PATHS = 1

# Start services
Write-Host "📦 Building and starting services..." -ForegroundColor Cyan
docker-compose -f docker-compose.dev.yml up --build -d

# Wait for services
Write-Host "⏳ Waiting for services..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Run migrations
Write-Host "🔄 Running database migrations..." -ForegroundColor Cyan
docker-compose -f docker-compose.dev.yml exec backend alembic upgrade head

# Seed database
Write-Host "🌱 Seeding database..." -ForegroundColor Cyan
docker-compose -f docker-compose.dev.yml exec backend python scripts/seed_database.py

Write-Host "✅ Development environment ready!" -ForegroundColor Green
Write-Host "   Frontend: http://localhost:3005" -ForegroundColor White
Write-Host "   Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "   Database: postgresql://localhost:5432/sigmasight_db" -ForegroundColor White
```

### 2.5 Developer Commands

Create `Makefile` for common commands:

```makefile
# Makefile - Developer convenience commands

.PHONY: dev dev-build dev-stop dev-clean dev-logs dev-shell-backend dev-shell-frontend dev-db-reset

# Start development environment
dev:
	@docker-compose -f docker-compose.dev.yml up

# Build and start development environment
dev-build:
	@docker-compose -f docker-compose.dev.yml up --build

# Stop development environment
dev-stop:
	@docker-compose -f docker-compose.dev.yml down

# Clean development environment (including volumes)
dev-clean:
	@docker-compose -f docker-compose.dev.yml down -v
	@docker volume rm sigmasight_postgres_dev sigmasight_backend_venv 2>/dev/null || true

# View logs
dev-logs:
	@docker-compose -f docker-compose.dev.yml logs -f

# Shell into backend container
dev-shell-backend:
	@docker-compose -f docker-compose.dev.yml exec backend bash

# Shell into frontend container
dev-shell-frontend:
	@docker-compose -f docker-compose.dev.yml exec frontend sh

# Reset database
dev-db-reset:
	@docker-compose -f docker-compose.dev.yml exec backend alembic downgrade base
	@docker-compose -f docker-compose.dev.yml exec backend alembic upgrade head
	@docker-compose -f docker-compose.dev.yml exec backend python scripts/seed_database.py

# Run tests
dev-test:
	@docker-compose -f docker-compose.dev.yml exec backend pytest
	@docker-compose -f docker-compose.dev.yml exec frontend npm test
```

### 2.6 IDE Configuration

#### VS Code Configuration

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "/usr/local/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "[python]": {
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  },
  "docker.commands.build": "docker-compose -f docker-compose.dev.yml build",
  "docker.commands.run": "docker-compose -f docker-compose.dev.yml up"
}
```

### 2.7 Troubleshooting Guide

#### Common Issues and Solutions

**Issue: Port already in use**
```bash
# Mac/Linux
lsof -ti:3005 | xargs kill -9  # Kill frontend port
lsof -ti:8000 | xargs kill -9  # Kill backend port
lsof -ti:5432 | xargs kill -9  # Kill database port

# Windows PowerShell
netstat -ano | findstr :3005
taskkill /PID <PID> /F
```

**Issue: Hot reload not working on Windows**
```yaml
# Add to docker-compose.dev.yml frontend service:
environment:
  - WATCHPACK_POLLING=true
  - CHOKIDAR_USEPOLLING=true
```

**Issue: Database connection errors**
```bash
# Check if postgres is healthy
docker-compose -f docker-compose.dev.yml ps

# View postgres logs
docker-compose -f docker-compose.dev.yml logs postgres

# Restart postgres
docker-compose -f docker-compose.dev.yml restart postgres
```

**Issue: Slow performance on Windows**
```text
Solution: Use WSL2
1. Install WSL2: wsl --install
2. Clone repository inside WSL2
3. Run Docker commands from WSL2 terminal
4. Access via Windows browser at localhost:3005
```

### 2.8 Development Workflow

#### Daily Development

1. **Start Environment**:
   ```bash
   make dev  # or docker-compose -f docker-compose.dev.yml up
   ```

2. **Code Changes**:
   - Frontend: Changes auto-reload at http://localhost:3005
   - Backend: Changes auto-reload at http://localhost:8000
   - Database: Changes require migration

3. **Database Migrations**:
   ```bash
   # Create migration
   docker-compose -f docker-compose.dev.yml exec backend alembic revision --autogenerate -m "description"
   
   # Apply migration
   docker-compose -f docker-compose.dev.yml exec backend alembic upgrade head
   ```

4. **Running Tests**:
   ```bash
   make dev-test
   ```

5. **Stop Environment**:
   ```bash
   make dev-stop
   ```

#### Team Collaboration

1. **Onboarding New Developer**:
   ```bash
   git clone https://github.com/elliottng/SigmaSight-BE.git
   cd SigmaSight-BE
   ./scripts/dev-setup.sh  # Mac/Linux
   ./scripts/dev-setup.ps1 # Windows
   ```

2. **Sharing Database State**:
   ```bash
   # Export
   docker-compose -f docker-compose.dev.yml exec postgres pg_dump -U sigmasight sigmasight_db > dump.sql
   
   # Import
   docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sigmasight sigmasight_db < dump.sql
   ```

## 4. Phase 2: Backend Production Dockerization

### 2.1 Dockerfile Creation

Create `backend/Dockerfile`:

```dockerfile
# backend/Dockerfile
# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock* requirements.txt* ./

# Install uv for dependency management
RUN pip install uv

# Install Python dependencies
RUN uv pip install --system -r requirements.txt || \
    pip install -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1001 sigmasight && \
    chown -R sigmasight:sigmasight /app

USER sigmasight

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Start command with migrations
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

### 2.2 Requirements File Generation

Create `backend/requirements.txt` from uv dependencies:

```bash
# Generate requirements.txt
cd backend
uv pip compile pyproject.toml -o requirements.txt
```

### 2.3 Environment Configuration

Create `backend/.env.docker`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://sigmasight:sigmasight_dev@postgres:5432/sigmasight_db

# API Keys (will be set in Railway)
OPENAI_API_KEY=${OPENAI_API_KEY}
POLYGON_API_KEY=${POLYGON_API_KEY}
FMP_API_KEY=${FMP_API_KEY}
FRED_API_KEY=${FRED_API_KEY}

# Application
SECRET_KEY=${SECRET_KEY:-your-secret-key-here}
ENVIRONMENT=production
LOG_LEVEL=INFO

# CORS
FRONTEND_URL=https://sigmasight-frontend.railway.app
```

### 2.4 Docker Ignore File

Create `backend/.dockerignore`:

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
.pytest_cache/
.coverage
*.egg-info/

# Development
.git/
.gitignore
.env
.env.local
*.log
*.sqlite
*.db

# IDE
.vscode/
.idea/
*.swp
*.swo

# Testing
tests/
test_*.py
*_test.py

# Documentation
docs/
_docs/
*.md
!README.md

# Scripts (except necessary ones)
scripts/
!scripts/run_migrations.sh
```

### AI Agent Implementation Steps

### Step 1: Prepare Dependencies
```bash
# TODO for AI Agent:
1. Navigate to backend directory
2. Run: uv pip compile pyproject.toml -o requirements.txt
3. Verify requirements.txt contains all dependencies
4. Test with: pip install -r requirements.txt in a clean venv
```

### Step 2: Create Dockerfile
```bash
# TODO for AI Agent:
1. Create backend/Dockerfile with content from section 2.1
2. Create backend/.dockerignore with content from section 2.4
3. Ensure health check endpoint exists in app/main.py:
   @app.get("/health")
   async def health():
       return {"status": "healthy"}
```

### Step 3: Build and Test Locally
```bash
# TODO for AI Agent:
1. Build image:
   docker build -t sigmasight-backend ./backend

2. Test standalone:
   docker run -p 8000:8000 \
     -e DATABASE_URL=postgresql://localhost:5432/sigmasight \
     sigmasight-backend

3. Test with docker-compose:
   Create docker-compose.test.yml with all 3 services
   docker-compose -f docker-compose.test.yml up
```

### Step 4: Optimize Image Size
```bash
# TODO for AI Agent:
1. Measure initial size: docker images sigmasight-backend
2. If > 500MB, optimize:
   - Use python:3.11-slim base
   - Remove unnecessary system packages
   - Clear apt cache
   - Use multi-stage build
3. Target: < 400MB final image
```

## 5. Phase 3: Railway Deployment Strategy

### 4.1 Project Structure on Railway

```
Railway Project: sigmasight-production
├── Service 1: sigmasight-frontend
│   ├── Source: GitHub (frontend/)
│   ├── Build: Dockerfile detected
│   └── Domain: sigmasight.railway.app
│
├── Service 2: sigmasight-backend  
│   ├── Source: GitHub (backend/)
│   ├── Build: Dockerfile detected
│   └── Domain: api.sigmasight.railway.app
│
└── Service 3: sigmasight-postgres
    ├── Source: Docker Hub (postgres:15)
    ├── Volume: /var/lib/postgresql/data
    └── Internal: postgres.railway.internal
```

### 4.2 Railway Configuration

#### Frontend Service Configuration
```yaml
# Railway Variables for Frontend
NEXT_PUBLIC_BACKEND_API_URL=https://api.sigmasight.railway.app
PORT=3005
NODE_ENV=production
```

#### Backend Service Configuration
```yaml
# Railway Variables for Backend
DATABASE_URL=${{Postgres.DATABASE_URL}}
PORT=8000
SECRET_KEY=${{RAILWAY_SECRET_KEY}}
OPENAI_API_KEY=${{OPENAI_API_KEY}}
POLYGON_API_KEY=${{POLYGON_API_KEY}}
FRONTEND_URL=https://sigmasight.railway.app
```

#### PostgreSQL Service Configuration
```yaml
# Railway Variables for PostgreSQL
POSTGRES_USER=sigmasight
POSTGRES_PASSWORD=${{RAILWAY_POSTGRES_PASSWORD}}
POSTGRES_DB=sigmasight_db
# Volume automatically attached at /var/lib/postgresql/data
```

### 4.3 Deployment Steps

#### Phase 1: Repository Preparation
```bash
1. Ensure all Dockerfiles are committed to GitHub
2. Push to main/production branch
3. Verify GitHub Actions (if any) pass
```

#### Phase 2: Railway Project Setup
```bash
1. Create new Railway project
2. Connect GitHub repository
3. Configure automatic deployments from main branch
```

#### Phase 3: Service Deployment Order
```bash
1. Deploy PostgreSQL first:
   - New Service → Docker Image → postgres:15
   - Add volume for data persistence
   - Configure environment variables
   - Wait for healthy status

2. Deploy Backend second:
   - New Service → GitHub → Select backend/
   - Railway auto-detects Dockerfile
   - Configure environment variables
   - Set DATABASE_URL from PostgreSQL
   - Generate domain

3. Deploy Frontend last:
   - New Service → GitHub → Select frontend/
   - Railway auto-detects Dockerfile
   - Set BACKEND_API_URL to backend domain
   - Generate public domain
```

### 4.4 Railway-Specific Features

#### Automatic SSL/HTTPS
- All public domains get free SSL certificates
- No configuration needed
- Automatic renewal

#### Internal Networking
```javascript
// Services communicate internally via:
http://backend.railway.internal:8000
http://postgres.railway.internal:5432
```

#### Environment Variable References
```bash
# Reference other services' variables:
DATABASE_URL=${{Postgres.DATABASE_URL}}
BACKEND_URL=${{Backend.RAILWAY_PUBLIC_DOMAIN}}
```

#### Health Checks & Monitoring
- Railway monitors health check endpoints
- Automatic restarts on failure
- Logs available in dashboard

## 6. Migration and Rollback Plan

### 5.1 Database Migration Strategy
```bash
# Migrations run automatically in Dockerfile CMD:
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app ..."]

# For manual migrations:
railway run alembic upgrade head
```

### 5.2 Rollback Procedure
```bash
1. Railway Dashboard → Service → Deployments
2. Find previous successful deployment
3. Click "Rollback to this deployment"
4. Verify service health
```

### 5.3 Data Backup Strategy
```bash
# Before deployment:
1. Backup PostgreSQL:
   railway run pg_dump sigmasight_db > backup.sql

2. Store backup securely
3. Test restore procedure
```

## 7. Testing Checklist

### Pre-Deployment Testing
- [ ] Backend Dockerfile builds successfully
- [ ] Backend health check endpoint responds
- [ ] Database migrations run without errors
- [ ] All three services communicate locally
- [ ] Environment variables properly configured
- [ ] Docker images under 500MB each

### Post-Deployment Verification
- [ ] All services show "Deployed" status
- [ ] Health checks passing
- [ ] Frontend loads at public URL
- [ ] API endpoints responding
- [ ] Database queries working
- [ ] Authentication flow functional
- [ ] Chat interface operational

## 8. Cost Estimation

### Railway Pricing (as of 2024)
```
Hobby Plan: $5/month (includes $5 usage)
- Frontend: ~$5-8/month
- Backend: ~$5-8/month  
- PostgreSQL: ~$5-8/month
- Estimated Total: $15-25/month

Pro Plan: $20/month (if scaling needed)
- Better resource limits
- Multiple environments
- Team collaboration
```

## 9. Monitoring and Maintenance

### Logging Strategy
```python
# Structured logging in backend:
import structlog
logger = structlog.get_logger()
logger.info("request_processed", user_id=user_id, endpoint=endpoint)
```

### Metrics to Track
- Response times (p50, p95, p99)
- Error rates by endpoint
- Database query performance
- Memory and CPU usage
- Active user sessions

### Alerting Rules
- Service down > 1 minute
- Error rate > 5%
- Response time p95 > 2 seconds
- Database connections > 80% of pool

## 10. Security Considerations

### Secret Management
```bash
# Use Railway's secret management:
- Never commit secrets to GitHub
- Use Railway environment variables
- Rotate secrets quarterly
- Use different secrets per environment
```

### Network Security
```yaml
# Internal services not exposed publicly:
- PostgreSQL: Only accessible internally
- Backend: Public domain with CORS configured
- Frontend: Public domain with CSP headers
```

## 11. References and Resources

### Railway Documentation
- [Getting Started](https://docs.railway.com/getting-started)
- [Dockerfiles](https://docs.railway.com/deploy/dockerfiles)
- [Environment Variables](https://docs.railway.com/guides/variables)
- [Databases](https://docs.railway.com/databases/postgresql)
- [Networking](https://docs.railway.com/reference/networking)
- [Deployments](https://docs.railway.com/deploy/deployments)
- [GitHub Integration](https://docs.railway.com/deploy/github)
- [Monitoring](https://docs.railway.com/reference/observability)

### Docker Best Practices
- [Docker Official Python Guide](https://docs.docker.com/language/python/)
- [Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [Security Best Practices](https://docs.docker.com/develop/security-best-practices/)

### FastAPI Deployment
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [FastAPI with Docker](https://fastapi.tiangolo.com/deployment/docker/)

## Appendix A: Complete docker-compose.yml for Local Testing

```yaml
# docker-compose.local.yml
version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "3005:3005"
    environment:
      - NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://sigmasight:sigmasight_dev@postgres:5432/sigmasight_db
      - SECRET_KEY=local-development-secret
    depends_on:
      postgres:
        condition: service_healthy

  postgres:
    image: postgres:15
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=sigmasight
      - POSTGRES_PASSWORD=sigmasight_dev
      - POSTGRES_DB=sigmasight_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sigmasight"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:

networks:
  default:
    name: sigmasight-network
```

## Appendix B: Troubleshooting Guide

### Common Issues and Solutions

#### Backend Container Won't Start
```bash
# Check logs:
docker logs sigmasight-backend

# Common fixes:
1. Ensure requirements.txt is generated
2. Check DATABASE_URL format
3. Verify migrations can run
4. Check port 8000 not in use
```

#### Database Connection Errors
```bash
# Verify PostgreSQL is running:
docker ps | grep postgres

# Test connection:
docker exec -it postgres psql -U sigmasight -d sigmasight_db

# Check network:
docker network inspect sigmasight-network
```

#### Railway Deployment Failures
```bash
# Check Railway logs:
railway logs

# Common issues:
1. Missing environment variables
2. Dockerfile syntax errors
3. Health check failures
4. Port configuration mismatch
```

---

**Document Status**: Ready for implementation  
**Next Steps**: 
1. AI Agent to implement backend Dockerfile
2. Local testing with docker-compose
3. Deploy to Railway following section 4.3

**Approvals Required**:
- [ ] Backend Dockerfile review
- [ ] Security audit of secrets management
- [ ] Cost approval for Railway services