# Railway Dockerfile for SigmaSight Backend - v2
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install UV
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy backend files
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync

# Copy rest of backend
COPY backend/ ./

# Expose port
EXPOSE 8000

# Start command
CMD sh -c "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
