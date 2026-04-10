"""Weighted confidence: explicit component contributions (sums to score before cap)."""

from __future__ import annotations

from app.schemas import (
    ConfidenceComponentsSection,
    FixPlanningOutput,
    LogAnalysisOutput,
    PatchValidationHandoff,
    ReproductionOutput,
    ReviewerOutput,
    TriageOutput,
)


def compute_weighted_confidence(
    triage: TriageOutput,
    logs: LogAnalysisOutput,
    repro: ReproductionOutput,
    fix_plan: FixPlanningOutput,
    review: ReviewerOutput,
    patch_val: PatchValidationHandoff,
) -> tuple[float, ConfidenceComponentsSection, str]:
    """Return overall score, per-component contributions, and narrative."""
    c = ConfidenceComponentsSection()
    reasons: list[str] = []

    if logs.degraded_missing_stacktrace or not logs.stack_trace_excerpt.strip():
        c.stack_trace_match = 0.0
        reasons.append("Stack trace missing or degraded; stack_trace_match=0.")
    elif len(logs.stack_frames) >= 1 and logs.error_signature:
        c.stack_trace_match = 0.20
    else:
        c.stack_trace_match = 0.10
        reasons.append("Partial stack trace or weak error line.")

    n_sig = len(logs.relevant_log_lines)
    if n_sig >= 8:
        c.log_signal_quality = 0.15
    elif n_sig >= 3:
        c.log_signal_quality = 0.10
        reasons.append("Fewer high-signal log lines than ideal.")
    else:
        c.log_signal_quality = 0.04
        reasons.append("Thin log correlation.")

    suspects = len(set(logs.correlated_repo_paths)) + len(set(fix_plan.impacted_files))
    if suspects >= 3 and not logs.degraded_missing_stacktrace:
        c.repo_alignment = 0.15
    elif suspects >= 1:
        c.repo_alignment = 0.10
        reasons.append("Limited repo alignment evidence.")
    else:
        c.repo_alignment = 0.05
        reasons.append("Weak mapping from stack to repo files.")

    if repro.status == "success" and repro.artifact_type == "pytest":
        c.repro_match = 0.25
        if repro.repro_error_signature and logs.error_signature:
            if repro.repro_error_signature[:40] not in logs.error_signature:
                c.repro_match = 0.18
                reasons.append("Repro error text diverges slightly from log signature.")
    elif repro.status == "success":
        c.repro_match = 0.18
    else:
        c.repro_match = 0.0
        reasons.append("No stable pytest repro; repro_match=0.")

    if patch_val.degraded_patch_apply_failed:
        c.patch_validation = 0.0
        reasons.append("Patch validation skipped (apply failed).")
    elif patch_val.after.status == "repro_passed_patch_verified":
        c.patch_validation = 0.10
    elif patch_val.after.status == "skipped_patch_apply_failed":
        c.patch_validation = 0.0
    elif patch_val.degraded_wrong_failure_after_patch:
        c.patch_validation = 0.02
        reasons.append("After patch, failure signature changed (possible wrong fix).")
    else:
        c.patch_validation = 0.04
        reasons.append("Patch validation inconclusive (repro still red or ambiguous).")

    penalty = 0.0
    penalty -= 0.03 * len(review.challenges)
    if review.confidence_adjustment:
        penalty += review.confidence_adjustment
    c.reviewer_penalty = max(-0.25, min(0.0, penalty))

    if triage.symptoms and not triage.expected_behavior:
        reasons.append("Triage missing crisp expected behavior text.")

    raw = (
        c.stack_trace_match
        + c.log_signal_quality
        + c.repo_alignment
        + c.repro_match
        + c.patch_validation
        + c.reviewer_penalty
    )
    score = max(0.03, min(0.98, raw))

    if not reasons:
        reasons.append(
            "At ceiling for offline evidence; production traces would raise confidence."
        )
    return score, c, " ".join(reasons)[:2000]
