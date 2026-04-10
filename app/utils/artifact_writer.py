"""Ensure output directories exist."""

from __future__ import annotations

from pathlib import Path


def ensure_run_dirs(output_root: Path, run_id: str) -> dict[str, Path]:
    base = output_root / run_id
    paths = {
        "base": base,
        "traces": base / "traces",
        "repro": base / "repro",
        "reports": base / "reports",
        "patches": base / "patches",
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths


def legacy_symlink_or_note(project_root: Path, run_base: Path) -> None:
    """Copy latest run pointer for demos (simple marker file)."""
    marker = project_root / "generated" / "LAST_RUN.txt"
    try:
        marker.write_text(str(run_base.resolve()), encoding="utf-8")
    except OSError:
        pass
