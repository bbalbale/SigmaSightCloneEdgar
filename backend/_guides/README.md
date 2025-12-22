# SigmaSight Backend

SigmaSight is a sophisticated portfolio analytics platform designed for options traders, providing real-time risk metrics, portfolio-level Greeks calculations, and comprehensive position management.

**Version**: 1.4.4  
**Status**: Phase 3.0 - API Development (30% complete)
**API Status**: Raw Data APIs 100% operational  
**Tech Stack**: FastAPI, PostgreSQL, Python 3.11+

## 📖 Setup Guides

- **Windows Users**: See [WINDOWS_SETUP_GUIDE.md](WINDOWS_SETUP_GUIDE.md) for detailed instructions
- **Quick Reference**: See [QUICK_START_WINDOWS.md](../QUICK_START_WINDOWS.md) for a one-page guide
- **Mac Users**: See [MAC_INSTALL_GUIDE.md](MAC_INSTALL_GUIDE.md) for detailed instructions
- **Linux Users**: Continue reading below
- **🤖 AI Agents**: See [../AI_AGENT_REFERENCE.md](../AI_AGENT_REFERENCE.md) and [../CLAUDE.md](../CLAUDE.md) for comprehensive codebase reference

FastAPI backend for SigmaSight portfolio risk management platform.

## Features

- **Portfolio Management**: CSV upload, position tracking, and portfolio analytics
- **Risk Analytics**: Factor exposures, risk metrics, and options Greeks
- **Market Data**: Integration with Polygon.io and YFinance APIs
- **Authentication**: JWT-based user authentication
- **Batch Processing**: Automated market data updates and calculations
- **Modern Stack**: FastAPI, PostgreSQL, and UV package manager

## 🌊 Using Windsurf IDE? 

**For the best development experience with AI assistance:**

👉 **[See WINDSURF_SETUP.md](./WINDSURF_SETUP.md)** for Windsurf-specific setup instructions with Cascade AI integration.

---

## 🚀 Quick Setup Guide (Non-Technical)

### Step 1: Install Prerequisites

#### Install Python 3.11+
**Windows:**
1. Download Python from https://python.org/downloads/
2. Run installer, check "Add Python to PATH"
3. Verify: Open Command Prompt, type `python --version`

**Mac:**
1. Install Homebrew: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
2. Install Python: `brew install python@3.11`
3. Verify: `python3 --version`

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip
```

#### Install UV Package Manager
**All Platforms:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

After installation, restart your terminal and verify: `uv --version`

### Step 2: Get the Code

1. **Clone the repository:**
```bash
git clone https://github.com/elliottng/SigmaSight-BE.git
cd SigmaSight-BE/backend
```

2. **Verify you're in the right directory:**
   - You should see files like `pyproject.toml`, `run.py`, `app/` folder

### Step 3: Install Dependencies

```bash
uv sync
```

This will:
- Create a virtual environment
- Install all required packages
- Set up the development environment

### Step 4: Configure Environment

1. **Copy the environment template:**
```bash
cp .env.example .env
```

**Windows (Command Prompt):**
```cmd
copy .env.example .env
```

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

2. **Edit .env file** (optional for basic testing):
   - The default values work for local development
   - You can leave it as-is for now

### Step 5: Set Up Database (Required for Full Functionality)

**Option A: Use Docker (Recommended)**

1. **Install Docker Desktop:**
   - **Mac:** `brew install --cask docker` then `open -a Docker`
   - **Windows:** Download from [docker.com](https://www.docker.com/products/docker-desktop/)
   - **Linux:** Follow [Docker installation guide](https://docs.docker.com/engine/install/)

2. **Start PostgreSQL:**
```bash
# Start PostgreSQL with Docker Compose
docker-compose up -d

# Verify it's running
docker-compose ps
```

3. **Update .env file:**
```bash
# Make sure your .env has the correct database URL:
DATABASE_URL=postgresql+asyncpg://sigmasight:sigmasight_dev@localhost:5432/sigmasight_db
```

4. **Set up database (Dual Database Migrations):**
```bash
# Run migrations for BOTH Core and AI databases
uv run alembic -c alembic.ini upgrade head        # Core DB (portfolios, positions, etc.)
uv run alembic -c alembic_ai.ini upgrade head     # AI DB (RAG, memories, feedback)
```

**Note:** The project uses a dual database architecture:
- **Core DB** (`DATABASE_URL`): Portfolios, positions, market data, chat messages
- **AI DB** (`AI_DATABASE_URL`): RAG knowledge base, user memories, feedback with pgvector

5. **Seed demo data (optional):**
```bash
uv run python scripts/database/seed_database.py
```

This creates the three demo accounts and portfolios:
- demo_individual@sigmasight.com (password: demo12345) — "Demo Individual Investor Portfolio" (16 positions)
- demo_hnw@sigmasight.com (password: demo12345) — "Demo High Net Worth Investor Portfolio" (17 positions)
- demo_hedgefundstyle@sigmasight.com (password: demo12345) — "Demo Hedge Fund Style Investor Portfolio" (30 positions)

**Option B: Use Existing PostgreSQL**
1. Update DATABASE_URL in .env file with your PostgreSQL connection
2. Set up database (dual migrations):
   ```bash
   uv run alembic -c alembic.ini upgrade head        # Core DB
   uv run alembic -c alembic_ai.ini upgrade head     # AI DB
   ```
3. Optionally seed demo data: `uv run python scripts/database/seed_database.py`

**Note:** The database is required for authentication, portfolio management, and all core features.

### Step 6: Start the Server

```bash
uv run python run.py
```

You should see output like:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Step 7: Verify Everything Works

**Option A: Run Automated Verification**
```bash
uv run python scripts/verify_setup.py
```

**Option B: Manual Verification**
1. Open browser to http://localhost:8000
2. You should see: `{"message": "SigmaSight Backend API", "version": "1.0.0"}`
3. Check API docs: http://localhost:8000/docs
4. Test health endpoint: http://localhost:8000/health

### Step 8: Test Authentication (Optional)

**Run the authentication test suite:**
```bash
uv run python scripts/test_auth.py
```

This will test:
- User registration and validation
- Login with demo users
- JWT token generation and refresh
- Protected route access
- Error handling

**Or test manually with curl:**
```bash
# Login with demo user
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "demo_individual@sigmasight.com", "password": "demo12345"}'

