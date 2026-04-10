"""Apply candidate patch to a temp repo copy and re-run repro + regression tests."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from app.logger import get_logger
from app.schemas import PatchValidationHandoff, PatchValidationSnapshot, RegressionTestResult
from app.utils.command_runner import run_command
from app.utils.signature import extract_error_signature_from_output, signatures_consistent

log = get_logger()


def _apply_patch(repo_root: Path, diff_path: Path) -> tuple[bool, str]:
    if not shutil.which("patch"):
        return False, "`patch` binary not found"
    proc = subprocess.run(
        ["patch", "-p1", "--batch", "-i", str(diff_path)],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return False, f"patch rc={proc.returncode} stderr={proc.stderr!r}"
    return True, ""


def copy_repo(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(
        src,
        dest,
        ignore=shutil.ignore_patterns(
            "__pycache__",
            "*.pyc",
            ".pytest_cache",
            ".git",
        ),
    )


def run_repro_on_repo(
    repro_test: Path,
    project_root: Path,
    repo_src: Path,
) -> tuple[int, str, str]:
    env = {**os.environ, "PYTHONPATH": str(repo_src), "BUG_WAR_ROOM_REPO_SRC": str(repo_src)}
    cmd = [sys.executable, "-m", "pytest", str(repro_test), "-v", "--tb=short"]
    res = run_command(cmd, cwd=project_root, env=env, timeout=120)
    combined = res.stdout + "\n" + res.stderr
    return res.exit_code, combined, extract_error_signature_from_output(combined)


def run_regression_tests(
    repo_root: Path,
    tests_dir: Path,
) -> list[RegressionTestResult]:
    if not tests_dir.is_dir():
        return [
            RegressionTestResult(
                test_id="regression",
                passed=False,
                detail="tests/ directory missing in workspace copy",
            )
        ]
    env = {**os.environ, "PYTHONPATH": str(repo_root / "src")}
    cmd = [sys.executable, "-m", "pytest", str(tests_dir), "-q", "--tb=line"]
    res = run_command(cmd, cwd=repo_root, env=env, timeout=120)
    out = res.stdout + res.stderr
    passed = res.exit_code == 0
    return [
        RegressionTestResult(
            test_id="mini_repo_tests",
            passed=passed,
            detail=out[-4000:] if out else f"exit={res.exit_code}",
        )
    ]


def execute_patch_validation(
    original_repo: Path,
    repro_test: Path,
    project_root: Path,
    diff_path: Path,
    workspace_copy: Path,
    log_error_signature: str,
    before_repro_exit: int,
    before_combined_output: str,
) -> PatchValidationHandoff:
    """Copy repo, apply diff, re-run repro and regression suite."""
    repro_command = [
        sys.executable,
        "-m",
        "pytest",
        str(repro_test),
        "-v",
        "--tb=short",
    ]
    before_sig = extract_error_signature_from_output(before_combined_output)
    if not before_sig and log_error_signature:
        before_sig = log_error_signature

    if before_repro_exit == 0:
        before_status = "repro_unexpected_pass"
    elif "typeerror" in before_combined_output.lower() and (
        "offset-naive" in before_combined_output.lower()
        or "offset-aware" in before_combined_output.lower()
    ):
        before_status = "reproduced_target_failure"
    elif "typeerror" in before_combined_output.lower():
        before_status = "reproduced_typeerror"
    else:
        before_status = "repro_failed_other"

    repro_match_before = signatures_consistent(log_error_signature, before_sig)
    safety_blurb = (
        "Validation mutates only `patched_workspace/` under this run_id; repository root "
        "`mini_repo/` is untouched unless the operator passes `--apply-candidate-patch`."
    )

    copy_repo(original_repo, workspace_copy)
    ok, err = _apply_patch(workspace_copy, diff_path)
    patched_src = workspace_copy / "src"

    reg_results: list[RegressionTestResult] = []
    after_exit = -1
    after_combined = ""
    after_sig = ""

    if not ok:
        log.warning("[patch_validation] apply failed: %s", err)
        return PatchValidationHandoff(
            before=PatchValidationSnapshot(status=before_status, error_signature=before_sig),
            after=PatchValidationSnapshot(status="skipped_patch_apply_failed", error_signature=""),
            regression_test_results=[
                RegressionTestResult(test_id="patch_apply", passed=False, detail=err)
            ],
            conclusion=(
                "Candidate patch could not be applied to a workspace copy; "
                "no after-state repro or regression run was executed."
            ),
            degraded_patch_apply_failed=True,
            patched_workspace=str(workspace_copy),
            repro_command=repro_command,
            repro_match_before=repro_match_before,
            repro_match_after=False,
            same_repro_command=True,
            original_failure_resolved=False,
            failure_changed_after_patch=False,
            safety_summary=safety_blurb,
            confidence_note=(
                "Patch validation did not run; `patch_validation` confidence component is zero."
            ),
        )

    after_exit, after_combined, after_sig = run_repro_on_repo(
        repro_test, project_root, patched_src,
    )
    reg_results = run_regression_tests(workspace_copy, workspace_copy / "tests")

    wrong_failure = False
    if after_exit != 0:
        if after_sig and before_sig and after_sig != before_sig:
            if "typeerror" not in after_sig.lower():
                wrong_failure = True
        elif after_exit != 0 and "passed" in after_combined.lower():
            pass

    repro_match_after = after_exit == 0
    reg_ok = bool(reg_results and reg_results[0].passed)
    original_failure_resolved = after_exit == 0 and before_status in (
        "reproduced_target_failure",
        "reproduced_typeerror",
    )
    failure_changed_after_patch = wrong_failure or (
        after_exit != 0
        and bool(after_sig)
        and bool(before_sig)
        and after_sig != before_sig
    )

    if after_exit == 0:
        after_status = "repro_passed_patch_verified"
        conclusion = (
            "After applying the candidate patch to an isolated copy, the repro test passed "
            f"and the bundled regression suite {'passed' if reg_ok else 'reported failures'}."
        )
    elif wrong_failure:
        after_status = "repro_still_fails_different_error"
        conclusion = (
            "Patch applied but the repro run still fails with a different signature than the "
            "original failure; the change may be incomplete or the repro is coupling to other behavior."
        )
    else:
        after_status = "repro_still_fails_same_class"
        conclusion = (
            "Patch applied but repro still exits non-zero with a similar error class; "
            "the fix may be incomplete."
        )

    if after_exit == 0 and reg_ok:
        conf_note = (
            "Verified fix: same pytest command as pre-patch repro now exits 0 on the patched "
            "copy; regression suite passed — `patch_validation` component contributes positively "
            "to overall confidence."
        )
    elif wrong_failure:
        conf_note = (
            "Confidence is penalized: post-patch failure signature diverged from the original "
            "log/repro TypeError — evidence that the change may not target the reported defect."
        )
    else:
        conf_note = (
            "Patch validation completed but repro or regression did not fully green; "
            "`patch_validation` score reflects partial or inconclusive verification."
        )

    return PatchValidationHandoff(
        before=PatchValidationSnapshot(status=before_status, error_signature=before_sig),
        after=PatchValidationSnapshot(status=after_status, error_signature=after_sig),
        regression_test_results=reg_results,
        conclusion=conclusion,
        degraded_wrong_failure_after_patch=wrong_failure,
        patched_workspace=str(workspace_copy),
        repro_command=repro_command,
        repro_match_before=repro_match_before,
        repro_match_after=repro_match_after,
        same_repro_command=True,
        original_failure_resolved=original_failure_resolved,
        failure_changed_after_patch=failure_changed_after_patch,
        safety_summary=safety_blurb,
        confidence_note=conf_note,
    )
