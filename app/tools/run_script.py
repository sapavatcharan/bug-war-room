"""Run a Python script and capture output."""

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
    def _run() -> RunScriptResult:
        import os
        import sys

        env = {**os.environ, **(extra_env or {})}
        cmd = [sys.executable, str(script_path)]
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
    )
