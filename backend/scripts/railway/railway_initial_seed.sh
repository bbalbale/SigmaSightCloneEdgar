#!/bin/bash
# Railway Initial Database Seeding Script
# Adapted from BACKEND_INITIAL_COMPLETE_WORKFLOW_GUIDE.md
#
# This script performs the complete first-time database setup for Railway deployment:
# 1. Checks for existing data
# 2. Seeds demo accounts and portfolios
# 3. Validates setup
# 4. Seeds target prices
# 5. Runs batch processing to populate all calculation data
#
# Usage: railway ssh bash scripts/railway_initial_seed.sh

set -e  # Exit on any error

echo "============================================"
echo "SigmaSight Railway - Initial Database Setup"
echo "============================================"
echo ""

# Transform DATABASE_URL for async driver (same as start.sh)
if [ -n "$DATABASE_URL" ]; then
    export DATABASE_URL=$(echo "$DATABASE_URL" | sed 's|postgresql://|postgresql+asyncpg://|')
    echo "✓ DATABASE_URL transformed for asyncpg driver"
fi
echo ""

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Check for existing data
echo -e "${YELLOW}[Step 1/6] Checking for existing data...${NC}"
if uv run python scripts/database/check_database_content.py 2>&1 | grep -q "portfolios found"; then
    echo -e "${RED}WARNING: Existing data found!${NC}"
    echo "This script will DELETE all existing data and reseed."
    echo "If this is not a fresh Railway deployment, press Ctrl+C to cancel."
    echo ""
    echo "Waiting 5 seconds before proceeding..."
    sleep 5
fi

# Step 2: Seed database with demo accounts and portfolios
echo ""
echo -e "${YELLOW}[Step 2/6] Seeding database with demo data...${NC}"
echo "Creating:"
echo "  - 3 Demo accounts (demo_individual, demo_hnw, demo_hedgefundstyle)"
echo "  - 63 positions across 3 portfolios"
echo "  - 8 Factor definitions"
echo "  - 18 Stress test scenarios"
echo "  - Security master data"
echo "  - Initial price cache"
echo ""

# Use seed_database.py (safer than reset) since Railway DB is fresh
if uv run python scripts/database/seed_database.py; then
    echo -e "${GREEN}✓ Demo data seeded successfully${NC}"
else
    echo -e "${RED}✗ Failed to seed demo data${NC}"
    exit 1
fi

# Step 3: Validate setup
echo ""
echo -e "${YELLOW}[Step 3/6] Validating database setup...${NC}"
if uv run python scripts/validation/verify_setup.py; then
    echo -e "${GREEN}✓ Database validation passed${NC}"
else
    echo -e "${RED}✗ Database validation failed${NC}"
    echo "Continuing anyway - some failures may be expected..."
fi

# Step 4: Verify portfolio IDs
echo ""
echo -e "${YELLOW}[Step 4/6] Verifying deterministic portfolio IDs...${NC}"
uv run python scripts/list_portfolios.py

# Step 5: Seed target prices (optional but recommended)
echo ""
echo -e "${YELLOW}[Step 5/5] Seeding target prices...${NC}"
echo "Creating 105 target price records (35 symbols × 3 portfolios)"
echo ""

if [ -f "data/target_prices_import.csv" ]; then
    if uv run python scripts/data_operations/populate_target_prices_via_service.py \
        --csv-file data/target_prices_import.csv --execute; then
        echo -e "${GREEN}✓ Target prices seeded successfully${NC}"
    else
        echo -e "${YELLOW}⚠ Target prices seeding failed (non-critical)${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Target prices CSV not found - skipping${NC}"
fi

# Final summary
echo ""
echo "============================================"
echo -e "${GREEN}✓ Railway Initial Setup Complete!${NC}"
echo "============================================"
echo ""
echo "Demo Accounts Created:"
echo "  - demo_individual@sigmasight.com"
echo "  - demo_hnw@sigmasight.com"
echo "  - demo_hedgefundstyle@sigmasight.com"
echo "  Password (all): demo12345"
echo ""
echo "Portfolio IDs (deterministic):"
echo "  - Individual: 1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe"
echo "  - HNW: e23ab931-a033-edfe-ed4f-9d02474780b4"
echo "  - Hedge Fund: fcd71196-e93e-f000-5a74-31a9eead3118"
echo ""
echo "Next steps:"
echo "  1. Test API health: curl https://sigmasight-be-production.up.railway.app/health"
echo "  2. Test login:"
echo "     curl -X POST https://sigmasight-be-production.up.railway.app/api/v1/auth/login \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"email\":\"demo_individual@sigmasight.com\",\"password\":\"demo12345\"}'"
echo "  3. View API docs: https://sigmasight-be-production.up.railway.app/docs"
echo ""
echo "For daily operations, see: backend/_guides/BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md"
echo "============================================"
