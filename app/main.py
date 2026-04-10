"""Typer CLI entrypoint for bug-war-room."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

import typer
from rich.panel import Panel
from rich.table import Table

from app.config import Settings, project_root as default_project_root
from app.logger import console, setup_logging
from app.orchestrator import Orchestrator
from app.schemas import FinalReport

app = typer.Typer(
    add_completion=False,
    help="Multi-agent (deterministic) bug triage, repro, and patch planning CLI.",
)


def _resolve_project_root(project_root: Optional[Path]) -> Path:
    return (project_root or default_project_root()).resolve()


def _clean_generated(root: Path, skip_confirm: bool = False) -> None:
    gen = root / "generated"
    if not gen.exists():
        gen.mkdir(parents=True, exist_ok=True)
        return
    if not skip_confirm:
        typer.confirm(f"Delete contents of {gen}?", abort=True)
    for child in list(gen.iterdir()):
        if child.name == ".gitkeep":
            continue
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=True)
        else:
            child.unlink(missing_ok=True)
    gen.mkdir(parents=True, exist_ok=True)


def _run_investigation(
    bug_report: Path,
    log_file: Path,
    repo_path: Path,
    project_root: Optional[Path],
    apply_candidate_patch: bool,
    verbose: bool,
) -> Tuple[FinalReport, Path, Path]:
    setup_logging(verbose or Settings().bug_war_room_verbose)
    root = _resolve_project_root(project_root)
    bug = (root / bug_report).resolve() if not bug_report.is_absolute() else bug_report
    log_p = (root / log_file).resolve() if not log_file.is_absolute() else log_file
    repo = (root / repo_path).resolve() if not repo_path.is_absolute() else repo_path

    orch = Orchestrator(project_root=root)
    return orch.run(
        bug_report=bug,
        log_file=log_p,
        repo_path=repo,
        apply_candidate_patch=apply_candidate_patch,
    )


def _print_completion_table(
    report: FinalReport,
    reports_dir: Path,
    run_base: Path,
    root: Path,
) -> None:
    pv = report.patch_validation
    repro_abs = (root / report.reproduction.artifact_path).resolve() if report.reproduction.artifact_path else None
    table = Table(title="Run summary", show_header=False, pad_edge=False)
    table.add_row("confidence", f"{report.overall_confidence.score:.2f} (patch_val component {report.overall_confidence.components.patch_validation:.2f})")
    table.add_row("repro", str(repro_abs) if repro_abs and repro_abs.is_file() else report.reproduction.artifact_path or "n/a")
    table.add_row("patch validation", f"{pv.before.status} → {pv.after.status}")
    table.add_row("regression", "; ".join(f"{r.test_id}:{'OK' if r.passed else 'FAIL'}" for r in pv.regression_test_results) or "n/a")
    table.add_row("final_report.json", str((reports_dir / "final_report.json").resolve()))
    table.add_row("evidence_pack.md", str((reports_dir / "evidence_pack.md").resolve()))
    table.add_row("run_trace.md", str((run_base / "traces" / "run_trace.md").resolve()))
    table.add_row("candidate_patch.diff", str((run_base / "patches" / "candidate_patch.diff").resolve()))
    console.print(table)


def _execute_pipeline(
    bug_report: Path,
    log_file: Path,
    repo_path: Path,
    project_root: Optional[Path],
    apply_candidate_patch: bool,
    verbose: bool,
) -> None:
    report, reports_dir, run_base = _run_investigation(
        bug_report,
        log_file,
        repo_path,
        project_root,
        apply_candidate_patch,
        verbose,
    )
    root = _resolve_project_root(project_root)

    console.print(
        Panel.fit(
            f"[bold green]Run complete[/bold green]\n"
            f"Reports: [cyan]{reports_dir}[/cyan]",
            title="bug-war-room",
        )
    )
    _print_completion_table(report, reports_dir, run_base, root)
    console.print(Panel.fit(report.patch_validation.conclusion[:500], title="Patch validation"))


@app.command("run")
def run_cmd(
    bug_report: Path = typer.Option(
        Path("inputs/bug_report.md"),
        "--bug-report",
        help="Path to bug report markdown",
    ),
    log_file: Path = typer.Option(
        Path("inputs/app.log"),
        "--log-file",
        help="Path to application log",
    ),
    repo_path: Path = typer.Option(
        Path("mini_repo"),
        "--repo-path",
        help="Path to repository under investigation",
    ),
    project_root: Optional[Path] = typer.Option(
        None,
        "--project-root",
        help="bug-war-room root (defaults to package parent)",
    ),
    apply_candidate_patch: bool = typer.Option(
        False,
        "--apply-candidate-patch",
        help="Apply generated/unified diff to mini_repo (off by default)",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Execute the full pipeline: triage → logs → repo → repro → plan → review → report."""
    _execute_pipeline(
        bug_report,
        log_file,
        repo_path,
        project_root,
        apply_candidate_patch,
        verbose,
    )


