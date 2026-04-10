"""Scheduling windows for reminders."""

from datetime import datetime, timedelta


def compute_next_window(now=None, cadence_hours: int = 24):
    if now is None:
        now = datetime.now()
    return now + timedelta(hours=cadence_hours)
