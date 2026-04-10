"""Challenge assumptions; adjust confidence when evidence is thin."""

from __future__ import annotations

from pathlib import Path

from app.logger import get_logger
from app.schemas import (
    FixPlanningOutput,
    LogAnalysisOutput,
    ReproductionOutput,
    ReviewerOutput,
    RunContext,
    TriageOutput,
)
from app.tools.search_repo import search_repo_tool
from app.tools.trace import TraceWriter

log = get_logger()


class ReviewerAgent:
    def run(
        self,
        ctx: RunContext,
        triage: TriageOutput,
        logs: LogAnalysisOutput,
        repro: ReproductionOutput,
        plan: FixPlanningOutput,
        tracer: TraceWriter,
    ) -> ReviewerOutput:
        tracer.set_agent("ReviewerAgent")
        challenges: list[str] = []
        edge_cases: list[str] = []
        questions: list[str] = []
        adjustment = 0.0

        verify = search_repo_tool(
            tracer,
            Path(ctx.repo_path),
            r"def\s+schedule_reminder",
            glob="*.py",
            max_matches=15,
        )
        if not verify.hits:
            challenges.append(
                "Could not locate `schedule_reminder` definition via repo search; "
                "hypothesis linkage to service entrypoint is weaker."
            )
            adjustment -= 0.04

        if repro.status != "success":
            challenges.append(
                "Automated repro did not demonstrate the TypeError; root cause "
                "relies primarily on static analysis and log correlation."
            )
            adjustment -= 0.08

        if "parser.py" not in " ".join(plan.impacted_files):
            challenges.append(
                "Parser behavior is inferred; confirm whether any inputs bypass "
                "`Z` handling and yield naive datetimes."
            )

        if not logs.stack_trace_excerpt.strip():
            challenges.append("Stack trace excerpt was empty; frame-to-file mapping is weaker.")
            adjustment -= 0.05

        edge_cases = [
            "User strings with explicit offsets (`+05:30`) vs `Z` normalization",
            "DST boundaries if local naive timestamps are ever introduced",
            "Leap seconds and sub-second precision in ISO inputs",
        ]

        questions = [
            "Should business logic interpret user times in tenant timezone rather than UTC?",
            "Are reminders persisted as UTC in the database today?",
        ]

        minimality = (
            "Repro targets a single public entrypoint with a fixed ISO string; "
            "further minimality could inline parser+scheduler calls, but current "
            "scope already pins the service-layer comparison."
        )
        evidence_note = (
            "Hypothesis is strongest when log signature, repo search hits for "
            "`datetime.now(`, and failing repro align; any missing piece reduces "
            "causal certainty."
        )

        log.info(
            "[agent] ReviewerAgent: title=%r challenges=%d",
            triage.title[:60],
            len(challenges),
        )

        return ReviewerOutput(
            challenges=challenges,
            edge_cases=edge_cases,
            open_questions=questions,
            repro_minimality_notes=minimality,
            evidence_support_notes=evidence_note,
            confidence_adjustment=adjustment,
        )
