#!/bin/bash
# Railway Migration Check and Fix Script
# This script transforms DATABASE_URL and checks/runs migrations on Railway

set -e

echo "============================================"
echo "Railway Migration Status Check"
echo "============================================"
echo ""

# Transform DATABASE_URL for async driver (same as start.sh)
if [ -n "$DATABASE_URL" ]; then
    export DATABASE_URL=$(echo "$DATABASE_URL" | sed 's|postgresql://|postgresql+asyncpg://|')
    echo "✓ DATABASE_URL transformed for asyncpg driver"
else
    echo "❌ ERROR: DATABASE_URL not set"
    exit 1
fi
echo ""

# Check current migration version
echo "Checking current migration version..."
echo "----------------------------------------"
uv run python -m alembic current
echo ""

# Check migration history (last 5)
echo "Recent migration history:"
echo "----------------------------------------"
uv run python -m alembic history --verbose | head -n 30
echo ""

# Check if we need to upgrade
echo "Checking if migrations are pending..."
echo "----------------------------------------"
uv run python -m alembic check 2>&1 || true
echo ""

# Ask if user wants to run migrations
echo "Do you want to run 'alembic upgrade head' now? (y/n)"
echo "Note: This will be automated in non-interactive mode"
echo ""
echo "Running upgrade automatically..."
uv run python -m alembic upgrade head
echo ""

echo "============================================"
echo "✓ Migration check complete"
echo "============================================"
