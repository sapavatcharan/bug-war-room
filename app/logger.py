"""Structured console logging with Rich."""

from __future__ import annotations

import logging
import sys

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

THEME = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "agent": "bold magenta",
        "tool": "green",
    }
)

console = Console(theme=THEME)


def setup_logging(verbose: bool = False) -> logging.Logger:
    log = logging.getLogger("bug_war_room")
    log.handlers.clear()
    log.setLevel(logging.DEBUG if verbose else logging.INFO)
    handler = RichHandler(
        console=console,
        show_path=False,
        rich_tracebacks=True,
        markup=True,
    )
    handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    log.addHandler(handler)
    log.propagate = False
    return log


def get_logger(name: str = "bug_war_room") -> logging.Logger:
    return logging.getLogger(name)
