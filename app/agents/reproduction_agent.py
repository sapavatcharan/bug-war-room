"""Generate minimal failing repro, optional second minimized variant, execute."""

from __future__ import annotations

import sys
from pathlib import Path

from app.logger import get_logger
from app.schemas import (
    LogAnalysisOutput,
    ReproductionOutput,
    RepoNavigationOutput,
    RunContext,
)
from app.tools.run_pytest import run_pytest
from app.tools.run_script import run_script
from app.tools.write_repro import write_repro
from app.tools.trace import TraceWriter
from app.utils.signature import extract_error_signature_from_output, signatures_consistent

log = get_logger()


REPRO_PYTEST_TEMPLATE = '''"""
Auto-generated repro: timezone-aware user input vs naive internal clock.
Set BUG_WAR_ROOM_REPO_SRC to an absolute path to .../src to target a patched copy.
"""
import os
import sys
from pathlib import Path

import pytest


def _repo_src():
    override = os.environ.get("BUG_WAR_ROOM_REPO_SRC")
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parents[{parents}] / "{src_rel}"


@pytest.fixture(scope="module", autouse=True)
def _path():
    p = _repo_src()
    assert p.is_dir(), f"missing src dir: {{p}}"
    sys.path.insert(0, str(p))


def test_schedule_reminder_reproduces_aware_naive_typeerror():
    from service import schedule_reminder

    schedule_reminder("2026-04-10T15:00:00Z", cadence_hours=24)
'''


REPRO_MINIMAL_TEMPLATE = '''"""Minimal repro: Z-suffix UTC ISO vs naive scheduler clock."""
import os
import sys
from pathlib import Path

import pytest


def _src():
    o = os.environ.get("BUG_WAR_ROOM_REPO_SRC")
    return Path(o).resolve() if o else Path(__file__).resolve().parents[{parents}] / "{src_rel}"


@pytest.fixture(scope="module", autouse=True)
def _p():
    p = _src()
    assert p.is_dir()
    sys.path.insert(0, str(p))


def test_z_iso_typeerror():
    from service import schedule_reminder
    schedule_reminder("2026-04-10T15:00:00Z", cadence_hours=24)
'''


SCRIPT_TEMPLATE = '''import os
import sys
from pathlib import Path
def _src():
    o = os.environ.get("BUG_WAR_ROOM_REPO_SRC")
    return Path(o).resolve() if o else Path(__file__).resolve().parents[{parents}] / "{src_rel}"
sys.path.insert(0, str(_src()))
from service import schedule_reminder
schedule_reminder("2026-04-10T15:00:00Z", cadence_hours=24)
'''


def _line_count(p: Path) -> int:
    return len(p.read_text(encoding="utf-8").splitlines())


