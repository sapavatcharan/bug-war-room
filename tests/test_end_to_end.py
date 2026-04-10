"""End-to-end validation against bundled fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from app.orchestrator import Orchestrator


def test_demo_bundle_reproduces_typeerror_in_report() -> None:
    root = Path(__file__).resolve().parent.parent
    orch = Orchestrator(project_root=root)
    report, reports_dir, _ = orch.run(
        bug_report=root / "inputs" / "bug_report.md",
        log_file=root / "inputs" / "app.log",
        repo_path=root / "mini_repo",
        apply_candidate_patch=False,
    )
    assert report.reproduction.status == "success"
    combined = report.reproduction.observed_output.lower()
    assert "typeerror" in combined
    yf = reports_dir / "final_report.yaml"
    assert yf.exists()
    raw = json.loads((reports_dir / "final_report.json").read_text(encoding="utf-8"))
    assert raw["reviewer_notes"]["open_questions"]
    assert raw["traceability"]["generated_artifacts"]
    assert raw["patch_validation"]["after"]["status"] == "repro_passed_patch_verified"
    assert raw["root_cause_analysis"]["considered_hypotheses"][0]["status"] == "selected"
    assert raw["reproduction"]["minimization_attempted"] is True
