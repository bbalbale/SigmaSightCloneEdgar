# SigmaSight

**Portfolio Risk Analytics Platform** with AI-powered insights, real-time market data, and comprehensive financial calculations.

## Overview

SigmaSight is a full-stack portfolio analytics platform that provides:

- 🎯 **Portfolio Management** - Multi-portfolio tracking with positions and tags (strategy containers removed Oct 2025)
- 📊 **Risk Analytics** - 8 calculation engines (Greeks, Factor Analysis, Correlations, Market Risk, Stress Testing)
- 🤖 **AI Agent** - OpenAI-powered chat interface with portfolio insights and analysis
- 📈 **Real-time Data** - Market quotes, historical prices, and factor ETF tracking
- 🔄 **Batch Processing** - Automated daily calculations and portfolio snapshots
- 🎨 **Modern UI** - React-based frontend with responsive design and SSE streaming

## Tech Stack

### Backend
- **FastAPI** - Async Python web framework
- **PostgreSQL** - Database with UUID primary keys
- **SQLAlchemy 2.0** - Async ORM with Alembic migrations
- **OpenAI Responses API** - AI agent integration (not Chat Completions)
- **Market Data** - FMP (primary), Polygon (options), FRED (economic)
- **Calculations** - mibian (Greeks), custom factor analysis

### Frontend
- **React + TypeScript** - Component-based UI
- **Docker** - Containerized deployment (preferred)
- **SSE Streaming** - Real-time AI agent responses
- **Port 3005** - Development and production

### Infrastructure
- **Docker Compose** - PostgreSQL development database
- **Railway** - Production deployment (planned)
- **Alembic** - Database schema migrations
- **UV** - Python package management

## Quick Start

### Prerequisites

- **Docker Desktop** - For PostgreSQL database
- **Python 3.11+** - For backend
- **Node.js 18+** - For frontend (if not using Docker)
- **UV** - Python package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

### 1. Clone Repository

```bash
git clone <repository-url>
cd SigmaSight-BE
```

### 2. Start Backend

```bash
# Start PostgreSQL
docker-compose up -d

# Navigate to backend
cd backend

# Set up environment
cp .env.example .env
# Edit .env with your API keys (POLYGON_API_KEY, FMP_API_KEY, etc.)

# Run migrations
uv run alembic upgrade head

# Seed demo data (3 portfolios, 75 positions)
uv run python scripts/database/seed_database.py

# Start backend server
uv run python run.py
```

Backend will be available at: **http://localhost:8000**
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### 3. Start Frontend

#### Option A: Docker (Recommended)

```bash
cd frontend
docker build -t sigmasight-frontend .
docker run -d -p 3005:3005 --name frontend sigmasight-frontend
```

#### Option B: npm

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at: **http://localhost:3005**

### 4. Login

Use one of the demo accounts:
- Email: `demo_individual@sigmasight.com`
- Email: `demo_hnw@sigmasight.com`
- Email: `demo_hedgefundstyle@sigmasight.com`
- Password: `demo12345` (all accounts)

## Project Structure

```
SigmaSight-BE/
├── backend/                 # FastAPI backend
│   ├── app/                 # Main application code
│   │   ├── api/v1/          # REST API endpoints
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── services/        # Business logic layer
│   │   ├── calculations/    # Financial calculation engines
│   │   ├── batch/           # Batch processing framework
│   │   └── agent/           # OpenAI Responses API integration
│   ├── scripts/             # Utility scripts
│   │   ├── database/        # Seeding and database utilities
│   │   ├── batch_processing/# Batch job runners
│   │   ├── monitoring/      # System monitoring
│   │   └── testing/         # Test scripts
│   ├── _docs/               # Documentation
│   │   ├── reference/       # API reference
│   │   └── requirements/    # Product requirements
│   ├── _guides/             # Workflow guides
│   └── alembic/             # Database migrations
├── frontend/                # React frontend
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   └── services/        # API clients
│   └── Dockerfile           # Frontend containerization
├── CLAUDE.md                # AI agent instructions (detailed)
└── README.md                # This file

```

## Development Workflow

### Backend Development

```bash
cd backend

# Run development server (auto-reload)
uv run python run.py

# Run tests
uv run pytest

# Run batch calculations manually
uv run python scripts/batch_processing/run_batch_orchestrator.py

# Check database status
uv run python scripts/verification/verify_setup.py

# Create new migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head
```

