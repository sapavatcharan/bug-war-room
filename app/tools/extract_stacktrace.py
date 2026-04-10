"""Extract Python stack trace and error line from log text."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.tools._helpers import with_trace
from app.tools.trace import TraceWriter
from app.utils import log_parser


@dataclass
class ExtractStacktraceResult:
    excerpt: str
    error_signature: str
    frames: list[dict[str, str]]
    summary: str


def extract_stacktrace(
    tracer: TraceWriter,
    log_path: Path,
) -> ExtractStacktraceResult:
    def _run() -> ExtractStacktraceResult:
        text = log_parser.read_log_text(log_path)
        lines = log_parser.extract_stacktrace_lines(text)
        excerpt = "\n".join(lines).strip()
        sig = log_parser.extract_error_signature(lines)
        frames = log_parser.parse_stack_frames(lines)
        summary = f"frames={len(frames)} signature={sig[:120]!r}"
        return ExtractStacktraceResult(
            excerpt=excerpt,
            error_signature=sig,
            frames=frames,
            summary=summary,
        )

    return with_trace(
        tracer,
        "extract_stacktrace",
        {"log_path": str(log_path)},
        "parse_traceback",
        _run,
        files_touched=[str(log_path.resolve())],
    )
