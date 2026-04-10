"""Minimized repro preserves the same failure class."""

from __future__ import annotations

from pathlib import Path

from app.orchestrator import Orchestrator


def test_repro_minimization_keeps_same_error() -> None:
    root = Path(__file__).resolve().parent.parent
    report, _, run_base = Orchestrator(project_root=root).run(
        bug_report=root / "inputs" / "bug_report.md",
        log_file=root / "inputs" / "app.log",
        repo_path=root / "mini_repo",
        apply_candidate_patch=False,
    )
    assert report.reproduction.minimization_attempted is True
    assert "adopted_minimal" in report.reproduction.minimization_result or "kept_primary" in report.reproduction.minimization_result
    assert "typeerror" in report.reproduction.observed_output.lower()
    art = root / report.reproduction.artifact_path
    assert art.exists()
    text = art.read_text(encoding="utf-8")
    assert "BUG_WAR_ROOM_REPO_SRC" in text
    assert run_base.joinpath("repro", "test_repro_minimal_typeerror.py").exists()
