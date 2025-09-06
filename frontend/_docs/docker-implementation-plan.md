# Docker Implementation Plan for SigmaSight Frontend

**Document Version**: 1.0  
**Created**: 2025-09-06  
**Branch**: dockerfrontend  
**Author**: Frontend Architect Agent

---

## Executive Summary

This document outlines the complete Docker implementation plan for the SigmaSight frontend application. The plan ensures consistency with the existing backend Docker setup while addressing cross-platform compatibility (Windows, Mac, Linux) and maintaining a "just works" philosophy.

### Key Goals
- **Zero Configuration**: Works immediately with `docker-compose up`
- **Cross-Platform**: Identical behavior on Windows, Mac, and Linux
- **Consistent with Backend**: Follows same patterns as backend PostgreSQL setup
- **Developer Experience**: Preserves hot reload and familiar workflows
- **Production Ready**: Same container works in development and production

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Architecture Decisions](#2-architecture-decisions)
3. [Implementation Phases](#3-implementation-phases)
4. [Risk Management](#4-risk-management)
5. [Testing Strategy](#5-testing-strategy)
6. [Quick Start Guide](#6-quick-start-guide)
7. [Troubleshooting Guide](#7-troubleshooting-guide)

---

## 1. Current State Analysis

### Backend Docker Configuration (Existing)
```yaml
# backend/docker-compose.yml
services:
  postgres:
    image: postgres:15
    ports: ["5432:5432"]
    healthcheck: enabled
    volumes: postgres_data
```

**Key Observations**:
- Simple, single-service setup
- Uses official images
- Health checks for reliability
- Named volumes for data persistence
- No complex build process

### Frontend Current Setup
- **Framework**: Next.js 14.2.5
- **Node Version**: >=18.17.0
- **Port**: 3005 (custom)
- **Build Tool**: Next.js built-in
- **Package Manager**: npm
- **Key Features**:
  - App Router
  - TypeScript
  - Tailwind CSS
  - API Proxy (`/api/proxy/`)

### Cross-Platform Requirements
| Platform | Developers | Special Needs |
|----------|------------|---------------|
| Windows | You (PM) | Path handling, CRLF, polling for hot reload |
| Mac | Team members | Native file watching works |
| Linux | Team members | Most Docker-friendly |

---

## 2. Architecture Decisions

### Core Principles (Matching Backend Philosophy)

1. **Simplicity First**
   - No unnecessary abstractions
   - Single command startup
   - Clear error messages

2. **Official Images Only**
   - `node:18-alpine` for production (120MB)
   - `node:18` for development if Alpine fails
   - No custom base images

3. **Best Practice Defaults**
   ```dockerfile
   # Production optimized by default
   ENV NODE_ENV=production
   ENV NEXT_TELEMETRY_DISABLED=1
   
   # Development overrides via docker-compose
   ```

4. **Graceful Degradation**
   - Works without backend (mock data)
   - Works without environment variables (defaults)
   - Clear messages when services unavailable

### Technical Decisions

#### Base Image Strategy
```
Decision: node:18-alpine (production), node:18 (development fallback)
Rationale: Matches Node requirement, smallest secure image
Alternative: node:18-slim if Alpine causes issues
```

#### Build Strategy
```
Decision: Multi-stage builds with standalone output
Rationale: Reduces image from 1GB to <200MB
Implementation: Next.js output: 'standalone' configuration
```

#### Network Strategy
```
Decision: Shared bridge network 'sigmasight-network'
Rationale: Consistent with backend, enables service discovery
Service Names: frontend, backend, postgres
```

#### Volume Strategy
```
Development: Bind mounts with node_modules exclusion
Production: No volumes, immutable containers
Rationale: Hot reload in dev, security in production
```

#### Environment Variable Strategy
```
Build-time: ARG for public Next.js variables
Runtime: ENV for server-side variables
Secrets: Never in image, only runtime injection
```

---

## 3. Implementation Phases

### Phase 1: Basic Containerization (Day 1, Hours 1-2)

#### Goals
- Frontend runs in Docker
- Accessible at localhost:3005
- Production-ready image

#### Files to Create

**1. `frontend/Dockerfile`**
```dockerfile
# Multi-stage build for production
FROM node:18-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --only=production

FROM node:18-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Next.js telemetry disabled
ENV NEXT_TELEMETRY_DISABLED 1

# Build application
RUN npm run build

# Production image
FROM node:18-alpine AS runner
WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

# Security: non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy built application
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3005

ENV PORT 3005
ENV HOSTNAME "0.0.0.0"

CMD ["node", "server.js"]
```

**2. `frontend/.dockerignore`**
```
node_modules
.next
.git
*.md
.env.local
coverage
.DS_Store
Thumbs.db
npm-debug.log*
```

**3. `frontend/next.config.js` (modification)**
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Add for Docker optimization
  output: 'standalone',
  
  // Existing config...
  webpack: (config, { dev, isServer }) => {
    // Add for Windows development
    if (dev && !isServer && process.env.DOCKER_ENV === 'development') {
      config.watchOptions = {
        poll: 1000,
        aggregateTimeout: 300,
      }
    }
    return config
  },
}
```

#### Validation Steps
```bash
cd frontend
docker build -t sigmasight-frontend:test .
docker run -p 3005:3005 sigmasight-frontend:test
# Visit http://localhost:3005
```

#### Success Criteria
- [ ] Image builds without errors
- [ ] Container starts and shows landing page
- [ ] Image size < 300MB
- [ ] No secrets in image layers

---

### Phase 2: Development Experience (Day 1, Hours 3-4)

#### Goals
- Hot reload working on all platforms
- Familiar npm workflow preserved
- Fast rebuilds

#### Files to Create

**1. `frontend/Dockerfile.dev`**
```dockerfile
FROM node:18-alpine
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Development environment
ENV NODE_ENV development
ENV NEXT_TELEMETRY_DISABLED 1
ENV CHOKIDAR_USEPOLLING true
ENV WATCHPACK_POLLING true

EXPOSE 3005

CMD ["npm", "run", "dev"]
```

**2. Root `docker-compose.yml` (unified)**
```yaml
version: '3.8'

services:
  # PostgreSQL (from backend)
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
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sigmasight"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - sigmasight-network

  # Backend API
  backend:
    image: sigmasight-backend:latest
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://sigmasight:sigmasight_dev@postgres:5432/sigmasight_db
      SECRET_KEY: ${SECRET_KEY:-development-secret-key}
      POLYGON_API_KEY: ${POLYGON_API_KEY}
      FMP_API_KEY: ${FMP_API_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - sigmasight-network
    volumes:
      - ./backend:/app
      - /app/__pycache__
    command: ["sh", "-c", "cd /app && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]

  # Frontend Production
  frontend:
    image: sigmasight-frontend:latest
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3005:3005"
    environment:
      BACKEND_URL: http://backend:8000
    depends_on:
      - backend
    networks:
      - sigmasight-network
    profiles:
      - production

  # Frontend Development (default)
  frontend-dev:
    image: sigmasight-frontend-dev:latest
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3005:3005"
    volumes:
      # Source code mount
      - ./frontend:/app
      # Exclude node_modules for performance
      - /app/node_modules
      - /app/.next
    environment:
      # Use host networking for backend in dev
      NEXT_PUBLIC_BACKEND_API_URL: http://localhost:8000/api/v1
      DOCKER_ENV: development
    depends_on:
      - backend
    networks:
      - sigmasight-network

networks:
  sigmasight-network:
    driver: bridge

volumes:
  postgres_data:
```

**3. `.gitattributes` (root, for Windows)**
```
# Ensure LF line endings in Docker
* text=auto eol=lf
*.{cmd,[cC][mM][dD]} text eol=crlf
*.{bat,[bB][aA][tT]} text eol=crlf
```

**4. `docker-compose.override.yml` (optional, for local overrides)**
```yaml
# Local development overrides (git-ignored)
version: '3.8'

services:
  frontend-dev:
    environment:
      # Add any local-specific environment variables
      NEXT_PUBLIC_DEBUG: "true"
```

#### Validation Steps
```bash
# Start everything
docker-compose up

# Test hot reload
# 1. Edit frontend/app/(landing)/page.tsx
# 2. Change some text
# 3. Save and check browser (should update in 3 seconds)

# Check logs
docker-compose logs -f frontend-dev
```

#### Success Criteria
- [ ] Hot reload works on Windows
- [ ] Hot reload works on Mac/Linux
- [ ] Changes visible within 3 seconds
- [ ] No "file not found" errors

---

### Phase 3: Integration & Optimization (Day 2, Hours 1-2)

#### Goals
- Seamless frontend-backend communication
- Optimized builds
- Production-ready setup

#### Optimizations to Implement

**1. Update `frontend/next.config.js`**
```javascript
const nextConfig = {
  output: 'standalone',
  compress: true,
  poweredByHeader: false,
  
  // Docker-specific optimizations
  experimental: {
    outputFileTracingRoot: undefined,
  },
  
  // Existing webpack config...
}
```

**2. Create `Makefile` (root, for convenience)**
```makefile
.PHONY: help up down build logs clean

help:
	@echo "Available commands:"
	@echo "  make up       - Start all services"
	@echo "  make down     - Stop all services"
	@echo "  make build    - Build all images"
	@echo "  make logs     - Show logs"
	@echo "  make clean    - Clean everything"

up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose build --no-cache

logs:
	docker-compose logs -f

clean:
	docker-compose down -v
	docker system prune -f
```

**3. Create health check endpoint `frontend/app/api/health/route.ts`**
```typescript
import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    version: process.env.npm_package_version || '0.1.0',
  });
}
```

**4. Add health check to Dockerfile**
```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3005/api/health', (r) => {r.statusCode === 200 ? process.exit(0) : process.exit(1)})"
```

---

## 4. Risk Management

### Critical Risks and Mitigations

#### Risk 1: Hot Reload Fails on Windows
**Probability**: High  
**Impact**: High (poor developer experience)  
**Detection**: File changes don't trigger rebuilds  
**Mitigation**:
```yaml
environment:
  CHOKIDAR_USEPOLLING: "true"
  WATCHPACK_POLLING: "true"
```
**Fallback**: Manual container restart

#### Risk 2: Frontend Can't Reach Backend
**Probability**: Medium  
**Impact**: High (app non-functional)  
**Detection**: API calls fail with ECONNREFUSED  
**Mitigation**:
```javascript
// Use service names in Docker network
const API_URL = process.env.DOCKER_ENV 
  ? 'http://backend:8000' 
  : 'http://localhost:8000';
```
**Fallback**: Mock data mode

#### Risk 3: Large Image Sizes
**Probability**: Medium  
**Impact**: Low (slower deployments)  
**Detection**: `docker images` shows >500MB  
**Mitigation**: Multi-stage builds, .dockerignore  
**Fallback**: Accept larger size temporarily

#### Risk 4: Node Module Compatibility
**Probability**: Low  
**Impact**: High (build failures)  
**Detection**: Build errors mentioning native modules  
**Mitigation**: Switch from Alpine to Debian base  
**Fallback**: Use node:18 instead of node:18-alpine

#### Risk 5: Port Conflicts
**Probability**: Low  
**Impact**: Medium (container won't start)  
**Detection**: "Port already in use" error  
**Mitigation**: Configurable ports via .env  
**Fallback**: Change port mapping in docker-compose

### Risk Matrix
```
Impact →  Low    Medium   High
High      -      R1       R1,R2
Medium    R3     R5       R2
Low       -      -        R4
↑ Probability
```

---

## 5. Testing Strategy

### Automated Tests

**1. Build Test Script** `scripts/test-docker-build.sh`
```bash
#!/bin/bash
set -e

echo "Testing Docker build..."
docker build -t test-frontend ./frontend

echo "Testing container startup..."
docker run -d --name test-container -p 3006:3005 test-frontend
sleep 10

echo "Testing health endpoint..."
curl -f http://localhost:3006/api/health || exit 1

echo "Cleaning up..."
docker stop test-container
docker rm test-container

echo "✅ All tests passed!"
```

**2. Integration Test Script** `scripts/test-full-stack.sh`
```bash
#!/bin/bash
set -e

echo "Starting full stack..."
docker-compose up -d

echo "Waiting for services..."
sleep 30

echo "Testing frontend..."
curl -f http://localhost:3005 || exit 1

echo "Testing backend..."
curl -f http://localhost:8000/api/v1/health || exit 1

echo "Testing frontend-backend connection..."
# Add specific API test

echo "✅ Integration tests passed!"
docker-compose down
```

### Manual Test Checklist

#### Phase 1 Checklist
- [ ] `docker build` completes without errors
- [ ] Image size is reasonable (<300MB)
- [ ] Container starts successfully
- [ ] Landing page loads at localhost:3005
- [ ] No errors in console

#### Phase 2 Checklist
- [ ] `docker-compose up` starts all services
- [ ] Hot reload works (test with text change)
- [ ] API proxy works (test login)
- [ ] Logs are readable and helpful
- [ ] Ctrl+C stops everything cleanly

#### Phase 3 Checklist
- [ ] Production build is optimized (<200MB)
- [ ] Health checks pass
- [ ] All environment variables work
- [ ] Cross-platform testing passes
- [ ] Documentation is complete

---

## 6. Quick Start Guide

### For Developers

#### First Time Setup
```bash
# Clone repository
git clone <repo-url>
cd SigmaSight

# Start everything
docker-compose up

# Visit frontend
open http://localhost:3005

# Visit backend
open http://localhost:8000/docs
```

#### Daily Workflow
```bash
# Start services
docker-compose up

# Stop services
docker-compose down

# View logs
docker-compose logs -f frontend-dev

# Rebuild after dependency changes
docker-compose build frontend-dev
docker-compose up
```

#### Common Tasks
```bash
# Run frontend tests
docker-compose exec frontend-dev npm test

# Install new package
docker-compose exec frontend-dev npm install <package>
docker-compose build frontend-dev

# Access container shell
docker-compose exec frontend-dev sh
```

### For Product Managers

#### Starting the Application
1. Open Docker Desktop
2. Open terminal in project folder
3. Run: `docker-compose up`
4. Visit: http://localhost:3005
5. Login with demo credentials

#### Checking Status
```bash
# Are services running?
docker-compose ps

# View recent logs
docker-compose logs --tail=50

# Stop everything
docker-compose down
```

#### Troubleshooting
- **Nothing starts**: Check Docker Desktop is running
- **Port in use**: Another app using port 3005
- **Can't login**: Backend may not be ready, wait 30 seconds
- **Changes don't appear**: Refresh browser with Ctrl+Shift+R

---

## 7. Troubleshooting Guide

### Common Issues and Solutions

#### Issue: "Cannot find module" errors
**Cause**: node_modules not properly mounted  
**Solution**:
```bash
docker-compose down
docker-compose build --no-cache frontend-dev
docker-compose up
```

#### Issue: Hot reload not working on Windows
**Cause**: File watching doesn't work across OS boundary  
**Solution**: Already configured with polling, check CHOKIDAR_USEPOLLING=true

#### Issue: "Port 3005 already in use"
**Cause**: Previous container still running or local dev server  
**Solution**:
```bash
# Find and stop process
netstat -ano | findstr :3005
taskkill /PID <process-id> /F

# Or change port in docker-compose.yml
ports:
  - "3006:3005"  # Use 3006 instead
```

#### Issue: API calls failing
**Cause**: Backend not ready or network issue  
**Solution**:
```bash
# Check backend is running
docker-compose ps
docker-compose logs backend

# Test backend directly
curl http://localhost:8000/api/v1/health

# Restart everything
docker-compose down
docker-compose up
```

#### Issue: Changes to package.json not taking effect
**Cause**: Dependencies cached in image  
**Solution**:
```bash
docker-compose build --no-cache frontend-dev
docker-compose up
```

### Debug Commands

```bash
# Check container status
docker ps -a

# Inspect container
docker inspect <container-id>

# View detailed logs
docker-compose logs -f --tail=100 frontend-dev

# Access container shell
docker-compose exec frontend-dev sh

# Check network connectivity
docker-compose exec frontend-dev ping backend

# Clean everything and start fresh
docker-compose down -v
docker system prune -f
docker-compose build --no-cache
docker-compose up
```

---

## Implementation Timeline

### Day 1 (Today)
- **Hour 1-2**: Phase 1 - Basic containerization
- **Hour 3-4**: Phase 2 - Development setup
- **Hour 5**: Testing and validation

### Day 2 (Tomorrow)
- **Hour 1-2**: Phase 3 - Optimization
- **Hour 3**: Cross-platform testing
- **Hour 4**: Documentation updates

### Day 3 (Optional)
- CI/CD integration
- Production deployment setup
- Performance tuning

---

## Success Metrics

### Immediate Success (Day 1)
- ✅ Single command startup: `docker-compose up`
- ✅ Works on Windows, Mac, Linux
- ✅ Hot reload functioning
- ✅ Frontend accessible at localhost:3005

### Short-term Success (Week 1)
- ✅ Team adoption without issues
- ✅ No "works on my machine" problems
- ✅ Faster onboarding for new developers
- ✅ Consistent development environment

### Long-term Success (Month 1)
- ✅ Production deployments using same containers
- ✅ Reduced deployment issues
- ✅ Improved development velocity
- ✅ Lower infrastructure costs

---

## Conclusion

This Docker implementation plan provides a robust, cross-platform solution that maintains the "just works" philosophy of the backend setup. The phased approach ensures we can validate at each step while maintaining the ability to rollback if issues arise.

The key to success is maintaining simplicity while addressing the real-world needs of a cross-platform development team. By following this plan, the SigmaSight frontend will have the same reliable Docker experience as the backend, with zero configuration required for developers.

### Next Steps
1. Review and approve the plan
2. Begin Phase 1 implementation
3. Test on Windows first (most challenging platform)
4. Iterate based on team feedback

---

**Document maintained by**: Frontend Architecture Team  
**Last updated**: 2025-09-06  
**Version**: 1.0