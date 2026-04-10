"""Single-file markdown bundle for reviewer handoff."""

from __future__ import annotations

from pathlib import Path

from app.schemas import FinalReport


def write_evidence_pack_md(report: FinalReport, path: Path) -> None:
    pv = report.patch_validation
    rca = report.root_cause_analysis
    lines = [
        "# Evidence pack",
        "",
        "## Bug",
        "",
        f"**{report.bug_summary.title}**",
        "",
        "### High-signal log lines",
        "",
        "```",
        *report.evidence.relevant_log_lines[:25],
        "```",
        "",
        "### Stack trace (excerpt)",
        "",
        "```",
        report.evidence.stack_trace_excerpt[:4000],
        "```",
        "",
        "## Repo signals",
        "",
        f"- **Suspect files:** {', '.join(report.evidence.suspect_files[:15])}",
        f"- **Suspect symbols:** {', '.join(report.evidence.suspect_symbols[:15])}",
        "",
        "## Reproduction",
        "",
        f"- **Artifact:** `{report.reproduction.artifact_path}`",
        f"- **Command:** `{' '.join(report.reproduction.command)}`",
        f"- **Minimization:** {report.reproduction.minimization_result or 'n/a'}",
        "",
        "### Observed failing output (truncated)",
        "",
        "```",
        report.reproduction.observed_output[:3500],
        "```",
        "",
        "## Root cause analysis",
        "",
        f"**Selected:** {rca.selected_hypothesis}",
        "",
        f"**Why:** {rca.why_selected}",
        "",
        "### Hypotheses considered",
        "",
    ]
    for h in rca.considered_hypotheses:
        lines.append(f"#### Rank {h.rank} — {h.status}")
        lines.append(h.hypothesis)
        lines.append("")
        lines.append("- Supporting: " + "; ".join(h.supporting_evidence[:5]))
        lines.append("- Conflicting: " + "; ".join(h.conflicting_evidence[:5]))
        lines.append("")

    lines.extend(
        [
            "## Candidate patch",
            "",
            "Unified diff targets `scheduler.compute_next_window` naive `datetime.now()` → UTC-aware anchor.",
            "",
            "## Patch validation",
            "",
            f"- **Before:** `{pv.before.status}` — `{pv.before.error_signature}`",
            f"- **After:** `{pv.after.status}` — `{pv.after.error_signature}`",
            "",
            "### Regression",
            "",
        ]
    )
    for r in pv.regression_test_results:
        lines.append(f"- **{r.test_id}:** {'PASS' if r.passed else 'FAIL'} — {r.detail[:500]}")
    lines.extend(
        [
            "",
            f"**Conclusion:** {pv.conclusion}",
            "",
            "## Artifacts",
            "",
            f"- Trace JSONL: `{report.traceability.trace_file}`",
            f"- Trace MD: `{report.traceability.trace_markdown}`",
            f"- Final JSON/YAML: under same reports directory as this file",
            "",
            "### All paths",
            "",
            *[f"- `{p}`" for p in report.traceability.generated_artifacts],
            "",
            f"**Overall confidence:** {report.overall_confidence.score:.2f}",
            "",
            "## Degradation / gaps",
            "",
            *[f"- {n}" for n in report.degradation.notes],
            "",
            "### What would increase certainty",
            "",
            *[f"- {n}" for n in report.degradation.what_would_increase_certainty],
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
