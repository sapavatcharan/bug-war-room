"""Unit tests for tools and log parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.tools.extract_stacktrace import extract_stacktrace
from app.tools.search_logs import search_logs
from app.tools.trace import TraceWriter
from app.utils import log_parser
from app.utils.signature import extract_error_signature_from_output


def test_extract_signature_strips_pytest_e_prefix() -> None:
    text = "some line\nE   TypeError: can't compare offset-naive and offset-aware datetimes\n"
    sig = extract_error_signature_from_output(text)
    assert sig.startswith("TypeError:")
    assert "offset-naive" in sig


def test_extract_error_signature_from_sample_log(project_root: Path) -> None:
    log_text = (project_root / "inputs" / "app.log").read_text(encoding="utf-8")
    st = log_parser.extract_stacktrace_lines(log_text)
    assert "Traceback (most recent call last):" in "\n".join(st)
    sig = log_parser.extract_error_signature(st)
    assert "TypeError" in sig
    assert "offset-naive" in sig or "offset-aware" in sig


def test_parse_stack_frames_contains_service(project_root: Path) -> None:
    log_text = (project_root / "inputs" / "app.log").read_text(encoding="utf-8")
    st = log_parser.extract_stacktrace_lines(log_text)
    frames = log_parser.parse_stack_frames(st)
    assert any("service.py" in f.get("path", "") for f in frames)


def test_search_logs_tool(tmp_path: Path, project_root: Path) -> None:
    trace = tmp_path / "t.jsonl"
    tw = TraceWriter(trace, "test")
    logf = project_root / "inputs" / "app.log"
    res = search_logs(tw, logf, patterns=["TypeError", "request_id=8f1e"])
    assert any("TypeError" in ln for ln in res.matches)
    assert trace.exists()


def test_extract_stacktrace_tool(tmp_path: Path, project_root: Path) -> None:
    trace = tmp_path / "t.jsonl"
    tw = TraceWriter(trace, "test")
    res = extract_stacktrace(tw, project_root / "inputs" / "app.log")
    assert res.error_signature
    assert "service.py" in res.excerpt


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent
