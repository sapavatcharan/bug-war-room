"""Parse user-supplied timestamps for the reminder service."""

from __future__ import annotations

from datetime import datetime


def parse_user_datetime(raw: str) -> datetime:
    """Return a datetime from ISO-8601 input.

    Strings ending with ``Z`` are treated as UTC and return timezone-aware datetimes.
    """
    s = raw.strip()
    if s.endswith("Z"):
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    return datetime.fromisoformat(s)
