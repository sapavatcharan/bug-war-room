"""Subprocess execution with captured output."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str


def run_command(
    cmd: list[str],
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    timeout: int = 120,
) -> CommandResult:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return CommandResult(
        exit_code=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )
