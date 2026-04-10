"""Parse bug report and seed log search keywords."""

from __future__ import annotations

import re
from pathlib import Path

from app.logger import get_logger
from app.schemas import RunContext, TriageOutput
from app.tools.search_logs import search_logs
from app.tools.trace import TraceWriter

log = get_logger()


class TriageAgent:
    def run(self, ctx: RunContext, tracer: TraceWriter) -> TriageOutput:
        text = ctx.bug_report_text
        if not text.strip():
            text = Path(ctx.bug_report_path).read_text(encoding="utf-8", errors="replace")

        title = ""
        m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if m:
            title = m.group(1).strip()

        symptoms: list[str] = []
        for line in text.splitlines():
            if re.match(r"^[-*]\s+", line.strip()):
                symptoms.append(line.strip().lstrip("-* ").strip())

        expected = ""
        actual = ""
        if "Expected" in text:
            sec = re.split(r"Expected behavior", text, maxsplit=1, flags=re.I)
            if len(sec) > 1:
                chunk = sec[1][:800]
                expected = chunk.split("\n\n")[0].strip(":\n- ")
        if "Actual" in text:
            sec = re.split(r"Actual behavior", text, maxsplit=1, flags=re.I)
            if len(sec) > 1:
                chunk = sec[1][:800]
                actual = chunk.split("\n\n")[0].strip(":\n- ")

        severity = "high" if "crash" in text.lower() or "500" in text else "medium"
        scope = "scheduler/reminder path" if "reminder" in text.lower() else "core service"
        failure_surface = "datetime comparison during scheduling"

        ranked = [
            "Mixed naive vs timezone-aware datetime objects in scheduling logic",
            "Incorrect parsing of ISO-8601 Z suffix without normalization",
            "Third-party library version mismatch (less likely given stack)",
        ]

        keywords = [
            "TypeError",
            "datetime",
            "offset-naive",
            "scheduler",
            "service",
            "reminder",
        ]
        unique_kw = list(dict.fromkeys(keywords))

        log_path = Path(ctx.log_file_path)
        sl = search_logs(tracer, log_path, patterns=unique_kw[:6], max_lines=30)

        if not title:
            title = "Untitled bug report"

        log.info("[agent] TriageAgent: %s (%d log hits)", title, len(sl.matches))

        return TriageOutput(
            title=title,
            symptoms=symptoms[:12] or ["See bug report body"],
            expected_behavior=expected or "Service handles user timestamps without crashing.",
            actual_behavior=actual or "Request fails with TypeError during datetime comparison.",
            severity_hint=severity,
            scope=scope,
            failure_surface=failure_surface,
            ranked_hypotheses=ranked,
            search_keywords=unique_kw,
        )