class ReproductionAgent:
    def run(
        self,
        ctx: RunContext,
        logs: LogAnalysisOutput,
        repo: RepoNavigationOutput,
        tracer: TraceWriter,
        repro_dir: Path,
        project_root: Path,
    ) -> ReproductionOutput:
        _ = repo
        repo_path = Path(ctx.repo_path).resolve()
        src = repo_path / "src"
        if not src.is_dir():
            log.warning("[agent] ReproductionAgent: no src/ under repo")
            return ReproductionOutput(
                status="failed",
                artifact_type="none",
                observed_output="mini_repo/src not found",
                final_artifact_reason="Cannot locate src/; repro skipped.",
                minimization_result="not_attempted: missing src directory",
            )

        try:
            rel_to_repro = len(repro_dir.resolve().relative_to(project_root.resolve()).parts)
        except ValueError:
            rel_to_repro = 2

        parents_up = rel_to_repro
        src_rel = f"{Path(ctx.repo_path).resolve().name}/src"

        test_name = "test_repro_timezone_comparison.py"
        test_path = repro_dir / test_name
        content = REPRO_PYTEST_TEMPLATE.format(
            parents=parents_up,
            src_rel=src_rel,
        )
        write_repro(tracer, test_path, content, kind="pytest")

        extra_env = {"PYTHONPATH": str(src)}
        res = run_pytest(
            tracer,
            test_path=test_path,
            cwd=project_root,
            extra_env=extra_env,
        )

        combined = res.stdout + "\n" + res.stderr
        bug_signal = (
            res.exit_code != 0
            and (
                "typeerror" in combined.lower()
                or "offset-naive" in combined.lower()
                or "offset-aware" in combined.lower()
            )
        )
        sig_primary = extract_error_signature_from_output(combined)

        minimization_attempted = False
        minimization_result = "not_attempted: primary repro did not exhibit target failure"
        final_reason = "Primary generated pytest targets schedule_reminder with Z-suffix ISO input."
        chosen_path = test_path
        chosen_type = "pytest"
        chosen_cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(test_path),
            "-v",
            "--tb=short",
        ]
        out_combined = combined
        exit_c = res.exit_code

        if bug_signal:
            minimal_path = repro_dir / "test_repro_minimal_typeerror.py"
            min_content = REPRO_MINIMAL_TEMPLATE.format(
                parents=parents_up,
                src_rel=src_rel,
            )
            write_repro(tracer, minimal_path, min_content, kind="pytest")
            minimization_attempted = True
            res2 = run_pytest(
                tracer,
                test_path=minimal_path,
                cwd=project_root,
                extra_env=extra_env,
            )
            c2 = res2.stdout + "\n" + res2.stderr
            sig_min = extract_error_signature_from_output(c2)
            min_ok = res2.exit_code != 0 and (
                "typeerror" in c2.lower()
                or "offset-naive" in c2.lower()
                or "offset-aware" in c2.lower()
            )
            if min_ok and signatures_consistent(logs.error_signature, sig_min):
                lc_full = _line_count(test_path)
                lc_min = _line_count(minimal_path)
                if lc_min < lc_full:
                    chosen_path = minimal_path
                    chosen_type = "pytest"
                    chosen_cmd = [
                        sys.executable,
                        "-m",
                        "pytest",
                        str(minimal_path),
                        "-v",
                        "--tb=short",
                    ]
                    out_combined = c2
                    exit_c = res2.exit_code
                    sig_primary = sig_min
                    minimization_result = (
                        f"adopted_minimal: {lc_min} lines vs {lc_full} lines, same failure class"
                    )
                    final_reason = (
                        "Minimized test removes non-essential commentary while preserving "
                        "the Z-suffix path through schedule_reminder."
                    )
                else:
                    minimization_result = (
                        f"kept_primary: minimal not shorter ({lc_min} vs {lc_full} lines)"
                    )
            elif min_ok:
                minimization_result = "kept_primary: minimal output signature diverged from log anchor"
            else:
                minimization_result = "kept_primary: minimized variant did not reproduce TypeError"

        out = ReproductionOutput(
            status="success" if bug_signal else "failed",
            artifact_type=chosen_type,
            artifact_path=str(chosen_path.relative_to(project_root)),
            command=chosen_cmd,
            exit_code=exit_c,
            stdout=res.stdout if chosen_path == test_path else res2.stdout if bug_signal else res.stdout,
            stderr=res.stderr if chosen_path == test_path else res2.stderr if bug_signal else res.stderr,
            observed_output=out_combined[-8000:],
            minimization_attempted=minimization_attempted,
            minimization_result=minimization_result,
            final_artifact_reason=final_reason,
            repro_error_signature=sig_primary or extract_error_signature_from_output(out_combined),
        )

        if not bug_signal:
            log.warning("[agent] ReproductionAgent: pytest passed unexpectedly; trying script")
            script_path = repro_dir / "repro_standalone.py"
            sc = SCRIPT_TEMPLATE.format(parents=parents_up, src_rel=src_rel)
            write_repro(tracer, script_path, sc, kind="script")
            sr = run_script(tracer, script_path, cwd=project_root, extra_env=extra_env)
            c3 = sr.stdout + "\n" + sr.stderr
            sig3 = extract_error_signature_from_output(c3)
            sig2_ok = sr.exit_code != 0 and (
                "typeerror" in c3.lower()
                or "offset-naive" in c3.lower()
                or "offset-aware" in c3.lower()
            )
            out = ReproductionOutput(
                status="success" if sig2_ok else "failed",
                artifact_type="script",
                artifact_path=str(script_path.relative_to(project_root)),
                command=[sys.executable, str(script_path)],
                exit_code=sr.exit_code,
                stdout=sr.stdout,
                stderr=sr.stderr,
                observed_output=c3[-8000:],
                minimization_attempted=False,
                minimization_result="fallback_script" if sig2_ok else "script_did_not_fail",
                final_artifact_reason="Standalone script after pytest did not exhibit failure.",
                repro_error_signature=sig3,
            )

        log.info(
            "[agent] ReproductionAgent: status=%s exit=%s min=%s",
            out.status,
            out.exit_code,
            out.minimization_result,
        )
        return out
