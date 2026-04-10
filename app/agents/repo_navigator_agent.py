"""Map stack frames and symptoms to repository symbols."""

from __future__ import annotations

from pathlib import Path

from app.logger import get_logger
from app.schemas import LogAnalysisOutput, RepoNavigationOutput, RunContext
from app.tools.search_repo import search_repo_tool
from app.tools.trace import TraceWriter
from app.utils.file_search import rg_available

log = get_logger()


class RepoNavigatorAgent:
    def run(
        self,
        ctx: RunContext,
        logs: LogAnalysisOutput,
        tracer: TraceWriter,
    ) -> RepoNavigationOutput:
        tracer.set_agent("RepoNavigatorAgent")
        repo = Path(ctx.repo_path)
        suspect_files: list[str] = []
        symbols: list[str] = []
        hints: list[str] = []
        search_summary: list[str] = []

        for fr in logs.stack_frames:
            p = fr.get("path", "")
            if "service.py" in p:
                suspect_files.append("src/service.py")
                symbols.append(fr.get("function", ""))
            if "scheduler.py" in p:
                suspect_files.append("src/scheduler.py")
            if "parser.py" in p:
                suspect_files.append("src/parser.py")
            hints.append(f"{fr.get('function')} @ {p}:{fr.get('line')}")

        patterns = [
            r"datetime\.now\(",
            r"parse_user_datetime",
            r"compute_next_window",
            r"schedule_reminder",
        ]
        if "naive" in logs.error_signature or "offset" in logs.error_signature:
            patterns.insert(0, r"datetime\.now\(")

        for pat in patterns:
            res = search_repo_tool(tracer, repo, pat, glob="*.py", max_matches=40)
            search_summary.append(res.summary)
            for rel, _ln, line in res.hits[:15]:
                if rel not in suspect_files:
                    suspect_files.append(rel)
                for name in ("parse_user_datetime", "compute_next_window", "schedule_reminder"):
                    if name in line:
                        symbols.append(name)

        suspect_files = list(dict.fromkeys(suspect_files))
        symbols = list(dict.fromkeys(s for s in symbols if s))

        if not symbols:
            symbols = ["schedule_reminder", "compute_next_window", "parse_user_datetime"]

        weak = len(suspect_files) > 6 and len(logs.stack_frames) < 1
        if weak:
            log.warning("[agent] RepoNavigatorAgent: many suspect files but shallow stack mapping")

        if not rg_available():
            log.debug(
                "[agent] RepoNavigatorAgent: ripgrep (rg) not on PATH; using built-in Python search"
            )

        log.info(
            "[agent] RepoNavigatorAgent: suspects=%s",
            ", ".join(suspect_files[:5]),
        )

        return RepoNavigationOutput(
            suspect_files=suspect_files,
            suspect_symbols=symbols,
            frame_to_path_hints=hints,
            search_hits_summary=search_summary,
            degraded_weak_file_evidence=weak,
            degraded_ripgrep_unavailable=not rg_available(),
        )