@app.command("demo")
def demo_cmd(
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Reviewer-facing demo: clean → full run → visible repro (on patched copy when validated) → summary."""
    root = _resolve_project_root(None)
    _clean_generated(root, skip_confirm=True)
    typer.echo("— Cleaned generated/ —")

    report, reports_dir, run_base = _run_investigation(
        Path("inputs/bug_report.md"),
        Path("inputs/app.log"),
        Path("mini_repo"),
        None,
        False,
        verbose,
    )

    repro_rel = report.reproduction.artifact_path
    repro_abs = root / repro_rel if repro_rel else None
    typer.echo(f"\n[repro artifact] {repro_abs}")
    pv = report.patch_validation

    if repro_abs and repro_abs.is_file():
        patched_raw = (report.meta or {}).get("patched_workspace")
        patched_src: Optional[Path] = None
        if patched_raw:
            pw = Path(patched_raw)
            if not pw.is_absolute():
                pw = (root / pw).resolve()
            else:
                pw = pw.resolve()
            cand = pw / "src"
            if cand.is_dir():
                patched_src = cand

        use_patched = (
            patched_src is not None
            and pv.after.status == "repro_passed_patch_verified"
        )

        if use_patched:
            typer.echo(
                "\n— Visible repro: same test against isolated patched_workspace (expect pass) —\n"
            )
            repo_src = str(patched_src)
            env = {
                **os.environ,
                "PYTHONPATH": repo_src,
                "BUG_WAR_ROOM_REPO_SRC": repo_src,
            }
            pr = subprocess.run(
                [sys.executable, "-m", "pytest", str(repro_abs), "-v", "--tb=short"],
                cwd=str(root),
                env=env,
                check=False,
            )
            if pr.returncode == 0:
                console.print(
                    Panel.fit(
                        "[bold green]Repro passed[/bold green] on "
                        "[cyan]generated/.../patched_workspace[/cyan] (matches patch validation). "
                        "[dim]Root [cyan]mini_repo[/cyan] in the repo is still unpatched unless you "
                        "use [cyan]run --apply-candidate-patch[/cyan].[/dim]",
                        title="Visible repro",
                        border_style="green",
                    )
                )
            else:
                console.print(
                    Panel.fit(
                        "[yellow]Unexpected:[/yellow] repro failed on patched_workspace "
                        f"(exit {pr.returncode}). See pytest output above.",
                        title="Visible repro",
                        border_style="yellow",
                    )
                )
        else:
            typer.echo("\n— Re-running repro against unpatched mini_repo (see note below) —\n")
            src = root / "mini_repo" / "src"
            env = {**os.environ, "PYTHONPATH": str(src)}
            pr = subprocess.run(
                [sys.executable, "-m", "pytest", str(repro_abs), "-v", "--tb=short"],
                cwd=str(root),
                env=env,
                check=False,
            )
            if pr.returncode != 0:
                console.print(
                    Panel.fit(
                        "[bold green]This is expected[/bold green]\n\n"
                        "Pytest reported [red]FAILED[/red] because [cyan]mini_repo[/cyan] still "
                        "contains the intentional bug. Patch validation did not re-run the repro "
                        "on a verified patched copy in this run.\n\n"
                        "[dim]To make this step pass (mutates repo): "
                        "python -m app.main run --apply-candidate-patch[/dim]",
                        title="Re-run repro — not an error",
                        border_style="green",
                    )
                )
            else:
                console.print(
                    Panel.fit(
                        "[cyan]mini_repo[/cyan] already passes the repro (scheduler may be patched).",
                        title="Re-run repro",
                        border_style="cyan",
                    )
                )
    else:
        typer.echo("(No repro file on disk — skipped visible pytest.)")

    json_path = reports_dir / "final_report.json"
    evidence_path = reports_dir / "evidence_pack.md"
    trace_md = run_base / "traces" / "run_trace.md"
    patch_path = run_base / "patches" / "candidate_patch.diff"

    decision = (
        "fix_candidate_validated_under_isolated_copy"
        if pv.after.status == "repro_passed_patch_verified"
        else "investigate_continue_or_refine_patch"
    )

    table = Table(title="bug-war-room demo summary", show_header=False)
    table.add_row("decision", decision)
    sel = report.root_cause_analysis.selected_hypothesis
    sel_disp = (sel[:117] + "…") if len(sel) > 120 else sel
    table.add_row("selected root cause", sel_disp)
    table.add_row("repro artifact", str(repro_abs or "n/a"))
    table.add_row("candidate patch", str(patch_path))
    table.add_row(
        "patch validation (before → after)",
        f"{pv.before.status} / {pv.before.error_signature[:60]}… → "
        f"{pv.after.status} / {(pv.after.error_signature or '∅')[:60]}",
    )
    table.add_row("regression", "; ".join(f"{r.test_id}:{'OK' if r.passed else 'FAIL'}" for r in pv.regression_test_results) or "n/a")
    table.add_row("final_report.json", str(json_path))
    table.add_row("evidence_pack.md", str(evidence_path))
    table.add_row("run_trace.md", str(trace_md))

    console.print(table)
    console.print(
        Panel.fit(
            f"[bold]{pv.conclusion}[/bold]",
            title="Patch validation conclusion",
        )
    )

    rep_cmd = " ".join(report.reproduction.command) if report.reproduction.command else "n/a"
    val_cmd = " ".join(pv.repro_command) if pv.repro_command else rep_cmd
    sel_full = report.root_cause_analysis.selected_hypothesis
    sel_short = (sel_full[:200] + "…") if len(sel_full) > 200 else sel_full
    before_st = pv.before.status
    after_st = pv.after.status
    trace_json = run_base / "traces" / "run_trace.jsonl"
    snapshot = (
        f"[bold]decision[/bold] {decision}\n"
        f"[bold]selected root cause[/bold] {sel_short}\n"
        f"[bold]repro artifact[/bold] {repro_abs or 'n/a'}\n"
        f"[bold]repro command[/bold] {rep_cmd}\n"
        f"[bold]validation repro command[/bold] {val_cmd}\n"
        f"[bold]patch file[/bold] {patch_path}\n"
        f"[bold]before status[/bold] {before_st}\n"
        f"[bold]after status[/bold] {after_st}\n"
        f"[bold]final_report.json[/bold] {json_path}\n"
        f"[bold]evidence_pack.md[/bold] {evidence_path}\n"
        f"[bold]run_trace.md[/bold] {trace_md}\n"
        f"[bold]run_trace.jsonl[/bold] {trace_json}"
    )
    console.print(Panel.fit(snapshot, title="Reviewer snapshot (copy paths)", border_style="blue"))


@app.command("test-repro")
def test_repro_cmd(
    project_root: Optional[Path] = typer.Option(None, "--project-root"),
) -> None:
    """Run pytest on the repro from the last run (reads final_report.json when present)."""
    root = _resolve_project_root(project_root)
    marker = root / "generated" / "LAST_RUN.txt"
    if not marker.exists():
        typer.echo("No LAST_RUN.txt; run `demo` or `run` first.", err=True)
        raise typer.Exit(code=1)
    run_base = Path(marker.read_text(encoding="utf-8").strip())
    jp = run_base / "reports" / "final_report.json"
    repro: Optional[Path] = None
    if jp.exists():
        data = json.loads(jp.read_text(encoding="utf-8"))
        rel = data.get("reproduction", {}).get("artifact_path")
        if rel:
            repro = (root / rel).resolve()
    if repro is None or not repro.is_file():
        repro = run_base / "repro" / "test_repro_timezone_comparison.py"
    if not repro.is_file():
        typer.echo(f"Missing repro file: {repro}", err=True)
        raise typer.Exit(code=1)
    src = root / "mini_repo" / "src"
    env = {**os.environ, "PYTHONPATH": str(src)}

    r = subprocess.run(
        [sys.executable, "-m", "pytest", str(repro), "-v", "--tb=short"],
        cwd=str(root),
        env=env,
        check=False,
    )
    raise typer.Exit(code=r.returncode)


@app.command("clean")
def clean_cmd(
    project_root: Optional[Path] = typer.Option(None, "--project-root"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Remove generated run artifacts (keeps directory structure)."""
    root = _resolve_project_root(project_root)
    _clean_generated(root, skip_confirm=yes)
    typer.echo("Cleaned generated/.")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
