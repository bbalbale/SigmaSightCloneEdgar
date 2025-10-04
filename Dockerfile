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

# Copy backend dependency files
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
RUN uv sync

# Copy rest of backend
COPY backend/ ./

# Make start script executable
RUN chmod +x /app/start.sh

# Expose port
EXPOSE 8000

# Start command
CMD ["/app/start.sh"]
