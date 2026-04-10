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
        "| # | Time (UTC) | Agent | Tool | Action | Cmd / touched | OK | ms | Summary |",
        "|---|------------|-------|------|--------|---------------|----|-----|---------|",
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
            ts = str(rec.get("timestamp", ""))[:19]
            agent = str(rec.get("agent_name", "")).replace("|", "\\|")[:24]
            cmd = rec.get("command_executed") or ""
            ft = rec.get("files_touched") or []
            extra = cmd[:60] if cmd else ""
            if not extra and ft:
                extra = str(ft[0])[:60] if ft else ""
            extra = extra.replace("|", "\\|")
            summ = str(rec.get("output_summary", ""))[:100].replace("|", "\\|")
            lines.append(
                f"| {n} | {ts} | {agent} | `{tool}` | {action} | {extra} | {ok} | {ms:.1f} | {summ} |"
            )

    lines.append("")
    lines.append(f"**Total tool calls:** {n}")
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines), encoding="utf-8")
