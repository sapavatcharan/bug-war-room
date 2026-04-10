"""Pipeline completes even when patch validation is degraded."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from app.orchestrator import Orchestrator
from app.schemas import PatchValidationHandoff, PatchValidationSnapshot


@pytest.fixture
def isolated_project(tmp_path: Path) -> Path:
    root = Path(__file__).resolve().parent.parent
    shutil.copytree(root / "inputs", tmp_path / "inputs")
    shutil.copytree(root / "mini_repo", tmp_path / "mini_repo")
    (tmp_path / "generated").mkdir(exist_ok=True)
    return tmp_path


def test_pipeline_still_reports_when_patch_application_fails(
    monkeypatch: pytest.MonkeyPatch,
    isolated_project: Path,
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
            conclusion="Synthetic: patch did not apply.",
            degraded_patch_apply_failed=True,
        )

    monkeypatch.setattr(orch_mod, "execute_patch_validation", fake_validate)

    orch = Orchestrator(project_root=isolated_project)
    report, reports_dir, _ = orch.run(
        bug_report=isolated_project / "inputs" / "bug_report.md",
        log_file=isolated_project / "inputs" / "app.log",
        repo_path=isolated_project / "mini_repo",
        apply_candidate_patch=False,
    )
    assert reports_dir.joinpath("final_report.json").exists()
    data = json.loads((reports_dir / "final_report.json").read_text(encoding="utf-8"))
    assert data["patch_validation"]["conclusion"]
    assert report.patch_validation.before.status == "reproduced_target_failure"
    assert any("patch" in n.lower() for n in report.degradation.notes)
