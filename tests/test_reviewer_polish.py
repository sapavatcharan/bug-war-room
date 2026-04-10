"""Targeted assertions for reviewer-facing polish (schema, trace, evidence pack, validation)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.orchestrator import Orchestrator
from app.schemas import PatchValidationHandoff, PatchValidationSnapshot


def test_report_contains_exact_error_signature() -> None:
    root = Path(__file__).resolve().parent.parent
    _, reports_dir, _ = Orchestrator(project_root=root).run(
        bug_report=root / "inputs" / "bug_report.md",
        log_file=root / "inputs" / "app.log",
        repo_path=root / "mini_repo",
        apply_candidate_patch=False,
    )
    data = json.loads((reports_dir / "final_report.json").read_text(encoding="utf-8"))
    sig = data["evidence"]["error_signature"]
    assert "TypeError" in sig
    assert "offset-naive" in sig or "offset-aware" in sig


def test_report_contains_repo_search_hits() -> None:
    root = Path(__file__).resolve().parent.parent
    _, reports_dir, _ = Orchestrator(project_root=root).run(
        bug_report=root / "inputs" / "bug_report.md",
        log_file=root / "inputs" / "app.log",
        repo_path=root / "mini_repo",
        apply_candidate_patch=False,
    )
    data = json.loads((reports_dir / "final_report.json").read_text(encoding="utf-8"))
    hits = data["evidence"]["repo_search_hits"]
    assert isinstance(hits, list)
    assert len(hits) >= 1


def test_trace_record_contains_agent_and_timestamp() -> None:
    root = Path(__file__).resolve().parent.parent
    _, _, run_base = Orchestrator(project_root=root).run(
        bug_report=root / "inputs" / "bug_report.md",
        log_file=root / "inputs" / "app.log",
        repo_path=root / "mini_repo",
        apply_candidate_patch=False,
    )
    trace_path = run_base / "traces" / "run_trace.jsonl"
    rows = [
        json.loads(line)
        for line in trace_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert rows
    assert any(r.get("timestamp") for r in rows)
    agents = {r.get("agent_name") for r in rows}
    assert "TriageAgent" in agents
    assert "ReportAgent" in agents


def test_patch_validation_marks_mismatch_when_failure_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.orchestrator as orch_mod

    def fake_validate(*_a, **_k):
        return PatchValidationHandoff(
            before=PatchValidationSnapshot(
                status="reproduced_target_failure",
                error_signature="TypeError: can't compare offset-naive and offset-aware datetimes",
            ),
            after=PatchValidationSnapshot(
                status="repro_still_fails_different_error",
                error_signature="ValueError: synthetic different failure",
            ),
            regression_test_results=[],
            conclusion="Synthetic: signature changed after patch.",
            degraded_wrong_failure_after_patch=True,
            patched_workspace="/tmp/fake",
            repro_command=["python", "-m", "pytest", "x.py"],
            repro_match_before=True,
            repro_match_after=False,
            same_repro_command=True,
            original_failure_resolved=False,
            failure_changed_after_patch=True,
            safety_summary="test",
            confidence_note="penalized",
        )

    monkeypatch.setattr(orch_mod, "execute_patch_validation", fake_validate)

    root = Path(__file__).resolve().parent.parent
    report, _, _ = Orchestrator(project_root=root).run(
        bug_report=root / "inputs" / "bug_report.md",
        log_file=root / "inputs" / "app.log",
        repo_path=root / "mini_repo",
        apply_candidate_patch=False,
    )
    assert report.patch_validation.failure_changed_after_patch is True
    assert report.patch_validation.after.status == "repro_still_fails_different_error"


def test_evidence_pack_contains_selected_hypothesis_and_patch_summary() -> None:
    root = Path(__file__).resolve().parent.parent
    _, reports_dir, _ = Orchestrator(project_root=root).run(
        bug_report=root / "inputs" / "bug_report.md",
        log_file=root / "inputs" / "app.log",
        repo_path=root / "mini_repo",
        apply_candidate_patch=False,
    )
    text = (reports_dir / "evidence_pack.md").read_text(encoding="utf-8")
    assert "## Selected root cause" in text
    assert "## Patch validation" in text
    assert "why this fix matches" in text.lower()


def test_pipeline_still_writes_report_when_patch_apply_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.orchestrator as orch_mod

    def fake_validate(*_a, **_k):
        return PatchValidationHandoff(
            before=PatchValidationSnapshot(
                status="reproduced_target_failure",
                error_signature="TypeError: can't compare",
            ),
            after=PatchValidationSnapshot(status="skipped_patch_apply_failed", error_signature=""),
            regression_test_results=[],
            conclusion="Patch did not apply.",
            degraded_patch_apply_failed=True,
            patched_workspace="/tmp/ws",
            repro_command=["py", "-m", "pytest", "t.py"],
            repro_match_before=True,
            repro_match_after=False,
            same_repro_command=True,
            original_failure_resolved=False,
            failure_changed_after_patch=False,
            safety_summary="isolated copy only",
            confidence_note="no validation run",
        )

    monkeypatch.setattr(orch_mod, "execute_patch_validation", fake_validate)

    root = Path(__file__).resolve().parent.parent
    report, reports_dir, _ = Orchestrator(project_root=root).run(
        bug_report=root / "inputs" / "bug_report.md",
        log_file=root / "inputs" / "app.log",
        repo_path=root / "mini_repo",
        apply_candidate_patch=False,
    )
    assert (reports_dir / "final_report.json").exists()
    assert report.patch_validation.repro_match_after is False
    assert report.patch_validation.safety_summary
