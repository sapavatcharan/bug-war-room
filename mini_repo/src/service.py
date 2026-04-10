"""Reminder scheduling entrypoint — HTTP layer hands off JSON here."""

from __future__ import annotations

from typing import Any

from parser import parse_user_datetime
from payloads import build_reminder_request
from scheduler import compute_next_window


def schedule_reminder(user_iso_ts: str, cadence_hours: int = 24) -> dict[str, str]:
    """Schedule a reminder relative to the next cadence window.

    Compares the user-provided instant with the internally computed window.
    """
    user_dt = parse_user_datetime(user_iso_ts)
    next_win = compute_next_window(cadence_hours=cadence_hours)
    if user_dt < next_win:
        return {"status": "scheduled", "next_window": next_win.isoformat()}
    return {"status": "deferred"}


def schedule_reminder_from_payload(body: dict[str, Any]) -> dict[str, str]:
    """Parse JSON payload then delegate to :func:`schedule_reminder`."""
    req = build_reminder_request(body)
    return schedule_reminder(req.fire_at_iso, cadence_hours=req.cadence_hours)
