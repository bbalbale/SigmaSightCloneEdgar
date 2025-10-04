#!/bin/sh
set -e

# Transform DATABASE_URL from postgresql:// to postgresql+asyncpg://
if [ -n "$DATABASE_URL" ]; then
    export DATABASE_URL=$(echo "$DATABASE_URL" | sed 's|postgresql://|postgresql+asyncpg://|')
fi

# Run migrations
uv run alembic upgrade head

# Start uvicorn
exec uv run uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
