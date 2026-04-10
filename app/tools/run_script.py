"""Run a Python script and capture output."""

import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from app.tools._helpers import with_trace
from app.tools.trace import TraceWriter
from app.utils.command_runner import run_command


@dataclass
class RunScriptResult:
    exit_code: int
    stdout: str
    stderr: str
    summary: str


def run_script(
    tracer: TraceWriter,
    script_path: Path,
    cwd: Path,
    extra_env: Optional[Dict[str, str]] = None,
) -> RunScriptResult:
    cmd = [sys.executable, str(script_path)]
    cmd_str = " ".join(shlex.quote(c) for c in cmd)

    def _run() -> RunScriptResult:
        import os

        env = {**os.environ, **(extra_env or {})}
        res = run_command(cmd, cwd=cwd, env=env, timeout=120)
        summary = f"exit={res.exit_code}"
        return RunScriptResult(
            exit_code=res.exit_code,
            stdout=res.stdout,
            stderr=res.stderr,
            summary=summary,
        )

    return with_trace(
        tracer,
        "run_script",
        {"script_path": str(script_path), "cwd": str(cwd)},
        "execute_script",
        _run,
        command_executed=cmd_str,
        files_touched=[str(script_path.resolve())],
    )
