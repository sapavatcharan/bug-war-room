"""Single-file markdown bundle for reviewer handoff (~90s read)."""

from __future__ import annotations

from pathlib import Path

from app.schemas import FinalReport


def write_evidence_pack_md(report: FinalReport, path: Path) -> None:
    pv = report.patch_validation
    rca = report.root_cause_analysis
    ev = report.evidence
    rep = report.reproduction
    pp = report.patch_plan

    lines: list[str] = [
        "# Evidence pack (reviewer handoff)",
        "",
        "## Bug",
        "",
        f"**{report.bug_summary.title}**",
        "",
        "### Error signature (exact)",
        "",
        f"`{ev.error_signature}`",
        "",
        "### High-signal log lines",
        "",
        "```",
        *(ev.exact_log_lines[:20] or ev.relevant_log_lines[:20]),
        "```",
        "",
        "### Stack trace (excerpt)",
        "",
        "```",
        ev.stack_trace_excerpt[:3500],
        "```",
        "",
        "## Correlation (why these clues tie together)",
        "",
        ev.correlation_reasoning,
        "",
        "## Repo signals",
        "",
        f"- **Suspect files:** {', '.join(ev.suspect_files[:12])}",
        f"- **Suspect symbols:** {', '.join(ev.suspect_symbols[:12])}",
        "",
        "### Repo search hit summaries",
        "",
        *[f"- {h}" for h in (ev.repo_search_hits[:8] or ["(none)"])],
        "",
        "## Reproduction",
        "",
        f"- **Artifact:** `{rep.artifact_path}`",
        f"- **Command:** `{' '.join(rep.command)}`",
        f"- **Exit code:** {rep.exit_code}",
        f"- **Signature match vs logs:** {'yes' if rep.matched_error_signature else 'no / partial'} — {rep.consistency_check}",
        f"- **Minimization:** {rep.minimization_result or 'n/a'}",
        "",
        "### Stdout (excerpt)",
        "",
        "```",
        (rep.stdout_excerpt or rep.observed_output)[:2500],
        "```",
        "",
        "### Stderr (excerpt)",
        "",
        "```",
        rep.stderr_excerpt[:2500],
        "```",
        "",
        "## Hypotheses (top 3 — why two lost)",
        "",
    ]
    for h in rca.considered_hypotheses:
        lines.append(f"### Rank {h.rank} — **{h.status}**")
        lines.append(h.hypothesis)
        lines.append("")
        lines.append("- **Supporting:** " + "; ".join(h.supporting_evidence[:4]))
        lines.append("- **Conflicting:** " + "; ".join(h.conflicting_evidence[:4]))
        lines.append("")

    lines.extend(
        [
            "## Selected root cause",
            "",
            rca.selected_hypothesis,
            "",
            f"**Why this one:** {rca.why_selected}",
            "",
            "## Patch plan (forensic)",
            "",
            f"- **Files:** {', '.join(pp.files_impacted[:12])}",
            f"- **Functions:** {', '.join(pp.functions_impacted[:12])}",
            "",
            "**Why this fix matches the evidence**",
            "",
            pp.why_this_fix_matches_the_evidence,
            "",
            "**Risks:** " + "; ".join(pp.patch_risks[:6] or pp.risks[:6]),
            "",
            "## Candidate patch",
            "",
            f"See `candidate_patch.diff` next to this run’s `patches/` directory (also listed below).",
            "",
            "## Patch validation",
            "",
            f"- **Same repro command before & after:** {pv.same_repro_command}",
            (
                f"- **Repro command (validation):** `{' '.join(pv.repro_command)}`"
                if pv.repro_command
                else "- **Repro command (validation):** _(skipped)_"
            ),
            (
                f"- **Before:** `{pv.before.status}` — `{pv.before.error_signature[:120]}…`"
                if len(pv.before.error_signature) > 120
                else f"- **Before:** `{pv.before.status}` — `{pv.before.error_signature}`"
            ),
            "",
            f"- **Repro matched log signature (pre-patch):** {pv.repro_match_before}",
            f"- **After:** `{pv.after.status}` — `{pv.after.error_signature or '∅'}`",
            f"- **Repro green after patch:** {pv.repro_match_after}",
            f"- **Original failure class resolved:** {pv.original_failure_resolved}",
            f"- **Failure changed to different error:** {pv.failure_changed_after_patch}",
            "",
            f"**Safety:** {pv.safety_summary}",
            "",
            f"**Confidence linkage:** {pv.confidence_note}",
            "",
            "### Regression",
            "",
        ]
    )
    for r in pv.regression_test_results:
        lines.append(f"- **{r.test_id}:** {'PASS' if r.passed else 'FAIL'} — {r.detail[:400]}")
    lines.extend(
        [
            "",
            f"**Conclusion:** {pv.conclusion}",
            "",
            f"**Patched workspace:** `{pv.patched_workspace}`" if pv.patched_workspace else "",
            "",
            "## Trace & artifacts",
            "",
            f"- **Run ID:** `{report.traceability.run_id}`",
            f"- **Trace JSONL:** `{report.traceability.trace_file}`",
            f"- **Trace MD:** `{report.traceability.trace_markdown}`",
            f"- **Decision path:** {' → '.join(report.traceability.decision_path)}",
            "",
            "### Generated paths",
            "",
            *[f"- `{p}`" for p in report.traceability.generated_artifacts],
            "",
            f"**Overall confidence:** {report.overall_confidence.score:.2f}",
            "",
            "## Gaps / degradation",
            "",
            *[f"- {n}" for n in report.degradation.notes],
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
