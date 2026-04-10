"""Derive root-cause hypothesis, patch plan, validation; emit candidate diff."""

from __future__ import annotations

from pathlib import Path

from app.logger import get_logger
from app.schemas import (
    FixPlanningOutput,
    HypothesisConsidered,
    LogAnalysisOutput,
    ReproductionOutput,
    RepoNavigationOutput,
    RootCauseAnalysisSection,
    RunContext,
    TriageOutput,
)
from app.tools.search_repo import search_repo_tool
from app.tools.trace import TraceWriter
from app.tools.write_repro import write_repro

log = get_logger()

CANDIDATE_DIFF = '''--- a/src/scheduler.py
+++ b/src/scheduler.py
@@ -1,9 +1,9 @@
 """Scheduling windows for reminders."""
 
-from datetime import datetime, timedelta
+from datetime import datetime, timedelta, timezone
 
 
 def compute_next_window(now=None, cadence_hours: int = 24):
     if now is None:
-        now = datetime.now()
+        now = datetime.now(timezone.utc)
     return now + timedelta(hours=cadence_hours)
'''


class FixPlannerAgent:
    def run(
        self,
        ctx: RunContext,
        triage: TriageOutput,
        logs: LogAnalysisOutput,
        repo: RepoNavigationOutput,
        repro: ReproductionOutput,
        tracer: TraceWriter,
        patches_dir: Path,
    ) -> FixPlanningOutput:
        tracer.set_agent("FixPlannerAgent")
        res = search_repo_tool(
            tracer,
            Path(ctx.repo_path),
            r"datetime\.now\(",
            glob="*.py",
            max_matches=20,
        )

        summary = (
            "The failure matches Python's rule that naive and aware datetimes "
            "cannot be ordered. `parser.parse_user_datetime` returns a timezone-aware "
            "instant for ISO strings ending with `Z`, while `scheduler.compute_next_window` "
            "defaults internal `now` to `datetime.now()` without tzinfo. "
            "`service.schedule_reminder` compares these values directly, triggering the "
            "observed TypeError consistent with the stack in app.log."
        )

        detailed = (
            f"Evidence: log signature {logs.error_signature!r} aligns with repo symbols "
            f"{', '.join(repo.suspect_symbols[:5])}. "
            f"Ripgrep located `datetime.now(` in scheduler-related code ({res.summary}). "
        )
        if repro.status == "success":
            detailed += (
                "The generated pytest reproduces the same TypeError when calling "
                "`schedule_reminder` with a `Z`-suffixed timestamp, isolating the "
                "comparison path without external services."
            )
        else:
            detailed += (
                "Reproduction did not firmly lock the runtime failure; hypothesis leans "
                "more heavily on static correlation between parser output shape and "
                "`datetime.now()` usage."
            )

        impacted = list(
            dict.fromkeys(
                [f for f in repo.suspect_files if f.endswith(".py")]
                or ["src/scheduler.py", "src/service.py", "src/parser.py"]
            )
        )

        proposed = [
            "Change `compute_next_window` to use an explicit UTC anchor "
            "(`datetime.now(timezone.utc)`) when `now` is omitted, matching aware "
            "user-derived instants.",
            "Add a regression test that feeds `...Z` timestamps through "
            "`schedule_reminder` and asserts scheduling succeeds.",
            "Optionally document that all wall-clock comparisons in this service "
            "use UTC-aware datetimes end-to-end.",
        ]

        safety = [
            "Scope is limited to default `now` selection; callers passing explicit "
            "`now` are unchanged.",
            "Prefer UTC for internal anchors to avoid local-DST ambiguity in servers.",
        ]

        risks = [
            "If any caller relied on naive local `datetime.now()` semantics for "
            "non-UTC business rules, behavior could shift; validate with domain owners.",
            "Downstream persistence expecting naive timestamps may need serialization "
            "adjustments.",
        ]

        functions_impacted = [
            "compute_next_window",
            "schedule_reminder",
            "parse_user_datetime",
        ]
        why_this_fix_matches = (
            "Log-derived signature is the stdlib rule against comparing naive vs aware datetimes; "
            "the stack excerpt points at `service.schedule_reminder` where `<` orders user input "
            "against the scheduler window. Repo search shows `datetime.now(` in "
            "`scheduler.compute_next_window` with no timezone, while `parse_user_datetime` documents "
            "UTC-aware output for `Z` ISO strings — so the failure mode is explained without "
            "invoking a broken parser. The pytest repro calls only `schedule_reminder` with a "
            "`Z` timestamp and fails with the same TypeError family, isolating that comparison. "
            "Hypothesis 2 (parser bug) is rejected: logs show ordering failure, not "
            "`ValueError` from parsing. Hypothesis 3 (third-party) is rejected: frames are "
            "service/stdlib only. Anchoring `now` to `timezone.utc` aligns both sides with the "
            "documented aware parser output."
        )

        patch_path = patches_dir / "candidate_patch.diff"
        write_repro(tracer, patch_path, CANDIDATE_DIFF, kind="diff")

        log.info("[agent] FixPlannerAgent: wrote %s", patch_path.name)

        h1_evidence = [
            f"Log signature: {logs.error_signature}",
            "Stack references `service.py` comparison site.",
            f"Repo search: {res.summary}",
        ]
        if repro.status == "success":
            h1_evidence.append("Pytest repro raises the same TypeError family.")

        h2_evidence = [
            "`parse_user_datetime` explicitly documents Z → aware UTC.",
            "Failure is ordering (`<`), not parse exception.",
        ]
        h2_conflicting = [
            "Stack points to comparison line, not parser internals.",
            "No `ValueError` from `fromisoformat` in logs.",
        ]

        h3_evidence = [
            "Useful when no local stack is available.",
        ]
        h3_conflicting = [
            "Same traceback reproduces on this Python; no third-party frame in trace.",
            "Reduces probability given direct stdlib datetime comparison error.",
        ]

        rca = RootCauseAnalysisSection(
            considered_hypotheses=[
                HypothesisConsidered(
                    rank=1,
                    hypothesis=(
                        "Naive `datetime.now()` in `compute_next_window` is ordered against "
                        "timezone-aware user instants from `parse_user_datetime`."
                    ),
                    supporting_evidence=h1_evidence,
                    conflicting_evidence=[],
                    status="selected",
                ),
                HypothesisConsidered(
                    rank=2,
                    hypothesis=(
                        "Parser mishandles `Z` and returns an inconsistent tz-aware object."
                    ),
                    supporting_evidence=h2_evidence,
                    conflicting_evidence=h2_conflicting,
                    status="rejected",
                ),
                HypothesisConsidered(
                    rank=3,
                    hypothesis="Third-party dependency regression in datetime handling.",
                    supporting_evidence=h3_evidence,
                    conflicting_evidence=h3_conflicting,
                    status="downgraded",
                ),
            ],
            selected_hypothesis=summary,
            why_selected=(
                "Hypothesis 1 is the only one consistent with the traceback line in "
                "`service.schedule_reminder`, the presence of `datetime.now(` in scheduler code, "
                "and a failing repro that only exercises ISO `Z` input plus default window "
                "computation. Hypotheses 2 and 3 lack supporting frames or conflict with "
                "observed error text."
            ),
        )

        return FixPlanningOutput(
            root_cause_summary=summary,
            root_cause_detailed=detailed,
            impacted_files=impacted,
            functions_impacted=functions_impacted,
            proposed_changes=proposed,
            why_this_fix_matches_the_evidence=why_this_fix_matches,
            safety_notes=safety,
            risks=risks,
            validation_tests_to_add=[
                "pytest: aware Z input + default window computation (no TypeError)",
                "pytest: naive local string parsing still compares if both sides normalized",
            ],
            regression_checks=[
                "Run existing `tests/test_scheduler_smoke.py` after patch",
                "Grep for remaining naive `datetime.now()` in scheduling paths",
            ],
            manual_checks=[
                "Submit sample payloads with `Z`, explicit offsets, and naive strings",
                "Verify logs no longer show datetime comparison TypeError under load test",
            ],
            candidate_patch_path=str(patch_path),
            root_cause_analysis=rca,
        )
