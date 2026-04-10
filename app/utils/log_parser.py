"""Log parsing: stack traces, error signatures, filtering."""

from __future__ import annotations

import re
from pathlib import Path


def read_log_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_stacktrace_lines(log_text: str) -> list[str]:
    lines = log_text.splitlines()
    collecting: list[str] = []
    in_trace = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("Traceback (most recent call last):"):
            in_trace = True
            collecting = [line]
            continue
        if in_trace:
            collecting.append(line)
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*(?:Error|Exception):", stripped):
                break
    return collecting


def extract_error_signature(stack_lines: list[str]) -> str:
    for line in reversed(stack_lines):
        s = line.strip()
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*(?:Error|Exception):", s):
            return s
    return ""


def parse_stack_frames(stack_lines: list[str]) -> list[dict[str, str]]:
    frames: list[dict[str, str]] = []
    file_line = re.compile(
        r'^\s*File "(?P<path>[^"]+)", line (?P<line>\d+), in (?P<func>\S+)\s*$'
    )
    for line in stack_lines:
        m = file_line.match(line)
        if m:
            frames.append(
                {
                    "path": m.group("path"),
                    "line": m.group("line"),
                    "function": m.group("func"),
                }
            )
    return frames


def score_line_signal(line: str, keywords: list[str]) -> int:
    lower = line.lower()
    score = 0
    for kw in keywords:
        if kw.lower() in lower:
            score += 2
    if "error" in lower or "exception" in lower or "traceback" in lower:
        score += 1
    if "warning" in lower and "deprecated" in lower:
        score -= 1
    return score


def filter_high_signal_lines(
    log_text: str,
    keywords: list[str],
    max_lines: int = 40,
) -> list[str]:
    ranked: list[tuple[int, str]] = []
    for line in log_text.splitlines():
        s = score_line_signal(line, keywords)
        if s > 0:
            ranked.append((s, line.rstrip()))
    ranked.sort(key=lambda x: (-x[0], x[1]))
    seen: set[str] = set()
    out: list[str] = []
    for _, ln in ranked:
        if ln not in seen:
            seen.add(ln)
            out.append(ln)
        if len(out) >= max_lines:
            break
    return out


def correlate_frames_to_repo(
    frames: list[dict[str, str]], repo_root: Path
) -> list[str]:
    repo_name = repo_root.name
    hints: list[str] = []
    for fr in frames:
        p = fr.get("path", "")
        if repo_name in p or p.endswith(".py"):
            hints.append(f"{fr.get('function')} @ {p}:{fr.get('line')}")
    return hints
