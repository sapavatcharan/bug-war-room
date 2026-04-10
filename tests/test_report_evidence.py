"""Final report embeds concrete log anchors."""

from __future__ import annotations

import json
from pathlib import Path

from app.orchestrator import Orchestrator


def test_report_contains_exact_evidence_lines() -> None:
    root = Path(__file__).resolve().parent.parent
    orch = Orchestrator(project_root=root)
    report, reports_dir, _ = orch.run(
        bug_report=root / "inputs" / "bug_report.md",
        log_file=root / "inputs" / "app.log",
        repo_path=root / "mini_repo",
        apply_candidate_patch=False,
    )
    raw = json.loads((reports_dir / "final_report.json").read_text(encoding="utf-8"))
    flat = json.dumps(raw)
    assert "deploy_image=reminder-svc_0.4.2_sha441" in flat
    assert "legacy_auth_header" in flat
    assert report.evidence.stack_trace_excerpt
