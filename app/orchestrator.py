"""Deterministic state-machine orchestrator for the multi-agent pipeline."""

import shutil
import subprocess
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.agents.fix_planner_agent import FixPlannerAgent
from app.agents.log_analyst_agent import LogAnalystAgent
from app.agents.report_agent import ReportAgent
from app.agents.repo_navigator_agent import RepoNavigatorAgent
from app.agents.reproduction_agent import ReproductionAgent
from app.agents.reviewer_agent import ReviewerAgent
from app.agents.triage_agent import TriageAgent
from app.logger import get_logger
from app.schemas import (
    FinalReport,
    PatchValidationHandoff,
    PatchValidationSnapshot,
    RunContext,
)
from app.state import Stage
from app.tools.trace import TraceWriter
from app.utils.artifact_writer import ensure_run_dirs, legacy_symlink_or_note
from app.utils.patch_validation import execute_patch_validation

log = get_logger()


def _run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{ts}_{uuid.uuid4().hex[:8]}"


def _apply_patch(repo_root: Path, diff_path: Path) -> None:
    if not shutil.which("patch"):
        raise RuntimeError("`patch` binary not found; install patch or apply diff manually")
    proc = subprocess.run(
        ["patch", "-p1", "--batch", "-i", str(diff_path)],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"patch failed rc={proc.returncode} stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )


class Orchestrator:
    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.project_root = (project_root or Path(__file__).resolve().parent.parent).resolve()

    def run(
        self,
        bug_report: Path,
        log_file: Path,
        repo_path: Path,
        apply_candidate_patch: bool = False,
    ) -> tuple[FinalReport, Path, Path]:
        run_id = _run_id()
        out_root = self.project_root / "generated"
        dirs = ensure_run_dirs(out_root, run_id)
        trace_path = dirs["traces"] / "run_trace.jsonl"
        tracer = TraceWriter(trace_path, run_id)
        legacy_symlink_or_note(self.project_root, dirs["base"])

        bug_text = bug_report.read_text(encoding="utf-8", errors="replace")
        ctx = RunContext(
            run_id=run_id,
            bug_report_path=str(bug_report.resolve()),
            log_file_path=str(log_file.resolve()),
            repo_path=str(repo_path.resolve()),
            output_root=str(out_root),
            bug_report_text=bug_text,
            apply_candidate_patch=apply_candidate_patch,
        )

        stage = Stage.LOADED
        log.info("[orchestrator] run_id=%s", run_id)

        try:
            triage = TriageAgent().run(ctx, tracer)
            stage = Stage.TRIAGED

            logs_out = LogAnalystAgent().run(ctx, triage, tracer)
            stage = Stage.LOGS_ANALYZED

            repo_out = RepoNavigatorAgent().run(ctx, logs_out, tracer)
            stage = Stage.REPO_NAVIGATED

            repro = ReproductionAgent().run(
                ctx,
                logs_out,
                repo_out,
                tracer,
                repro_dir=dirs["repro"],
                project_root=self.project_root,
            )
            stage = Stage.REPRO_ATTEMPTED

            plan = FixPlannerAgent().run(
                ctx,
                triage,
                logs_out,
                repo_out,
                repro,
                tracer,
                patches_dir=dirs["patches"],
            )
            stage = Stage.FIX_PLANNED

            diff_p = Path(plan.candidate_patch_path)
            repro_fs = self.project_root / repro.artifact_path if repro.artifact_path else None
            if (
                repro.status == "success"
                and repro_fs
                and repro_fs.is_file()
                and diff_p.is_file()
            ):
                before_combined = (repro.stdout + "\n" + repro.stderr)[:50000]
                patch_val = execute_patch_validation(
                    Path(ctx.repo_path).resolve(),
                    repro_fs.resolve(),
                    self.project_root,
                    diff_p.resolve(),
                    dirs["base"] / "patched_workspace",
                    logs_out.error_signature,
                    repro.exit_code if repro.exit_code is not None else 1,
                    before_combined,
                )
            else:
                reason = "no repro file" if not (repro_fs and repro_fs.is_file()) else "no diff"
                log.warning("[orchestrator] patch validation skipped (%s)", reason)
                patch_val = PatchValidationHandoff(
                    before=PatchValidationSnapshot(
                        status="skipped_no_repro_or_diff",
                        error_signature=logs_out.error_signature,
                    ),
                    after=PatchValidationSnapshot(status="skipped", error_signature=""),
                    regression_test_results=[],
                    conclusion=(
                        "Patch validation skipped: need a failing repro artifact and "
                        "candidate_patch.diff on disk."
                    ),
                )

            review = ReviewerAgent().run(ctx, triage, logs_out, repro, plan, tracer)
            stage = Stage.REVIEWED

            patch_rel = Path(plan.candidate_patch_path).relative_to(self.project_root)
            extra = [
                str(trace_path.relative_to(self.project_root)),
                str(patch_rel),
            ]
            if repro.artifact_path:
                extra.append(repro.artifact_path)

            report = ReportAgent().run(
                triage=triage,
                logs=logs_out,
                repo_out=repo_out,
                repro=repro,
                plan=plan,
                review=review,
                patch_val=patch_val,
                tracer=tracer,
                reports_dir=dirs["reports"],
                trace_file=trace_path,
                project_root=self.project_root,
                extra_artifacts=sorted(set(extra)),
            )
            stage = Stage.REPORTED

            if ctx.apply_candidate_patch:
                try:
                    _apply_patch(Path(ctx.repo_path), diff_p)
                    log.warning(
                        "[orchestrator] applied candidate patch to original repo %s",
                        ctx.repo_path,
                    )
                except Exception as e:
                    log.error(
                        "[orchestrator] apply_candidate_patch failed (non-fatal): %s",
                        e,
                    )

            log.info("[orchestrator] completed stage=%s", stage.name)
            return report, dirs["reports"], dirs["base"]

        except Exception:
            log.error(
                "[orchestrator] failed at stage=%s\n%s",
                stage.name,
                traceback.format_exc(),
            )
            raise
