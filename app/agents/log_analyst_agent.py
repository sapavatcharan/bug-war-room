"""Extract stack traces and correlate with repository paths."""

from __future__ import annotations

from pathlib import Path

from app.logger import get_logger
from app.schemas import LogAnalysisOutput, RunContext, TriageOutput
from app.tools.extract_stacktrace import extract_stacktrace
from app.tools.search_logs import search_logs
from app.tools.trace import TraceWriter
from app.utils import log_parser

log = get_logger()


class LogAnalystAgent:
    def run(
        self,
        ctx: RunContext,
        triage: TriageOutput,
        tracer: TraceWriter,
    ) -> LogAnalysisOutput:
        log_path = Path(ctx.log_file_path)
        repo_root = Path(ctx.repo_path)

        ex = extract_stacktrace(tracer, log_path)
        sl = search_logs(
            tracer,
            log_path,
            patterns=triage.search_keywords[:8],
            max_lines=60,
        )

        high = log_parser.filter_high_signal_lines(
            log_path.read_text(encoding="utf-8", errors="replace"),
            triage.search_keywords,
            max_lines=35,
        )

        correlated = log_parser.correlate_frames_to_repo(ex.frames, repo_root)

        red_herrings = [
            "Log line mentioning deprecated API is informational only; stack does not traverse that module.",
            "Periodic 'slow query' warning occurs before the failing request and is unrelated to datetime TypeError.",
        ]

        log.info(
            "[agent] LogAnalystAgent: signature=%r frames=%d",
            ex.error_signature[:80] if ex.error_signature else "",
            len(ex.frames),
        )

        missing = not (ex.excerpt.strip() and ex.error_signature.strip())
        if missing:
            log.warning("[agent] LogAnalystAgent: degraded — missing stack or error line")

        return LogAnalysisOutput(
            error_signature=ex.error_signature,
            stack_trace_excerpt=ex.excerpt,
            stack_frames=[dict(f) for f in ex.frames],
            relevant_log_lines=high or sl.matches[:25],
            correlated_repo_paths=correlated,
            red_herring_notes=red_herrings,
            degraded_missing_stacktrace=missing,
        )
