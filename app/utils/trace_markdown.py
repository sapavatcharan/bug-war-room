"""Human-readable trace from JSONL tool records."""

from __future__ import annotations

import json
from pathlib import Path


def write_run_trace_markdown(trace_jsonl: Path, out_md: Path) -> None:
    lines: list[str] = [
        "# Tool execution trace",
        "",
        f"_Source: `{trace_jsonl.name}`_",
        "",
        "| # | Tool | Action | Success | ms | Summary |",
        "|---|------|--------|---------|-----|---------|",
    ]
    if not trace_jsonl.exists():
        out_md.write_text("\n".join(lines + ["", "_No trace records._"]), encoding="utf-8")
        return

    n = 0
    with trace_jsonl.open(encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            n += 1
            tool = rec.get("tool_name", "?")
            action = rec.get("action", "")
            ok = rec.get("success", False)
            ms = rec.get("duration_ms", 0)
            summ = str(rec.get("output_summary", ""))[:120].replace("|", "\\|")
            lines.append(f"| {n} | `{tool}` | {action} | {ok} | {ms:.1f} | {summ} |")

    lines.append("")
    lines.append(f"**Total tool calls:** {n}")
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines), encoding="utf-8")
