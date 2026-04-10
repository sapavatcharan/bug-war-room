"""JSON body normalization for reminder requests."""

from __future__ import annotations

from typing import Any

from config import DEFAULT_CADENCE_HOURS
from models import ReminderDispatchRequest


def build_reminder_request(body: dict[str, Any]) -> ReminderDispatchRequest:
    """Map a JSON dict to a dispatch request (raises KeyError if required keys missing)."""
    fire_at = str(body["fire_at"])
    cadence = int(body.get("cadence_hours", DEFAULT_CADENCE_HOURS))
    tenant = body.get("tenant_id")
    return ReminderDispatchRequest(
        fire_at_iso=fire_at,
        cadence_hours=cadence,
        tenant_id=str(tenant) if tenant is not None else None,
    )
