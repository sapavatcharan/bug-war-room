"""Search log files for patterns and return matching lines with context."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.tools._helpers import with_trace
from app.tools.trace import TraceWriter


@dataclass
class SearchLogsResult:
    path: str
    matches: list[str]
    summary: str


def search_logs(
    tracer: TraceWriter,
    log_path: Path,
    patterns: list[str],
    max_lines: int = 80,
    context_lines: int = 0,
) -> SearchLogsResult:
    """Return lines containing any pattern (case-insensitive substring)."""

    def _run() -> SearchLogsResult:
        text = log_path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        lower_patterns = [p.lower() for p in patterns]
        hits: list[str] = []
        for i, line in enumerate(lines):
            low = line.lower()
            if any(p in low for p in lower_patterns):
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                block = lines[start:end]
                hits.extend(block)
            if len(hits) >= max_lines:
                break
        dedup: list[str] = []
        seen: set[str] = set()
        for h in hits:
            if h not in seen:
                seen.add(h)
                dedup.append(h)
        dedup = dedup[:max_lines]
        summary = f"{len(dedup)} line(s) matched patterns in {log_path.name}"
        return SearchLogsResult(path=str(log_path), matches=dedup, summary=summary)

    return with_trace(
        tracer,
        "search_logs",
        {
            "log_path": str(log_path),
            "patterns": patterns,
            "max_lines": max_lines,
        },
        "scan_log_file",
        _run,
        files_touched=[str(log_path.resolve())],
    )
