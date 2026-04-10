"""Assemble FinalReport, confidence, evidence pack, trace markdown."""

from __future__ import annotations

from pathlib import Path

from app.logger import get_logger
from app.schemas import (
    BugSummarySection,
    DegradationSection,
    EvidenceSection,
    FinalReport,
    FixPlanningOutput,
    LogAnalysisOutput,
    OverallConfidenceSection,
    PatchPlanSection,
    PatchValidationHandoff,
    PatchValidationSection,
    ReproductionOutput,
    ReproductionSection,
    RepoNavigationOutput,
    ReviewerNotesSection,
    ReviewerOutput,
    RootCauseAnalysisSection,
    RootCauseHypothesisSection,
    TraceabilitySection,
    TriageOutput,
    ValidationPlanSection,
)
from app.tools.trace import TraceWriter
from app.tools.write_report import write_report_files
from app.utils.confidence import compute_weighted_confidence
from app.utils.evidence_pack import write_evidence_pack_md
from app.utils.trace_markdown import write_run_trace_markdown

log = get_logger()


def _build_degradation(
    logs: LogAnalysisOutput,
    repo: RepoNavigationOutput,
    repro: ReproductionOutput,
    patch_val: PatchValidationHandoff,
    review: ReviewerOutput,
) -> DegradationSection:
    notes: list[str] = []
    fix: list[str] = []

    if logs.degraded_missing_stacktrace:
        notes.append("Stack trace or error line missing from log extraction.")
        fix.append("Provide a raw traceback block or increase log retention.")

    if repo.degraded_ripgrep_unavailable:
        notes.append("Ripgrep unavailable; repo search used Python scan (slower, still deterministic).")
    if repo.degraded_weak_file_evidence:
        notes.append("Many suspect files with shallow stack mapping—evidence is noisier.")

    if repro.status != "success":
        notes.append("Repro did not lock the failure; causal claims lean on static correlation.")
        fix.append("Add a minimal failing command or pytest case from production.")

    if patch_val.degraded_patch_apply_failed:
        notes.append("Candidate patch did not apply cleanly to the workspace copy.")
        fix.append("Regenerate diff against exact mini_repo revision or fix hunk drift.")

    if patch_val.degraded_wrong_failure_after_patch:
        notes.append("After patch, failure signature diverged from the original TypeError.")
        fix.append("Verify patch targets the same comparison site as the repro.")

    if review.challenges:
        notes.append(f"Reviewer raised {len(review.challenges)} evidence challenges.")

    if not notes:
        notes.append("No formal degradation flags; standard offline uncertainty only.")
    if not fix:
        fix.append("Production request IDs, binary versions, and full request payloads.")

    return DegradationSection(notes=notes, what_would_increase_certainty=fix)


class ReportAgent:
    def run(
        self,
        triage: TriageOutput,
        logs: LogAnalysisOutput,
        repo_out: RepoNavigationOutput,
        repro: ReproductionOutput,
        plan: FixPlanningOutput,
        review: ReviewerOutput,
        patch_val: PatchValidationHandoff,
        tracer: TraceWriter,
        reports_dir: Path,
        trace_file: Path,
        project_root: Path,
        extra_artifacts: list[str],
    ) -> FinalReport:
        score, components, why = compute_weighted_confidence(
            triage, logs, repro, plan, review, patch_val,
        )

        rca = plan.root_cause_analysis or RootCauseAnalysisSection(
            considered_hypotheses=[],
            selected_hypothesis=plan.root_cause_summary,
            why_selected="Fallback: structured hypothesis table unavailable.",
        )

        root_conf = min(0.95, max(0.1, score))
        if review.challenges:
            why = why + f" Reviewer flagged {len(review.challenges)} challenges."

        trace_md_path = trace_file.parent / "run_trace.md"
        trace_md_rel = str(trace_md_path.relative_to(project_root))

        degradation = _build_degradation(logs, repo_out, repro, patch_val, review)

        patch_section = PatchValidationSection(
            before=patch_val.before,
            after=patch_val.after,
            regression_test_results=patch_val.regression_test_results,
            conclusion=patch_val.conclusion,
        )

        artifacts = sorted(
            set(
                extra_artifacts
                + [
                    trace_md_rel,
                    str((reports_dir / "evidence_pack.md").relative_to(project_root)),
                ]
            )
        )

        report = FinalReport(
            bug_summary=BugSummarySection(
                title=triage.title,
                symptoms=triage.symptoms,
                expected_behavior=triage.expected_behavior,
                actual_behavior=triage.actual_behavior,
                scope=triage.scope,
                severity=triage.severity_hint,
            ),
            evidence=EvidenceSection(
                stack_trace_excerpt=logs.stack_trace_excerpt,
                relevant_log_lines=logs.relevant_log_lines,
                suspect_files=repo_out.suspect_files,
                suspect_symbols=repo_out.suspect_symbols,
            ),
            reproduction=ReproductionSection(
                status=repro.status,
                artifact_type=repro.artifact_type,
                artifact_path=repro.artifact_path,
                command=repro.command,
                observed_output=repro.observed_output[:12000],
                minimization_attempted=repro.minimization_attempted,
                minimization_result=repro.minimization_result,
                final_artifact_reason=repro.final_artifact_reason,
            ),
            root_cause_analysis=rca,
            root_cause_hypothesis=RootCauseHypothesisSection(
                summary=plan.root_cause_summary,
                detailed_reasoning=plan.root_cause_detailed,
                confidence=round(root_conf, 3),
            ),
            patch_plan=PatchPlanSection(
                files_impacted=plan.impacted_files,
                proposed_changes=plan.proposed_changes,
                safety_notes=plan.safety_notes,
                risks=plan.risks,
            ),
            patch_validation=patch_section,
            validation_plan=ValidationPlanSection(
                tests_to_add=plan.validation_tests_to_add,
                regression_checks=plan.regression_checks,
                manual_checks=plan.manual_checks,
            ),
            reviewer_notes=ReviewerNotesSection(
                challenges=review.challenges,
                edge_cases=review.edge_cases,
                open_questions=review.open_questions,
            ),
            traceability=TraceabilitySection(
                trace_file=str(trace_file.relative_to(project_root)),
                trace_markdown=trace_md_rel,
                generated_artifacts=artifacts,
            ),
            overall_confidence=OverallConfidenceSection(
                score=round(score, 3),
                components=components,
                why_not_higher=why[:2000],
            ),
            degradation=degradation,
            meta={
                "pipeline": "bug-war-room deterministic state machine + patch validation",
                "red_herrings_filtered": logs.red_herring_notes,
                "patched_workspace": patch_val.patched_workspace or None,
            },
        )

        write_run_trace_markdown(trace_file, trace_md_path)
        ep = reports_dir / "evidence_pack.md"
        write_evidence_pack_md(report, ep)

        write_report_files(tracer, report, reports_dir, base_name="final_report")
        log.info("[agent] ReportAgent: final_report + evidence_pack + run_trace.md written")
        return report
