# Database Management Scripts

Scripts for database initialization, seeding, and management.

## Key Scripts

### Setup & Initialization
- **init_database.py** - Initialize database schema
- **setup_dev_database_alembic.py** - Setup development database with Alembic migrations
- **setup_minimal_demo.py** - Create minimal demo environment

### Seeding
- **seed_database.py** - Main database seeding script
- **reset_and_seed.py** - Complete reset and reseed (DESTRUCTIVE)
- **seed_stress_scenarios.py** - Seed stress test scenarios
- **create_sample_positions.py** - Create sample portfolio positions

### Inspection
- **check_database_content.py** - Verify database contents
- **check_tables.py** - Check table existence
- **list_portfolios.py** - List all portfolios with details
- **list_users.py** - List all system users

## Common Commands

### Reset and seed database (DESTRUCTIVE):
```bash
cd backend
uv run python scripts/database/reset_and_seed.py
```

### Seed demo data only:
```bash
uv run python scripts/database/seed_database.py
```

### Check database content:
```bash
uv run python scripts/database/check_database_content.py
```

### List portfolios:
```bash
uv run python scripts/database/list_portfolios.py
```

## Demo Data

Seeds 3 demo portfolios with 63 positions total:
- Demo Individual Investor Portfolio
- Demo High Net Worth Investor Portfolio  
- Demo Institutional Investor Portfolio

All demo users use password: `demo12345`