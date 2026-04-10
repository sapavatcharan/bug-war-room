"""Weighted confidence reacts to evidence quality."""

from __future__ import annotations

from app.schemas import (
    FixPlanningOutput,
    LogAnalysisOutput,
    PatchValidationHandoff,
    PatchValidationSnapshot,
    ReproductionOutput,
    ReviewerOutput,
    TriageOutput,
)
from app.utils.confidence import compute_weighted_confidence


def test_confidence_drops_on_mismatch() -> None:
    triage = TriageOutput(title="t", symptoms=["a"], expected_behavior="e", actual_behavior="b")
    logs = LogAnalysisOutput(
        error_signature="TypeError: can't compare offset-naive and offset-aware datetimes",
        stack_trace_excerpt="Traceback...",
        stack_frames=[{"path": "x.py"}],
        relevant_log_lines=["a"] * 10,
        correlated_repo_paths=["src/a.py"],
    )
    repro = ReproductionOutput(
        status="success",
        artifact_type="pytest",
        repro_error_signature="RuntimeError: unrelated",
    )
    plan = FixPlanningOutput(
        impacted_files=["src/x.py"],
        proposed_changes=["fix"],
    )
    review = ReviewerOutput()
    pv = PatchValidationHandoff(
        before=PatchValidationSnapshot(status="x", error_signature="TypeError: ..."),
        after=PatchValidationSnapshot(status="repro_still_fails_same_class", error_signature="TypeError"),
        conclusion="inconclusive",
    )
    score, comp, _ = compute_weighted_confidence(
        triage, logs, repro, plan, review, pv,
    )
    score_aligned, comp_aligned, _ = compute_weighted_confidence(
        triage,
        logs,
        ReproductionOutput(
            status="success",
            artifact_type="pytest",
            repro_error_signature=logs.error_signature,
        ),
        plan,
        review,
        PatchValidationHandoff(
            before=pv.before,
            after=PatchValidationSnapshot(
                status="repro_passed_patch_verified",
                error_signature="",
            ),
            conclusion="ok",
        ),
    )
    assert score < score_aligned
    assert comp.repro_match <= comp_aligned.repro_match
    assert comp.patch_validation <= comp_aligned.patch_validation
