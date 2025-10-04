# SigmaSight Backend

FastAPI-based portfolio risk analytics platform with 8 calculation engines, automated batch processing, and AI-powered chat interface.

## Quick Start

### Development (Local)
```bash
# Start PostgreSQL
docker-compose up -d

# Run migrations
uv run alembic upgrade head

# Seed demo data
uv run python scripts/database/seed_database.py

# Start development server
uv run python run.py
```

Backend runs at: http://localhost:8000
API Docs: http://localhost:8000/docs

### Production (Docker)

**Build:**
```bash
docker build -t sigmasight-backend:prod .
```

**Run:**
```bash
docker run -d -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@host:port/db" \
  -e SECRET_KEY="your-secret-key" \
  -e POLYGON_API_KEY="your-key" \
  -e FMP_API_KEY="your-key" \
  -e OPENAI_API_KEY="your-key" \
  sigmasight-backend:prod
```

**Deploy to Railway:**
```bash
railway link
railway up --detach
```

## Features

- **8 Calculation Engines**: Greeks, Factor Analysis, Correlations, Market Risk, Stress Testing, etc.
- **Batch Processing**: Automated daily calculations with APScheduler
- **AI Chat**: OpenAI Responses API integration with SSE streaming
- **Demo Data**: 3 portfolios, 75 positions, ready for testing
- **Async-First**: SQLAlchemy 2.0 async with asyncpg driver
- **Auto Migrations**: Alembic runs on container startup

## Environment Variables

Required:
- `DATABASE_URL` - PostgreSQL connection (auto-transformed to asyncpg)
- `SECRET_KEY` - JWT secret key
- `POLYGON_API_KEY` - Market data API
- `FMP_API_KEY` - Financial Modeling Prep API

Optional:
- `OPENAI_API_KEY` - AI chat functionality
- `FRED_API_KEY` - Treasury rates
- `PORT` - Server port (default: 8000)

## Documentation

- **Complete README**: See `/README.md` at repository root
- **API Reference**: `/docs` endpoint when server is running
- **Codebase Guide**: `CLAUDE.md` for AI agents and developers
