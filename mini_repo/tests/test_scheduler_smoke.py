"""Smoke tests for scheduler (naive clock only)."""

from datetime import datetime, timedelta

import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from scheduler import compute_next_window


def test_compute_next_window_with_explicit_now():
    base = datetime(2026, 1, 1, 12, 0, 0)
    nxt = compute_next_window(now=base, cadence_hours=1)
    assert nxt == base + timedelta(hours=1)
