"""Append-only JSONL trace for every tool invocation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.schemas import ToolCallRecord


class TraceWriter:
    def __init__(self, trace_path: Path, run_id: str):
        self.trace_path = trace_path.expanduser().resolve()
        self.run_id = run_id
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: ToolCallRecord) -> None:
        # Re-create parents every append: demo may have cleaned generated/ while another
        # logical run expects the same path, or the traces dir was removed mid-flight.
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        with self.trace_path.open("a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")


def append_tool_dict(trace_path: Path, run_id: str, payload: dict[str, Any]) -> None:
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {**payload, "run_id": run_id}
    with trace_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, default=str) + "\n")
