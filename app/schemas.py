"""Pydantic models for handoffs and final reports."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class RunContext(BaseModel):
    """Immutable-ish run metadata passed through the pipeline."""

    run_id: str
    bug_report_path: str
    log_file_path: str
    repo_path: str
    output_root: str = "generated"
    bug_report_text: str = ""
    apply_candidate_patch: bool = False


class TriageOutput(BaseModel):
    title: str = ""
    symptoms: list[str] = Field(default_factory=list)
    expected_behavior: str = ""
    actual_behavior: str = ""
    severity_hint: str = "unknown"
    scope: str = ""
    failure_surface: str = ""
    ranked_hypotheses: list[str] = Field(default_factory=list)
    search_keywords: list[str] = Field(default_factory=list)


class LogAnalysisOutput(BaseModel):
    error_signature: str = ""
    stack_trace_excerpt: str = ""
    stack_frames: list[dict[str, str]] = Field(default_factory=list)
    relevant_log_lines: list[str] = Field(default_factory=list)
    correlated_repo_paths: list[str] = Field(default_factory=list)
    red_herring_notes: list[str] = Field(default_factory=list)
    degraded_missing_stacktrace: bool = False


class RepoNavigationOutput(BaseModel):
    suspect_files: list[str] = Field(default_factory=list)
    suspect_symbols: list[str] = Field(default_factory=list)
    frame_to_path_hints: list[str] = Field(default_factory=list)
    search_hits_summary: list[str] = Field(default_factory=list)
    degraded_weak_file_evidence: bool = False
    degraded_ripgrep_unavailable: bool = False


class ReproductionOutput(BaseModel):
    status: Literal["success", "failed", "skipped"] = "skipped"
    artifact_type: Literal["pytest", "script", "none"] = "none"
    artifact_path: str = ""
    command: list[str] = Field(default_factory=list)
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    observed_output: str = ""
    minimization_attempted: bool = False
    minimization_result: str = ""
    final_artifact_reason: str = ""
    repro_error_signature: str = ""


class HypothesisConsidered(BaseModel):
    rank: int
    hypothesis: str
    supporting_evidence: list[str] = Field(default_factory=list)
    conflicting_evidence: list[str] = Field(default_factory=list)
    status: Literal["selected", "rejected", "downgraded"] = "downgraded"


class RootCauseAnalysisSection(BaseModel):
    considered_hypotheses: list[HypothesisConsidered]
    selected_hypothesis: str
    why_selected: str


class FixPlanningOutput(BaseModel):
    root_cause_summary: str = ""
    root_cause_detailed: str = ""
    impacted_files: list[str] = Field(default_factory=list)
    proposed_changes: list[str] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    validation_tests_to_add: list[str] = Field(default_factory=list)
    regression_checks: list[str] = Field(default_factory=list)
    manual_checks: list[str] = Field(default_factory=list)
    candidate_patch_path: str = ""
    root_cause_analysis: Optional[RootCauseAnalysisSection] = None


class ReviewerOutput(BaseModel):
    challenges: list[str] = Field(default_factory=list)
    edge_cases: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    repro_minimality_notes: str = ""
    evidence_support_notes: str = ""
    confidence_adjustment: float = 0.0


class PatchValidationSnapshot(BaseModel):
    status: str
    error_signature: str


class RegressionTestResult(BaseModel):
    test_id: str
    passed: bool
    detail: str


class PatchValidationSection(BaseModel):
    before: PatchValidationSnapshot
    after: PatchValidationSnapshot
    regression_test_results: list[RegressionTestResult]
    conclusion: str


class BugSummarySection(BaseModel):
    title: str
    symptoms: list[str]
    expected_behavior: str
    actual_behavior: str
    scope: str
    severity: str


class EvidenceSection(BaseModel):
    stack_trace_excerpt: str
    relevant_log_lines: list[str]
    suspect_files: list[str]
    suspect_symbols: list[str]


class ReproductionSection(BaseModel):
    status: str
    artifact_type: str
    artifact_path: str
    command: list[str]
    observed_output: str
    minimization_attempted: bool = False
    minimization_result: str = ""
    final_artifact_reason: str = ""


class RootCauseHypothesisSection(BaseModel):
    summary: str
    detailed_reasoning: str
    confidence: float


class PatchPlanSection(BaseModel):
    files_impacted: list[str]
    proposed_changes: list[str]
    safety_notes: list[str]
    risks: list[str]


class ValidationPlanSection(BaseModel):
    tests_to_add: list[str]
    regression_checks: list[str]
    manual_checks: list[str]


class ReviewerNotesSection(BaseModel):
    challenges: list[str]
    edge_cases: list[str]
    open_questions: list[str]


class TraceabilitySection(BaseModel):
    trace_file: str
    trace_markdown: str = ""
    generated_artifacts: list[str]


class ConfidenceComponentsSection(BaseModel):
    stack_trace_match: float = 0.0
    log_signal_quality: float = 0.0
    repo_alignment: float = 0.0
    repro_match: float = 0.0
    patch_validation: float = 0.0
    reviewer_penalty: float = 0.0


class OverallConfidenceSection(BaseModel):
    score: float
    components: ConfidenceComponentsSection
    why_not_higher: str


class DegradationSection(BaseModel):
    notes: list[str] = Field(default_factory=list)
    what_would_increase_certainty: list[str] = Field(default_factory=list)


class FinalReport(BaseModel):
    bug_summary: BugSummarySection
    evidence: EvidenceSection
    reproduction: ReproductionSection
    root_cause_analysis: RootCauseAnalysisSection
    root_cause_hypothesis: RootCauseHypothesisSection
    patch_plan: PatchPlanSection
    patch_validation: PatchValidationSection
    validation_plan: ValidationPlanSection
    reviewer_notes: ReviewerNotesSection
    traceability: TraceabilitySection
    overall_confidence: OverallConfidenceSection
    degradation: DegradationSection
    meta: dict[str, Any] = Field(default_factory=dict)


class ToolCallRecord(BaseModel):
    run_id: str
    tool_name: str
    input_summary: dict[str, Any]
    action: str
    output_summary: str
    success: bool
    duration_ms: float
    error: Optional[str] = None


class PatchValidationHandoff(BaseModel):
    """Built by orchestrator; consumed by ReportAgent."""

    before: PatchValidationSnapshot
    after: PatchValidationSnapshot
    regression_test_results: list[RegressionTestResult] = Field(default_factory=list)
    conclusion: str = ""
    degraded_patch_apply_failed: bool = False
    degraded_wrong_failure_after_patch: bool = False
    patched_workspace: str = ""