### Frontend Development

```bash
cd frontend

# Development mode (npm)
npm run dev

# Build for production
npm run build

# Docker rebuild
docker stop frontend && docker rm frontend
docker build -t sigmasight-frontend .
docker run -d -p 3005:3005 --name frontend sigmasight-frontend
```

### Code Quality

```bash
# Format code
uv run black .
uv run isort .

# Lint
uv run flake8 app/

# Type checking
uv run mypy app/
```

## Key Features

### Portfolio Management
- Create and manage multiple portfolios
- Track positions (equities, options, private investments)
- Tag-based organization and filtering
- Target price tracking and alerts

### Analytics & Calculations
1. **Position Greeks** - Delta, Gamma, Theta, Vega for options
2. **Factor Exposure** - 8-factor risk model analysis
3. **Correlations** - Position and factor correlation matrices
4. **Market Risk** - Scenario-based risk analysis
5. **Stress Testing** - 18 predefined stress scenarios
6. **Portfolio Snapshots** - Daily portfolio state capture
7. **Diversification Score** - Portfolio diversification metrics
8. **P&L Tracking** - Historical performance analysis

### AI Agent (OpenAI Responses API)
- Natural language portfolio queries
- SSE streaming responses
- Tool-based function calling
- Context-aware analysis
- Portfolio recommendations

### Market Data
- Real-time quotes (FMP, Polygon)
- Historical prices and OHLCV data
- Factor ETF prices (8 factors)
- Treasury rates (FRED)
- Options data (Polygon)

## API Endpoints

### Authentication (5 endpoints)
- `POST /api/v1/auth/login` - JWT token generation
- `POST /api/v1/auth/logout` - Session invalidation
- `POST /api/v1/auth/refresh` - Token refresh
- `GET /api/v1/auth/me` - Current user info
- `POST /api/v1/auth/register` - User registration

### Data (10 endpoints)
- Portfolio complete snapshots
- Position details with P&L
- Historical prices
- Real-time quotes
- Factor ETF prices
- Data quality metrics

### Analytics (7 endpoints)
- Portfolio metrics
- Diversification score
- Risk analytics
- Performance tracking

### Chat (6 endpoints)
- Message send (SSE streaming)
- Conversation management
- Message history

### Tags & Target Prices
- Tag management (10 endpoints)
- Position tagging (5 endpoints)
- Target price tracking (10 endpoints)

**Full API Reference**: See `backend/_docs/reference/API_REFERENCE_V1.4.6.md`

## Environment Variables

Create a `.env` file in the `backend/` directory:

```bash
# Database (Required)
DATABASE_URL=postgresql+asyncpg://sigmasight:sigmasight_dev@localhost:5432/sigmasight_db

# API Keys (Required for market data)
POLYGON_API_KEY=your_polygon_key
FMP_API_KEY=your_fmp_key
FRED_API_KEY=your_fred_key

# OpenAI (Required for AI agent)
OPENAI_API_KEY=your_openai_key

# JWT (Required)
SECRET_KEY=your_jwt_secret_key

# Optional
MODEL_DEFAULT=gpt-4o-mini-2024-07-18
LOG_LEVEL=INFO
```

## Demo Data

The system includes comprehensive demo data:

### 3 Demo Portfolios
1. **Balanced Individual Investor** - 25 positions
2. **High Net Worth Investor** - 23 positions
3. **Hedge Fund Style** - 27 positions (includes options)

### Additional Seed Data
- **8 Factor Definitions** - Risk factor model
- **Security Master Data** - Classification metadata
- **18 Stress Scenarios** - Predefined stress tests
- **105 Target Prices** - 35 symbols × 3 portfolios

**Seeding Command**: `uv run python scripts/database/seed_database.py`

## Testing

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_market_data_service.py

# Run with coverage
uv run pytest --cov=app

