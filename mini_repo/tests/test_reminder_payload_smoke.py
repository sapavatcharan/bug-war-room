"""Regression: JSON payload path uses same scheduling core (naive ISO avoids tz bug)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from service import schedule_reminder_from_payload


def test_schedule_from_payload_z_suffix_ok():
    """Use Z so parser output stays comparable to UTC-aware scheduler windows."""
    out = schedule_reminder_from_payload(
        {"fire_at": "2030-01-01T12:00:00Z", "cadence_hours": 1, "tenant_id": "acme"}
    )
    assert out["status"] in ("scheduled", "deferred")
