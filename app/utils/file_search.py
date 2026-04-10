"""Ripgrep-backed search with Python fallback."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path


def rg_available() -> bool:
    return shutil.which("rg") is not None


def search_files_python(
    root: Path,
    pattern: str,
    glob: str = "*.py",
    max_matches: int = 200,
) -> list[tuple[str, int, str]]:
    """Return list of (relative_path, line_no, line_text)."""
    rx = re.compile(pattern)
    hits: list[tuple[str, int, str]] = []
    for path in sorted(root.rglob(glob)):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if rx.search(line):
                rel = str(path.relative_to(root))
                hits.append((rel, i, line.rstrip()))
                if len(hits) >= max_matches:
                    return hits
    return hits


def search_files_rg(
    root: Path,
    pattern: str,
    glob: str = "*.py",
    max_matches: int = 200,
) -> list[tuple[str, int, str]]:
    cmd = [
        "rg",
        "--json",
        "--glob",
        glob,
        "--max-count",
        str(max(1, max_matches)),
        pattern,
        str(root),
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    hits: list[tuple[str, int, str]] = []
    if proc.returncode not in (0, 1):
        return hits
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") != "match":
            continue
        data = obj.get("data", {})
        path_text = data.get("path", {}).get("text", "")
        line_no = data.get("line_number", 0)
        line_data = data.get("lines", {}).get("text", "").rstrip()
        if path_text:
            try:
                rel = str(Path(path_text).relative_to(root.resolve()))
            except ValueError:
                rel = path_text
            hits.append((rel, int(line_no), line_data))
        if len(hits) >= max_matches:
            break
    return hits


def search_repo(
    root: Path,
    pattern: str,
    glob: str = "*.py",
    max_matches: int = 200,
) -> list[tuple[str, int, str]]:
    root = root.resolve()
    if rg_available():
        return search_files_rg(root, pattern, glob=glob, max_matches=max_matches)
    return search_files_python(root, pattern, glob=glob, max_matches=max_matches)
