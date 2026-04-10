"""Load structured rows from run_trace.jsonl for reports and summaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_tool_call_rows(trace_jsonl: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not trace_jsonl.exists():
        return rows
    with trace_jsonl.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.append(
                {
                    "timestamp": rec.get("timestamp", ""),
                    "run_id": rec.get("run_id", ""),
                    "agent_name": rec.get("agent_name", ""),
                    "tool_name": rec.get("tool_name", ""),
                    "action": rec.get("action", ""),
                    "success": rec.get("success"),
                    "duration_ms": rec.get("duration_ms"),
                    "command_executed": rec.get("command_executed"),
                    "files_touched": rec.get("files_touched") or [],
                    "output_summary": str(rec.get("output_summary", ""))[:400],
                    "error": rec.get("error"),
                }
            )
    return rows
