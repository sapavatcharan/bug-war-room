"""Orchestrator produces reports and traces."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from app.orchestrator import Orchestrator


@pytest.fixture
def isolated_project(tmp_path: Path) -> Path:
    root = Path(__file__).resolve().parent.parent
    shutil.copytree(root / "inputs", tmp_path / "inputs")
    shutil.copytree(root / "mini_repo", tmp_path / "mini_repo")
    (tmp_path / "generated").mkdir(exist_ok=True)
    return tmp_path


def test_orchestrator_writes_report_and_trace(isolated_project: Path) -> None:
    orch = Orchestrator(project_root=isolated_project)
    report, reports_dir, run_base = orch.run(
        bug_report=isolated_project / "inputs" / "bug_report.md",
        log_file=isolated_project / "inputs" / "app.log",
        repo_path=isolated_project / "mini_repo",
        apply_candidate_patch=False,
    )
    jf = reports_dir / "final_report.json"
    assert jf.exists()
    data = json.loads(jf.read_text(encoding="utf-8"))
    assert data["bug_summary"]["title"]
    assert "TypeError" in data["evidence"]["stack_trace_excerpt"]
    trace_dir = reports_dir.parent / "traces"
    assert (trace_dir / "run_trace.jsonl").exists()
    assert (trace_dir / "run_trace.md").exists()
    assert (reports_dir / "evidence_pack.md").exists()
    assert report.reproduction.artifact_path
    assert data["patch_validation"]["before"]["status"]
    assert data["patch_validation"]["conclusion"]
    assert "components" in data["overall_confidence"]
    assert run_base.is_dir()