# Manual API testing
./scripts/testing/test_api_endpoints.sh
```

## Documentation

### For Developers
- **[CLAUDE.md](CLAUDE.md)** - Comprehensive codebase reference for AI agents
- **[backend/TODO3.md](backend/TODO3.md)** - Current phase development (API Integration)
- **[backend/_docs/reference/API_REFERENCE_V1.4.6.md](backend/_docs/reference/API_REFERENCE_V1.4.6.md)** - Complete API documentation
- **[backend/_guides/](backend/_guides/)** - Workflow guides (initial setup, daily operations)

### For AI Agents
- **[CLAUDE.md](CLAUDE.md)** - Primary reference with architecture, patterns, and best practices
- **[AGENTS.md](AGENTS.md)** - Agent-specific guidelines

### Architecture Docs
- **[backend/_docs/requirements/](backend/_docs/requirements/)** - Product requirements and specifications
- **[backend/scripts/README.md](backend/scripts/README.md)** - Scripts documentation

## Current Status

### Completed ✅
- **Phase 1**: Batch Processing Framework (8 calculation engines)
- **Phase 2**: Automated Scheduling (APScheduler with graceful shutdown)
- **Phase 3.0**: API Development (46 endpoints across 6 categories)
- **Tagging System**: Position-based tagging (October 2025)
- **AI Agent**: OpenAI Responses API integration with SSE streaming

### In Progress 🚧
- Frontend UI enhancements
- Additional analytics endpoints
- Performance optimizations

### Known Issues ⚠️
- Some calculation engines require additional market data
- Stress test results table pending (documented in backend/_archive/todos/TODO1.md)
- Mock data fallbacks for unavailable calculations

## Deployment

### Development (Local)
- **Backend**: `uv run python run.py` → http://localhost:8000
- **Frontend**: `npm run dev` → http://localhost:3005 (or Docker)
- **Database**: `docker-compose up -d` → PostgreSQL on localhost:5432

### Production (Docker) ✅ Ready

**Build Docker Image:**
```bash
docker build -t sigmasight-backend:prod .
```

**Run Locally:**
```bash
docker run -d -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@host:port/db" \
  -e SECRET_KEY="$(openssl rand -hex 32)" \
  -e POLYGON_API_KEY="your-key" \
  -e FMP_API_KEY="your-key" \
  -e OPENAI_API_KEY="your-key" \
  sigmasight-backend:prod
```

**Deploy to Railway:**
```bash
# Install Railway CLI
brew install railway

# Login and link
railway login
railway link

# Deploy
railway up --detach
```

**Deploy to Other Providers:**
- **AWS ECS/Fargate**: Push to ECR → Create ECS service
- **Google Cloud Run**: `gcloud run deploy --image ...`
- **DigitalOcean**: Connect GitHub → Dockerfile auto-detected
- **Heroku**: `heroku container:push web && heroku container:release web`
- **Azure Container Apps**: `az containerapp create --image ...`

### Production Environment Variables

**Required:**
- `DATABASE_URL` - PostgreSQL connection (auto-transformed to asyncpg)
- `SECRET_KEY` - JWT secret key
- `POLYGON_API_KEY` - Market data
- `FMP_API_KEY` - Financial data

**Optional:**
- `OPENAI_API_KEY` - AI chat
- `FRED_API_KEY` - Treasury rates
- `PORT` - Server port (default: 8000)

**Container Features:**
- ✅ Automatic DATABASE_URL transformation (`postgresql://` → `postgresql+asyncpg://`)
- ✅ Alembic migrations run on startup
- ✅ Health check endpoint: `/health`
- ✅ FastAPI docs: `/docs`
- ✅ Tested and verified locally

**Deployment Plan**: See `backend/_docs/requirements/Dockerization_and_Deployment_Plan_v1.4.md`

## Contributing

### Development Guidelines
1. Always use async patterns for database operations
2. Create Alembic migrations for schema changes
3. Test with existing demo data (don't create new test data)
4. Implement graceful degradation for missing calculation data
5. Follow existing code patterns (see CLAUDE.md Part II)
6. Update documentation when discovering new patterns

### Git Workflow
```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "feat: description of changes"

# Push and create PR
git push origin feature/your-feature-name
```

## Support & Resources

- **API Documentation**: http://localhost:8000/docs (when backend running)
- **Issue Tracker**: GitHub Issues
- **Codebase Reference**: [CLAUDE.md](CLAUDE.md)
- **API Reference**: [backend/_docs/reference/API_REFERENCE_V1.4.6.md](backend/_docs/reference/API_REFERENCE_V1.4.6.md)

## License

Proprietary - All rights reserved

---

**Last Updated**: October 4, 2025
**Version**: 1.4 (Phase 3.0 - API Integration Complete)
