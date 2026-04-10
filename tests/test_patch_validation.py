"""Patch application on a copy fixes the scheduling path."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from app.agents.fix_planner_agent import CANDIDATE_DIFF
from app.utils.command_runner import run_command
from app.utils.patch_validation import _apply_patch, copy_repo


@pytest.fixture
def mini_root() -> Path:
    return Path(__file__).resolve().parent.parent / "mini_repo"


def test_patch_validation_detects_fix(tmp_path: Path, mini_root: Path) -> None:
    workspace = tmp_path / "ws"
    copy_repo(mini_root, workspace)
    diff = tmp_path / "p.diff"
    diff.write_text(CANDIDATE_DIFF, encoding="utf-8")
    ok, err = _apply_patch(workspace, diff)
    assert ok, err

    snippet = tmp_path / "snip.py"
    snippet.write_text(
        "\n".join(
            [
                "import sys",
                f'sys.path.insert(0, r"{(workspace / "src").resolve()}")',
                "from service import schedule_reminder",
                'schedule_reminder("2026-04-10T15:00:00Z", cadence_hours=24)',
                "print('ok')",
            ]
        ),
        encoding="utf-8",
    )
    env = {**os.environ, "PYTHONPATH": str(workspace / "src")}
    res = run_command([sys.executable, str(snippet)], cwd=tmp_path, env=env, timeout=60)
    assert res.exit_code == 0, res.stderr
