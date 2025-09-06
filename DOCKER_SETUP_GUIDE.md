# Docker Setup Guide for SigmaSight

This guide will help you transition from traditional npm/uv development to Docker-based development for the SigmaSight project.

## Prerequisites

1. **Install Docker Desktop** (if not already installed):
   - Mac: https://docs.docker.com/desktop/install/mac-install/
   - Windows: https://docs.docker.com/desktop/install/windows-install/
   - Linux: https://docs.docker.com/desktop/install/linux-install/

2. **Verify Docker is running**:
   ```bash
   docker --version
   docker ps
   ```

## Quick Start (Production Mode)

### 1. Stop Current Development Servers

First, stop any running development servers to free up ports:

```bash
# Find and kill processes on port 3005 (frontend)
lsof -ti:3005 | xargs kill -9

# Find and kill processes on port 8000 (backend)
lsof -ti:8000 | xargs kill -9
```

### 2. Start Backend (Still using uv for now)

The backend doesn't have Docker support yet, so continue using uv:

```bash
cd backend
uv run python run.py
```

### 3. Build and Run Frontend with Docker

```bash
cd frontend

# Build the Docker image (first time or after code changes)
docker build -t sigmasight-frontend .

# Run the container
docker run -d -p 3005:3005 --name frontend sigmasight-frontend

# Access the application
open http://localhost:3005
```

## Docker Commands Reference

### Frontend Container Management

```bash
# Start container (if already built)
docker start frontend

# Stop container
docker stop frontend

# Restart container
docker restart frontend

# View logs
docker logs -f frontend

# Remove container (to rebuild)
docker stop frontend && docker rm frontend

# Check container status
docker ps -a | grep frontend

# Check health
curl http://localhost:3005/api/health
```

### Rebuilding After Code Changes

```bash
cd frontend

# Stop and remove old container
docker stop frontend && docker rm frontend

# Rebuild image
docker build -t sigmasight-frontend .

# Run new container
docker run -d -p 3005:3005 --name frontend sigmasight-frontend
```

## Development Workflow

### ⚠️ IMPORTANT: Docker is for Production Testing Only

**The current Docker setup is NOT recommended for local development or end-to-end testing.**

#### Why We're Deferring Development Docker (Railway Strategy)

**Key Insight**: We're deploying to Railway.app, which fundamentally changes the Docker equation:

1. **Railway Auto-Builds Containers** - Railway detects your framework and builds optimized containers automatically
   - No need to learn Docker networking, volumes, or multi-stage builds
   - Railway handles Python/Node.js detection and optimization
   - Production containers are created from your code, not your Dockerfiles

2. **Traditional Path** (without Railway):
   - Dev Docker → Learn patterns → Write production Docker → Deploy
   - Total time: 5-7 days of Docker work
   
3. **Our Railway Path**:
   - Skip dev Docker → Continue npm/uv → Railway auto-containerizes → Deploy
   - Total time: 1 day configuration

#### Additional Reasons to Avoid Docker for Development

- **No hot reload** - Every code change requires full rebuild (2-3 minutes)
- **Production-only build** - Uses static Next.js standalone output
- **No volume mounts** - Cannot edit code and see changes instantly
- **Optimized for deployment** - Multi-stage build focused on size (210MB), not dev experience
- **Productivity killer** - 10-20x slower iteration cycles vs npm run dev

### Option 1: Recommended for Development (npm + uv)

**Use this for all local development and end-to-end testing:**

```bash
# Frontend with npm (development mode with hot reload)
cd frontend
npm run dev  # Hot reload enabled, instant changes

# Backend with uv (development mode)
cd backend
uv run python run.py
```

✅ **Best for:**
- Active development
- Debugging
- End-to-end testing
- Quick iteration cycles

### Option 2: Docker for Production Verification Only

**Only use Docker when you need to verify the production build:**

```bash
# Frontend in Docker (production mode - NO hot reload)
cd frontend
docker build -t sigmasight-frontend .
docker run -d -p 3005:3005 --name frontend sigmasight-frontend

# Backend with uv
cd backend
uv run python run.py
```

✅ **Use Docker only for:**
- Final production build verification before deployment
- Testing Docker-specific issues (networking, env variables)
- Ensuring production build works correctly
- Pre-deployment checks

### Option 3: Future Development Docker (Not Yet Implemented)

📋 **Planned in Phase 1 of Dockerization Plan:**
- Development Docker with volume mounts
- Hot reload support in containers
- Docker Compose for full stack
- See `backend/_docs/requirements/Dockerization_and_Deployment_Plan_v1.1.md`

## Docker Compose (Future)

A `docker-compose.yml` file can be created to orchestrate both frontend and backend:

```yaml
# docker-compose.yml (example for future implementation)
version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "3005:3005"
    environment:
      - BACKEND_URL=http://backend:8000
    depends_on:
      - backend
      
  backend:
    build: ./backend  # Needs Dockerfile to be created
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db/sigmasight
      
  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=sigmasight
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Troubleshooting

### Port Already in Use

If you get "port already in use" errors:

```bash
# Mac/Linux
lsof -ti:3005 | xargs kill -9  # Kill frontend port
lsof -ti:8000 | xargs kill -9  # Kill backend port

# Windows (PowerShell as Admin)
netstat -ano | findstr :3005
taskkill /PID <PID> /F
```

### Docker Build Fails

1. Check Docker Desktop is running
2. Ensure you're in the `frontend` directory
3. Clear Docker cache: `docker system prune -a`

### Container Won't Start

```bash
# Check logs for errors
docker logs frontend

# Remove and rebuild
docker rm frontend
docker build --no-cache -t sigmasight-frontend .
docker run -d -p 3005:3005 --name frontend sigmasight-frontend
```

### Backend Connection Issues

The Docker container uses `host.docker.internal` to connect to the backend on your host machine. If this doesn't work:

1. Ensure backend is running on `http://localhost:8000`
2. Check firewall settings
3. On Linux, you might need to add `--add-host=host.docker.internal:host-gateway` to the docker run command

## Benefits of Docker

1. **Consistency**: Same environment across all machines
2. **Isolation**: No npm package conflicts
3. **Production-Ready**: Test production builds locally
4. **Easy Deployment**: Same image works everywhere
5. **Clean System**: No global npm packages needed

## Next Steps

1. Start with the Quick Start section above
2. Use Docker for testing production builds
3. Continue using npm for active development (hot reload)
4. Consider Docker Compose when backend Dockerfile is ready

## Current Status

- ✅ Frontend: Full Docker support (optimized to ~210MB)
- ⏳ Backend: Docker support not yet implemented (use uv)
- ⏳ Database: Can use Docker PostgreSQL or local instance