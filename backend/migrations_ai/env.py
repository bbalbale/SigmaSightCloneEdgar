"""
Alembic env.py for AI Database migrations.

This targets AiBase.metadata from app.models.ai_models.
Uses AI_DATABASE_URL if set, otherwise falls back to DATABASE_URL.
"""
from logging.config import fileConfig
import os
from sqlalchemy import create_engine
from alembic import context

from app.models.ai_models import AiBase

config = context.config

# Get database URL - prefer AI_DATABASE_URL, fallback to DATABASE_URL
db_url = os.getenv("AI_DATABASE_URL") or os.getenv("DATABASE_URL", "")
# Use sync driver for alembic
db_url = db_url.replace("+asyncpg", "").replace("postgresql+asyncpg", "postgresql")
config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target the AI models metadata (AiBase, not Base)
target_metadata = AiBase.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = create_engine(config.get_main_option("sqlalchemy.url"))
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
