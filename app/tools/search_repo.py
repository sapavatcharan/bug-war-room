"""Search repository source for regex patterns."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.tools._helpers import with_trace
from app.tools.trace import TraceWriter
from app.utils.file_search import search_repo as fs_search


@dataclass
class SearchRepoResult:
    hits: list[tuple[str, int, str]]
    summary: str


def search_repo_tool(
    tracer: TraceWriter,
    repo_root: Path,
    pattern: str,
    glob: str = "*.py",
    max_matches: int = 100,
) -> SearchRepoResult:
    def _run() -> SearchRepoResult:
        hits = fs_search(repo_root, pattern, glob=glob, max_matches=max_matches)
        summary = f"{len(hits)} hit(s) for /{pattern}/ in {repo_root.name}"
        return SearchRepoResult(hits=hits, summary=summary)

    touched = [str(repo_root.resolve())]
    return with_trace(
        tracer,
        "search_repo",
        {
            "repo_root": str(repo_root),
            "pattern": pattern,
            "glob": glob,
            "max_matches": max_matches,
        },
        "regex_search",
        _run,
        command_executed=f"scan_repo pattern={pattern!r} glob={glob}",
        files_touched=touched,
    )
