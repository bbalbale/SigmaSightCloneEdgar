#!/bin/bash
# Migration script for Railway deployment
# Run this script on Railway to execute Alembic migrations

set -e  # Exit on error

echo "Starting database migrations..."

# Set migration mode to prevent async engine creation
export MIGRATION_MODE=1

# Run Alembic migrations
alembic upgrade head

echo "Migrations completed successfully!"
