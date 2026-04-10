"""Shared tracing wrapper for tools."""

import time
from collections.abc import Callable
from typing import Any, Optional, TypeVar

from app.schemas import ToolCallRecord
from app.tools.trace import TraceWriter

T = TypeVar("T")


def with_trace(
    tracer: TraceWriter,
    tool_name: str,
    input_summary: dict[str, Any],
    action: str,
    fn: Callable[[], T],
) -> T:
    start = time.perf_counter()
    err: Optional[str] = None
    success = True
    out_summary = ""
    try:
        result = fn()
        out_summary = (getattr(result, "summary", None) or str(result))[:800]
        return result
    except Exception as e:
        success = False
        err = f"{type(e).__name__}: {e}"
        out_summary = err
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        tracer.append(
            ToolCallRecord(
                run_id=tracer.run_id,
                tool_name=tool_name,
                input_summary=input_summary,
                action=action,
                output_summary=out_summary[:2000],
                success=success,
                duration_ms=duration_ms,
                error=err,
            )
        )
