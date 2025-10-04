# Railway Dockerfile for SigmaSight Backend
FROM python:3.11-slim

# Install PostgreSQL client for psycopg2
RUN apt-get update && apt-get install -y postgresql-client libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install uv

# Set working directory
WORKDIR /app/backend

# Copy only backend directory
COPY backend/ .

# Install dependencies
RUN uv sync

# Run migrations (will fail gracefully if DB not ready)
RUN uv run alembic upgrade head || true

# Expose port
EXPOSE 8000

# Start the application (Railway provides PORT environment variable)
CMD uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT
