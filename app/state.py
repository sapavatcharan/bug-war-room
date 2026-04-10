"""Orchestrator state machine stages."""

from __future__ import annotations

from enum import Enum, auto


class Stage(Enum):
    INIT = auto()
    LOADED = auto()
    TRIAGED = auto()
    LOGS_ANALYZED = auto()
    REPO_NAVIGATED = auto()
    REPRO_ATTEMPTED = auto()
    FIX_PLANNED = auto()
    REVIEWED = auto()
    REPORTED = auto()
    FAILED = auto()
