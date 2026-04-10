"""Inbound reminder domain types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReminderDispatchRequest:
    """Validated reminder payload from the edge API."""

    fire_at_iso: str
    cadence_hours: int = 24
    tenant_id: str | None = None
