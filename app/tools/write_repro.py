"""Write a reproducible pytest file or standalone script."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.tools._helpers import with_trace
from app.tools.trace import TraceWriter


@dataclass
class WriteReproResult:
    path: Path
    kind: str
    summary: str


def write_repro(
    tracer: TraceWriter,
    dest_path: Path,
    content: str,
    kind: str = "pytest",
) -> WriteReproResult:
    def _run() -> WriteReproResult:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(content, encoding="utf-8")
        summary = f"wrote {kind} artifact -> {dest_path.name}"
        return WriteReproResult(path=dest_path, kind=kind, summary=summary)

    return with_trace(
        tracer,
        "write_repro",
        {"dest_path": str(dest_path), "kind": kind, "bytes": len(content)},
        "write_file",
        _run,
        files_touched=[str(dest_path.resolve())],
    )