# Use the returned access_token to access protected endpoints
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

## ⚡ Automated Setup (Alternative)

For even easier setup, use the automated setup scripts:

**Mac/Linux:**
```bash
./setup.sh
```

**Windows:**
```cmd
setup.bat
```

These scripts will:
- Install UV if not present
- Install all dependencies
- Set up environment file
- Run verification tests
- Provide next steps

## ✅ Verification Checklist

Run this checklist to ensure identical setup:

- [ ] Python 3.11+ installed (`python --version` or `python3 --version`)
- [ ] UV package manager installed (`uv --version`)
- [ ] Docker Desktop installed and running (for database)
- [ ] Repository cloned and in correct directory
- [ ] Dependencies installed (`uv sync` completed successfully)
- [ ] Environment file created (`.env` exists with correct DATABASE_URL)
- [ ] PostgreSQL container running (`docker-compose ps` shows postgres as "Up")
- [ ] Database migrations applied (both `alembic.ini` and `alembic_ai.ini` upgrade head succeeded)
- [ ] Demo data seeded (optional: `uv run python scripts/database/seed_database.py`)
- [ ] Server starts without errors (`uv run python run.py`)
- [ ] API responds at http://localhost:8000
- [ ] API documentation loads at http://localhost:8000/docs
- [ ] Health check works at http://localhost:8000/health
- [ ] Authentication works (login with demo_individual@sigmasight.com / demo12345)
- [ ] All verification tests pass (`uv run python scripts/verify_setup.py`)

## 🔧 API Documentation

Once the server is running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 📋 Available API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `POST /api/v1/auth/login` - User authentication
- `GET /api/v1/portfolio/` - Portfolio overview
- `GET /api/v1/positions/` - Position management
- `GET /api/v1/risk/greeks` - Options Greeks
- `GET /api/v1/risk/metrics` - Risk metrics
- And 10+ more endpoints...

## 🐛 Troubleshooting

### Common Issues:

**"uv: command not found"**
- Restart your terminal after installing UV
- On Mac/Linux: `source ~/.bashrc` or `source ~/.zshrc`
- On Windows: Restart Command Prompt

**"Python version too old"**
- Ensure Python 3.11+ is installed
- Try `python3` instead of `python`

**"Port 8000 already in use"**
- Stop other servers running on port 8000
- Or change port in `run.py`: `uvicorn.run(..., port=8001)`

**Dependencies fail to install**
- Try: `uv sync --reinstall`
- Ensure internet connection is stable

**"Docker not running" or database connection errors**
- Ensure Docker Desktop is running (check system tray/menu bar)
- Run `docker-compose up -d` to start PostgreSQL
- Check container status: `docker-compose ps`
- Verify .env has correct DATABASE_URL matching docker-compose.yml

**"Alembic migration failed"**
- Check database is running: `docker-compose ps`
- Ensure .env DATABASE_URL matches docker-compose credentials
- Try: `docker-compose down` then `docker-compose up -d`
- Check logs: `docker-compose logs postgres`

### Get Help:
1. Run the verification script: `uv run python scripts/verify_setup.py`
2. Check the output for specific error messages
3. Ensure all prerequisites are properly installed

## Development

### Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── config.py        # Configuration settings
│   └── ...
├── .env                 # Environment variables
├── .env.example         # Environment template
├── pyproject.toml       # Project dependencies
├── run.py              # Development server
└── README.md
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `POLYGON_API_KEY` | Polygon.io API key | Yes |
| `SECRET_KEY` | JWT secret key | Yes |
| `DEBUG` | Enable debug mode | No |

### Development Commands

```bash
# Run development server
uv run python run.py

# Run tests
uv run pytest

# Format code
uv run black .
uv run isort .

# Type checking
uv run mypy app/

# Linting
uv run flake8 app/
```

## Deployment

This project is configured for deployment on Railway with UV package manager.

## License

MIT License