"""
Lightweight telemetry sink for batch-processing metrics.

This module provides a single `record_metric` helper that forwards events to
standard logging. The implementation is intentionally simple so we can swap in
Grafana, Prometheus, or a database sink later without rewriting callers.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.logging import get_logger


logger = get_logger(__name__)


def record_metric(
    event_name: str,
    payload: Optional[Dict[str, Any]] = None,
    *,
    source: str = "batch_orchestrator",
) -> None:
    """
    Emit a structured telemetry event.

    Args:
        event_name: Metric identifier (e.g., "phase_start", "phase_result").
        payload: Optional dictionary of metric fields.
        source: Logical component emitting the event.
    """
    envelope = {
        "event": event_name,
        "source": source,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload or {},
    }
    logger.info("telemetry %s", json.dumps(envelope, separators=(",", ":")))

