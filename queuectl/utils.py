"""Utility functions for QueueCTL."""

import json
from datetime import datetime
from typing import Dict, Any


def parse_json_input(json_str: str) -> Dict[str, Any]:
    """Parse JSON string input from CLI."""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON input: {e}")


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.utcnow().isoformat() + "Z"


def calculate_next_retry_time(attempts: int, backoff_base: int) -> str:
    """Calculate next retry time using exponential backoff.
    
    Formula: delay = base ^ attempts seconds
    """
    delay_seconds = backoff_base ** attempts
    next_retry = datetime.utcnow()
    from datetime import timedelta
    next_retry += timedelta(seconds=delay_seconds)
    return next_retry.isoformat() + "Z"

