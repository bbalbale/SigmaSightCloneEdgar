"""
Database connection utilities that work in both local (async) and Railway (sync) environments.

Usage in scripts:
    from app.core.db_utils import get_sync_connection, is_railway_environment

    # For Railway scripts that need sync connections:
    with get_sync_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users")
            rows = cur.fetchall()

    # Or use the context manager for auto-commit:
    with get_sync_cursor() as cur:
        cur.execute("CREATE TABLE IF NOT EXISTS ...")
"""

import os
from contextlib import contextmanager
from typing import Generator, Any


def is_railway_environment() -> bool:
    """
    Detect if we're running on Railway.

    Railway sets several environment variables:
    - RAILWAY_ENVIRONMENT
    - RAILWAY_PROJECT_ID
    - RAILWAY_SERVICE_ID

    Also, Railway's DATABASE_URL typically doesn't have the +asyncpg suffix.
    """
    # Check for Railway-specific env vars
    if os.environ.get("RAILWAY_ENVIRONMENT"):
        return True
    if os.environ.get("RAILWAY_PROJECT_ID"):
        return True
    if os.environ.get("RAILWAY_SERVICE_ID"):
        return True

    # Check if DATABASE_URL lacks asyncpg (Railway pattern)
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url.startswith("postgresql://") and "+asyncpg" not in db_url:
        # Could be Railway or a plain postgres URL
        # Check if it's an internal Railway URL
        if "railway.internal" in db_url or "rlwy.net" in db_url:
            return True

    return False


def get_sync_database_url() -> str:
    """
    Get a psycopg2-compatible database URL.

    Handles both:
    - Local: postgresql+asyncpg://... -> postgresql://...
    - Railway: postgresql://... (already correct)
    """
    database_url = os.environ.get("DATABASE_URL", "")

    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    # Remove asyncpg prefix if present (local development)
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    return database_url


def get_sync_connection():
    """
    Get a synchronous psycopg2 database connection.

    Works in both local and Railway environments.

    Usage:
        conn = get_sync_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        finally:
            conn.close()

    Or use get_sync_cursor() for a context manager that handles cleanup.
    """
    try:
        import psycopg2
    except ImportError:
        raise ImportError(
            "psycopg2 is required for sync database connections. "
            "Install with: pip install psycopg2-binary"
        )

    database_url = get_sync_database_url()
    return psycopg2.connect(database_url)


@contextmanager
def get_sync_cursor(autocommit: bool = True) -> Generator[Any, None, None]:
    """
    Context manager for sync database operations with automatic cleanup.

    Args:
        autocommit: If True, each statement is committed immediately.
                   If False, you must call conn.commit() manually.

    Usage:
        with get_sync_cursor() as cur:
            cur.execute("CREATE TABLE IF NOT EXISTS ...")
            cur.execute("INSERT INTO ...")
        # Connection is automatically closed

        # For transactions:
        with get_sync_cursor(autocommit=False) as cur:
            cur.execute("INSERT INTO ...")
            cur.execute("UPDATE ...")
            cur.connection.commit()  # Commit the transaction
    """
    conn = get_sync_connection()
    conn.autocommit = autocommit
    cur = conn.cursor()

    try:
        yield cur
    finally:
        cur.close()
        conn.close()


@contextmanager
def get_sync_connection_context() -> Generator[Any, None, None]:
    """
    Context manager for sync database connection with automatic cleanup.

    Usage:
        with get_sync_connection_context() as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users")
    """
    conn = get_sync_connection()
    try:
        yield conn
    finally:
        conn.close()


# SQLAlchemy sync session for scripts that need ORM models
@contextmanager
def get_sync_session() -> Generator[Any, None, None]:
    """
    Get a synchronous SQLAlchemy session for ORM operations.

    Works in both local and Railway environments.
    Use this when you need to query using SQLAlchemy models.

    Usage:
        from app.core.db_utils import get_sync_session
        from app.models.users import Portfolio

        with get_sync_session() as db:
            result = db.execute(select(Portfolio))
            portfolios = result.scalars().all()
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    database_url = get_sync_database_url()
    engine = create_engine(database_url)

    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


# For backwards compatibility and convenience
def execute_sync_query(query: str, params: tuple = None, fetch: bool = False) -> list | None:
    """
    Execute a single query synchronously.

    Args:
        query: SQL query to execute
        params: Query parameters (optional)
        fetch: If True, return fetched results

    Returns:
        List of rows if fetch=True, else None

    Usage:
        # Simple query
        execute_sync_query("CREATE TABLE IF NOT EXISTS foo (id INT)")

        # Query with parameters
        execute_sync_query("INSERT INTO foo VALUES (%s)", (1,))

        # Fetch results
        rows = execute_sync_query("SELECT * FROM foo", fetch=True)
    """
    with get_sync_cursor() as cur:
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)

        if fetch:
            return cur.fetchall()
        return None
