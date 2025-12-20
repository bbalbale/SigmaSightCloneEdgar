#!/bin/sh
set -e

# Transform DATABASE_URL from postgresql:// to postgresql+asyncpg://
if [ -n "$DATABASE_URL" ]; then
    export DATABASE_URL=$(echo "$DATABASE_URL" | sed 's|postgresql://|postgresql+asyncpg://|')
fi

# Transform AI_DATABASE_URL from postgresql:// to postgresql+asyncpg://
if [ -n "$AI_DATABASE_URL" ]; then
    export AI_DATABASE_URL=$(echo "$AI_DATABASE_URL" | sed 's|postgresql://|postgresql+asyncpg://|')
fi

# NOTE: Migrations are run manually or via separate job
# Skipping automatic migrations to speed up startup and avoid import issues
echo "Skipping migrations - run manually if needed"

# Start uvicorn
exec uv run uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
