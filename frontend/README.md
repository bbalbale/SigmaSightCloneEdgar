# SigmaSight Frontend

A Next.js 14 portfolio analytics dashboard with real-time data visualization and AI-powered chat assistant.

## Quick Start

### Docker (Recommended)
```bash
# Production build and run
docker build -t sigmasight-frontend .
docker run -p 3005:3005 sigmasight-frontend

# Development with hot reload (coming in Phase 2)
docker-compose up frontend-dev
```

### Traditional Setup
```bash
npm install
npm run dev
# Visit http://localhost:3005
```

## Docker Architecture

### Production Container
- **Image Size**: ~210MB (optimized multi-stage build)
- **Base Image**: node:18-alpine
- **Port**: 3005
- **Health Check**: `/api/health`

### Key Docker Files
- `Dockerfile` - Production multi-stage build
- `.dockerignore` - Excludes unnecessary files from build
- `Dockerfile.dev` - Development container (Phase 2)
- `docker-compose.yml` - Full stack orchestration (Phase 2)

## Development Commands

### Docker Commands
```bash
# Build production image
docker build -t sigmasight-frontend .

# Run production container
docker run -d -p 3005:3005 --name frontend sigmasight-frontend

# Check container health
curl http://localhost:3005/api/health

# View container logs
docker logs frontend

# Stop and remove container
docker stop frontend && docker rm frontend
```

### NPM Commands
```bash
npm run dev       # Development server (port 3005)
npm run build     # Production build
npm run start     # Production server
npm run lint      # ESLint check
npm run type-check # TypeScript check
```

## Environment Variables

### Required for Production
```env
NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_GPT_AGENT_URL=http://localhost:8787
NEXT_PUBLIC_ENABLE_GPT_FEATURES=true
NEXT_PUBLIC_ENABLE_BACKEND_INTEGRATION=true
```

### Docker Build Args
```bash
docker build \
  --build-arg NEXT_PUBLIC_BACKEND_API_URL=http://backend:8000/api/v1 \
  --build-arg NEXT_PUBLIC_GPT_AGENT_URL=http://gpt-agent:8787 \
  -t sigmasight-frontend .
```

## Architecture

### Tech Stack
- **Framework**: Next.js 14.2.5 (App Router)
- **UI**: React 18.3.1 + TailwindCSS
- **State**: Zustand
- **Types**: TypeScript (strict mode)
- **Testing**: Vitest + Playwright

### Project Structure
```
frontend/
├── app/              # Next.js App Router pages
│   ├── (landing)/    # Public marketing pages
│   ├── (app)/        # Authenticated app pages
│   └── api/          # API routes (health, proxy)
├── src/
│   ├── components/   # React components
│   ├── services/     # API clients & services
│   ├── stores/       # Zustand state stores
│   └── utils/        # Utility functions
├── public/           # Static assets
├── Dockerfile        # Production container
└── .dockerignore     # Docker build exclusions
```

### Key Features
- Portfolio data visualization
- Real-time market data
- AI chat assistant (V1.1 in progress)
- Authentication via JWT
- Responsive design

## Troubleshooting

### Docker Build Issues
```bash
# Clear Docker cache and rebuild
docker build --no-cache -t sigmasight-frontend .

# Check build logs
docker build --progress=plain -t sigmasight-frontend .
```

### TypeScript Errors
- Ensure `downlevelIteration: true` in tsconfig.json
- Run `npm run type-check` to validate

### Port Conflicts
```bash
# Use different port
docker run -p 3006:3005 sigmasight-frontend
```

## Development Status

### Phase 1 ✅ Complete
- Basic Docker containerization
- Production-ready image
- Health checks
- TypeScript fixes

### Phase 2 🚧 In Progress
- Development container with hot reload
- Docker Compose integration
- Full stack orchestration

### Phase 3 📋 Planned
- CI/CD pipeline
- Kubernetes deployment
- Performance optimization

## Dependencies

### Core
- Next.js 14.2.5
- React 18.3.1
- TypeScript 5.5.4
- TailwindCSS 3.4.7

### Docker Requirements
- Docker Desktop 4.0+
- Docker Compose 2.0+ (for development)

## Contributing

1. Create feature branch from `main`
2. Test with Docker build
3. Ensure health check passes
4. Submit PR with Docker test results

## License

Proprietary - SigmaSight