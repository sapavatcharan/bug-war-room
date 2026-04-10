"""Run pytest on a path and capture output."""

import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from app.tools._helpers import with_trace
from app.tools.trace import TraceWriter
from app.utils.command_runner import run_command


@dataclass
class RunPytestResult:
    exit_code: int
    stdout: str
    stderr: str
    summary: str


def run_pytest(
    tracer: TraceWriter,
    test_path: Path,
    cwd: Path,
    extra_env: Optional[Dict[str, str]] = None,
) -> RunPytestResult:
    cmd = [sys.executable, "-m", "pytest", str(test_path), "-v", "--tb=short"]
    cmd_str = " ".join(shlex.quote(c) for c in cmd)

    def _run() -> RunPytestResult:
        import os

        env = {**os.environ, **(extra_env or {})}
        res = run_command(cmd, cwd=cwd, env=env, timeout=120)
        summary = f"exit={res.exit_code} stdout_bytes={len(res.stdout)}"
        return RunPytestResult(
            exit_code=res.exit_code,
            stdout=res.stdout,
            stderr=res.stderr,
            summary=summary,
        )

    return with_trace(
        tracer,
        "run_pytest",
        {"test_path": str(test_path), "cwd": str(cwd)},
        "execute_pytest",
        _run,
        command_executed=cmd_str,
        files_touched=[str(test_path.resolve())],
    )
