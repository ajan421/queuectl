"""Utility functions for QueueCTL."""

import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional


def parse_json_input(json_str: str) -> Dict[str, Any]:
    """Parse JSON string input from CLI."""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON input: {e}")


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware in UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.utcnow().replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_timestamp(value: Any) -> str:
    """Normalize a timestamp input to ISO format with UTC timezone."""
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = _ensure_utc(value)
    elif isinstance(value, str):
        try:
            if value.endswith("Z"):
                value = value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"Invalid timestamp format: {value}") from exc
        dt = _ensure_utc(dt)
    else:
        raise ValueError(f"Unsupported timestamp value: {value}")
    return dt.isoformat().replace("+00:00", "Z")


def parse_iso_timestamp(value: Optional[str]) -> Optional[datetime]:
    """Parse ISO timestamp stored in the database."""
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except ValueError:
        return None


def calculate_next_retry_time(attempts: int, backoff_base: int) -> str:
    """Calculate next retry time using exponential backoff.
    
    Formula: delay = base ^ attempts seconds
    """
    delay_seconds = backoff_base ** attempts
    next_retry = datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(seconds=delay_seconds)
    return next_retry.isoformat().replace("+00:00", "Z")

