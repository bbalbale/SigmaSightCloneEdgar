# Docker Setup Guide

Updated: 2025-10-09

## Quick Start

### Using Docker Compose (Recommended)

```bash
# 1. Ensure .env.local is configured (copy from .env.example if needed)
cp .env.example .env.local
# Edit .env.local with your settings

# 2. Build and start the container
cd frontend
docker-compose up -d

# 3. View logs
docker-compose logs -f

# 4. Stop the container
docker-compose down
```

### Using Docker Commands Directly

```bash
cd frontend

# Build the image
docker build -t sigmasight-frontend .

# Run with environment variables from .env.local
docker run -d \
  -p 3005:3005 \
  --env-file .env.local \
  --name sigmasight-frontend \
  sigmasight-frontend

# Or run with inline environment variables
docker run -d \
  -p 3005:3005 \
  -e BACKEND_URL=http://localhost:8000 \
  -e NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000/api/v1 \
  -e OPENAI_API_KEY=your_key_here \
  --name sigmasight-frontend \
  sigmasight-frontend
```

## Configuration

### Environment Variables

The Docker container uses the same environment variables as local development. Configure these in `.env.local`:

**Required:**
- `BACKEND_URL` - Backend server URL (proxy layer)
- `NEXT_PUBLIC_BACKEND_API_URL` - Backend API URL (client-side)
- `OPENAI_API_KEY` - OpenAI API key for chat features

**Optional:**
- `NEXT_PUBLIC_DEBUG` - Enable debug mode
- `NEXT_PUBLIC_DEFAULT_PORTFOLIO_ID` - Default portfolio
- `NEXT_PUBLIC_MARKET_DATA_REFRESH_INTERVAL` - Data refresh interval
- `NEXT_PUBLIC_ENABLE_REALTIME_DATA` - Enable real-time data
- `NEXT_PUBLIC_ENABLE_HISTORICAL_CHARTS` - Enable historical charts

### Switching Between Local and Railway Backend

**Local Backend:**
```bash
# In .env.local:
NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000/api/v1
BACKEND_URL=http://localhost:8000
```

**Railway Backend:**
```bash
# In .env.local:
NEXT_PUBLIC_BACKEND_API_URL=https://sigmasight-be-sandbox-frontendrailway.up.railway.app/api/v1
BACKEND_URL=https://sigmasight-be-sandbox-frontendrailway.up.railway.app
```

After changing `.env.local`, rebuild and restart:
```bash
docker-compose down
docker-compose up -d --build
```

## Multi-Stage Build Details

The Dockerfile uses a 3-stage build for optimization:

1. **deps** - Installs all dependencies (cached layer)
2. **builder** - Builds the Next.js application with all dependencies
3. **runner** - Minimal production image (~210MB)

### Build Arguments

You can pass build arguments during build:

```bash
docker build \
  --build-arg NEXT_PUBLIC_BACKEND_API_URL=https://your-backend.com/api/v1 \
  --build-arg OPENAI_API_KEY=your_key \
  -t sigmasight-frontend .
```

## Health Check

The container includes a health check that pings `/api/health` every 30 seconds:

```bash
# Check container health status
docker ps

# View health check logs
docker inspect sigmasight-frontend | grep Health -A 10
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker logs sigmasight-frontend

# Check if port is already in use
netstat -ano | findstr :3005

# Use a different port
docker run -d -p 3006:3005 --env-file .env.local --name sigmasight-frontend sigmasight-frontend
```

### Environment variables not working
```bash
# Verify .env.local exists and has correct values
cat .env.local

# Rebuild with --no-cache
docker build --no-cache -t sigmasight-frontend .

# Check environment inside container
docker exec sigmasight-frontend env | grep BACKEND
```

### Build fails
```bash
# Clean up and rebuild
docker-compose down
docker system prune -a
docker-compose up -d --build

# Or with detailed output
docker build --no-cache --progress=plain -t sigmasight-frontend .
```

### Can't connect to backend
```bash
# If using local backend, ensure it's accessible from Docker
# Use host.docker.internal on Windows/Mac instead of localhost
BACKEND_URL=http://host.docker.internal:8000

# Or use your machine's IP address
BACKEND_URL=http://192.168.1.X:8000
```

## Common Commands

```bash
# Start container
docker-compose up -d

# Stop container
docker-compose down

# Restart container
docker-compose restart

# View logs
docker-compose logs -f

# Rebuild and restart
docker-compose up -d --build

# Remove everything and rebuild
docker-compose down
docker rmi sigmasight-frontend
docker-compose up -d --build

# Execute command in container
docker exec -it sigmasight-frontend sh

# Check health
curl http://localhost:3005/api/health
```

## Production Deployment

For production deployments:

1. Use production environment variables
2. Set `NODE_ENV=production`
3. Use HTTPS backend URL
4. Secure your OPENAI_API_KEY
5. Consider using Docker secrets or environment injection

```bash
docker build \
  --build-arg NEXT_PUBLIC_BACKEND_API_URL=https://api.production.com/api/v1 \
  -t sigmasight-frontend:production .

docker run -d \
  -p 80:3005 \
  -e NODE_ENV=production \
  --env-file .env.production \
  --restart unless-stopped \
  sigmasight-frontend:production
```

## Notes

- **Node Version**: Uses Node 20 LTS (alpine)
- **Image Size**: ~210MB optimized
- **Port**: 3005 (configurable)
- **User**: Runs as non-root user (nextjs:nodejs)
- **Build Time**: ~2-3 minutes (first build), ~30s (cached)
- **Standalone Output**: Uses Next.js standalone mode for minimal runtime
