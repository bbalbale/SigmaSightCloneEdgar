"""
Thin wrapper around the authoritative calculation clearing script.

The script already implements all destructive cleanup (analytics tables,
soft-deleted positions, duplicate positions, equity resets). Exposing it
through this module keeps FastAPI endpoints and Railway scripts decoupled
from the script's path/import quirks.
"""
from datetime import date
from typing import Optional, Dict, Any

from scripts.database.clear_calculation_data import (
    clear_calculations_comprehensive as script_clear_calculations,
)

DEFAULT_CLEAR_START_DATE = date(2000, 1, 1)


async def clear_calculations_comprehensive(
    db,
    start_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Invoke the authoritative script logic with the given session.

    Args:
        db: AsyncSession provided by FastAPI dependency
        start_date: Optional date from which to clear analytics (defaults to Jan 1, 2000)

    Returns:
        Dict[str, Any]: statistics from the script (table counts, cleanup totals)
    """
    start = start_date or DEFAULT_CLEAR_START_DATE
    return await script_clear_calculations(db, start, dry_run=False)
