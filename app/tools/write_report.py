"""Write final report as JSON, YAML, and Markdown summary."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import yaml

from app.schemas import FinalReport
from app.tools._helpers import with_trace
from app.tools.trace import TraceWriter


@dataclass
class WriteReportResult:
    json_path: Path
    yaml_path: Path
    md_path: Path
    summary: str


def write_report_files(
    tracer: TraceWriter,
    report: FinalReport,
    reports_dir: Path,
    base_name: str = "final_report",
) -> WriteReportResult:
    def _run() -> WriteReportResult:
        reports_dir.mkdir(parents=True, exist_ok=True)
        jp = reports_dir / f"{base_name}.json"
        yp = reports_dir / f"{base_name}.yaml"
        mp = reports_dir / f"{base_name}_summary.md"

        data = report.model_dump(mode="json")
        jp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        yp.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")

        oc = report.overall_confidence
        comp = oc.components
        md = "\n".join(
            [
                "# bug-war-room run summary",
                "",
                f"**Title:** {report.bug_summary.title}",
                "",
                f"**Overall confidence:** {oc.score:.2f}",
                "",
                "**Component contributions:** "
                f"trace={comp.stack_trace_match:.2f} log={comp.log_signal_quality:.2f} "
                f"repo={comp.repo_alignment:.2f} repro={comp.repro_match:.2f} "
                f"patch_val={comp.patch_validation:.2f} reviewer={comp.reviewer_penalty:.2f}",
                "",
                f"**Why not higher:** {oc.why_not_higher}",
                "",
                "## Patch validation",
                "",
                f"- Before: `{report.patch_validation.before.status}`",
                f"- After: `{report.patch_validation.after.status}`",
                f"- Conclusion: {report.patch_validation.conclusion}",
                "",
                "## Reproduction",
                "",
                f"- Status: {report.reproduction.status}",
                f"- Artifact: `{report.reproduction.artifact_path}`",
                f"- Minimization: {report.reproduction.minimization_result or 'n/a'}",
                f"- Command: `{' '.join(report.reproduction.command)}`",
                "",
                "## Root cause (hypothesis)",
                "",
                report.root_cause_hypothesis.summary,
                "",
                "## Evidence bundle",
                "",
                "- `evidence_pack.md` (same directory)",
                f"- Trace MD: `{report.traceability.trace_markdown}`",
                f"- JSONL: `{report.traceability.trace_file}`",
                "",
            ]
        )
        mp.write_text(md, encoding="utf-8")
        summary = f"reports -> {jp.name}, {yp.name}, {mp.name}"
        return WriteReportResult(
            json_path=jp, yaml_path=yp, md_path=mp, summary=summary
        )

    return with_trace(
        tracer,
        "write_report",
        {"reports_dir": str(reports_dir), "base_name": base_name},
        "write_json_yaml_md",
        _run,
    )
