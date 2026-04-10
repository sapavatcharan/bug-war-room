# bug-war-room

Production-oriented **multi-agent CLI** for triaging a bug report, analyzing logs, searching a codebase, generating and running a **minimal failing reproduction**, **ranking hypotheses**, producing a **root-cause analysis**, **safe patch plan**, **candidate patch (diff)**, **verified patch validation on an isolated repo copy**, and **structured reports** plus **JSONL traces**, **`run_trace.md`**, and **`evidence_pack.md`**.

Designed for assessment review: **deterministic orchestration**, **programmatic tool calls**, **required execution**, **weighted confidence with explicit components**, **graceful degradation**, and **no API keys** in the default path.

## Why this submission is stronger than a basic agent demo

| Differentiator | What you get |
|----------------|--------------|
| **Verified patch loop** | Candidate diff is applied to a **temporary copy** of `mini_repo`, the **same repro** is re-run with `BUG_WAR_ROOM_REPO_SRC`, and **regression tests** execute on that copy—reported as `patch_validation.*`. |
| **Hypothesis discipline** | Top **3** hypotheses with **supporting vs conflicting evidence**, **status** (selected / rejected / downgraded), and an explicit **`why_selected`** narrative—not a single hand-wavy root cause. |
| **Deliberate repro** | Primary pytest repro plus an optional **minimized** second file; the pipeline **compares** line count and **same failure class** before keeping the smaller artifact. |
| **Evidence pack** | One **`evidence_pack.md`** surfaces logs, stack, suspects, repro, validation, and artifact paths for a **under-two-minute** reviewer read. |
| **Weighted confidence** | `overall_confidence.components` breaks down **stack / logs / repo / repro / patch validation / reviewer penalty** instead of a single opaque score. |
| **Safe degradation** | Missing stack, missing `rg`, failed patch apply, weak repo evidence—**logged**, **confidence reduced**, **report still emitted** with `degradation.*`. |

## Investigation flow

1. **Load** bug report + log paths into `RunContext`.
2. **Triage** — parse report, seed `search_logs`.
3. **Log analysis** — `extract_stacktrace`, high-signal lines, red-herring callouts.
4. **Repo navigation** — `search_repo` (ripgrep or Python fallback).
5. **Reproduction** — `write_repro` + `run_pytest` (+ optional minimization + `run_script` fallback).
6. **Fix planning** — ranked hypotheses table, patch plan, `candidate_patch.diff`.
7. **Patch validation** — `copy` → `patch` → repro on copy → `pytest` on `mini_repo/tests`.
8. **Review** — `search_repo` sanity check + critique.
9. **Report** — JSON/YAML/summary MD + **`evidence_pack.md`** + **`run_trace.md`**.

## How offline mode works

All agents use **deterministic** string extraction, regex, ripgrep/Python search, and subprocess execution. Optional env keys in `.env.example` are **not** used to call cloud models in this codebase. There is **no** hidden LLM completion path in the default run.

## How repro generation works

- **Primary** pytest file: resolves `mini_repo/src` via `Path(__file__).parents[...]` **or** obeys **`BUG_WAR_ROOM_REPO_SRC`** when set (used by patch validation).
- **Minimized** sibling test: shorter module; adopted only if it **still** raises the same **TypeError / offset-naive|aware** class and is **smaller** by line count.
- **Fallback** standalone script if pytest does not fail as expected.

## How patch validation works

1. `shutil.copytree` the original `mini_repo` to `generated/<run_id>/patched_workspace` (ignores `__pycache__`, `.git`).
2. `patch -p1` applies `candidate_patch.diff` **only** on that copy.
3. The **same** repro test is executed with `BUG_WAR_ROOM_REPO_SRC=<copy>/src`.
4. `pytest -q mini_repo/tests` runs on the copy with `PYTHONPATH` set.
5. `final_report.patch_validation` records **before/after status + error signatures**, **regression_test_results**, and a **conclusion**.

Original `mini_repo` is untouched unless you pass **`--apply-candidate-patch`** to `run`.

## Where to inspect evidence quickly

| File | Purpose |
|------|---------|
| `generated/<run_id>/reports/evidence_pack.md` | **Start here** — full narrative + paths. |
| `generated/<run_id>/reports/final_report.json` | Machine-readable; includes `root_cause_analysis`, `patch_validation`, `overall_confidence.components`. |
| `generated/<run_id>/traces/run_trace.md` | Human-readable tool call table from JSONL. |
| `generated/<run_id>/traces/run_trace.jsonl` | Raw tool I/O audit trail. |

## Why this design (engineering choices)

| Choice | Rationale |
|--------|-----------|
| **State-machine orchestrator** | One file (`app/orchestrator.py`), fixed order, easy audit. |
| **Agents vs tools** | Side effects and tracing live in **tools** only. |
| **Per-run directories** | `generated/<run_id>/` isolates artifacts. |
| **Ripgrep + fallback** | Fast when available; deterministic Python scan otherwise. |

## Architecture

```
 CLI (Typer) → Orchestrator
      → Triage → LogAnalyst → RepoNav → Repro → FixPlanner
      → PatchValidation (temp copy + patch + repro + regression)
      → Reviewer → Report (+ evidence_pack + run_trace.md)
```

## Agent responsibilities

| Agent | Role | Tools |
|-------|------|--------|
| **TriageAgent** | Parse report; keywords | `search_logs` |
| **LogAnalystAgent** | Trace + signature | `search_logs`, `extract_stacktrace` |
| **RepoNavigatorAgent** | Suspects | `search_repo` |
| **ReproductionAgent** | Repro + minimization | `write_repro`, `run_pytest`, `run_script` |
| **FixPlannerAgent** | Hypotheses + plan + diff | `search_repo`, `write_repro` |
| **ReviewerAgent** | Critique | `search_repo` |
| **ReportAgent** | Reports + bundles | `write_report` |

## The bundled scenario (`mini_repo`)

- **`config.py`** — service name, **deploy image tag** (surfaced in sample log).
- **`models.py`** / **`payloads.py`** — request payload layer (`ReminderDispatchRequest`, `build_reminder_request`).
- **`parser.py`** — `Z` → timezone-aware UTC.
- **`scheduler.py`** — naive `datetime.now()` when `now` omitted (**intentional bug**).
- **`service.py`** — compares user instant vs window; JSON entrypoint `schedule_reminder_from_payload`.
- **Tests** — scheduler smoke + config smoke + payload path with **`Z`** suffix (passes after patch when scheduler is UTC-aware).

`inputs/app.log` includes **deploy marker**, **misleading feature-flag line**, **slow query**, and **deprecation** noise not on the crash path.

## Setup

**Python:** 3.9+ required (`pyproject.toml`); 3.11+ optional.

**Easiest (no fragile copy-paste):** from `bug-war-room`, run `./run_demo_and_tests.sh` (creates `.venv` if missing, runs `demo`, then `pytest`).

```bash
cd bug-war-room
chmod +x setup.sh run_demo_and_tests.sh
./setup.sh
source .venv/bin/activate
```

Manual venv instead of `./setup.sh`: `python3.11 -m venv .venv` or `python3 -m venv .venv`, then `source .venv/bin/activate` and `pip install -r requirements.txt`.

**zsh tip:** If you paste instructions from chat, do not paste prose lines that contain `( ... )` unless the whole line is a shell comment starting with `#`. Otherwise zsh treats parentheses as **globs** and you may see `no matches found: (...)`.

## Commands

```bash
python -m app.main demo

python -m app.main run \
  --bug-report inputs/bug_report.md \
  --log-file inputs/app.log \
  --repo-path mini_repo

python -m app.main test-repro
python -m app.main clean --yes
python -m app.main run --apply-candidate-patch
```

## Sample artifact paths

| Artifact | Pattern |
|----------|---------|
| Trace JSONL | `generated/<run_id>/traces/run_trace.jsonl` |
| Trace MD | `generated/<run_id>/traces/run_trace.md` |
| Repro | `generated/<run_id>/repro/test_repro_*.py` |
| Reports | `generated/<run_id>/reports/final_report.{json,yaml}`, `_summary.md`, **`evidence_pack.md`** |
| Patch | `generated/<run_id>/patches/candidate_patch.diff` |
| Validation copy | `generated/<run_id>/patched_workspace/` |
| Last run | `generated/LAST_RUN.txt` |

## Sample terminal run (`python -m app.main demo`)

```
— Cleaned generated/ —
INFO  run_id=20260410T...
INFO  TriageAgent: Reminder API 500 when client sends ISO timestamps with `Z` suffix (6 log hits)
INFO  LogAnalystAgent: signature="TypeError: can't compare offset-naive and offset-aware datetimes"
INFO  ReproductionAgent: status=success exit=1 min=adopted_minimal: ...
INFO  FixPlannerAgent: wrote candidate_patch.diff
INFO  ReportAgent: final_report + evidence_pack + run_trace.md written

[repro artifact] .../generated/<run_id>/repro/test_repro_minimal_typeerror.py
— Visible repro: same test against isolated patched_workspace (expect pass) —
... test_z_iso_typeerror PASSED ...

╭ Visible repro ───────────────╮
│ Repro passed on patched_workspace (matches patch validation). │
│ Root mini_repo/ is still unpatched unless you use run --apply-candidate-patch. │
╰──────────────────────────────╯

┌ decision ┬ fix_candidate_validated_under_isolated_copy ┐
┌ regression ┬ mini_repo_tests:OK ┐
└ final_report.json / evidence_pack.md / run_trace.md paths shown in table ┘
```

## Optional environment variables

See `.env.example` (`MODEL_PROVIDER=local`, optional API keys for future extension). **`BUG_WAR_ROOM_REPO_SRC`** is set internally during patch validation; you normally do not set it by hand.

## Tests

```bash
pytest tests/ -v
```

Includes: tools, orchestrator, end-to-end, **confidence weights**, **patch validation fix**, **evidence line anchoring**, **repro minimization**, **degraded patch path**, pipeline degradation monkeypatch.

## Known limitations

- **Repo search** uses **ripgrep** (`rg`) when it is on `PATH`; otherwise a **built-in Python scan** (same results, slower). Install: `brew install ripgrep` (macOS).
- **Sequential** pipeline only.
- **Patch validation** requires a POSIX `patch` binary.
- **Log parsing** assumes CPython tracebacks for stack extraction.
- **Regression** runs the bundled `mini_repo/tests` suite—not your production suite.
- After the scheduler fix, **naive** ISO strings without timezone still risk comparison issues; production code would normalize both sides—out of scope for this miniature repo.

## Future extensions

- Optional LLM rewrite of `why_selected` with guardrails.
- AST/dataflow layer for stronger `repo_alignment` scoring.
- JUnit/SARIF export for CI dashboards.

## Submission checklist (before you zip or push)

- [ ] `./setup.sh` (or `python3.11 -m venv .venv` / `python3 -m venv .venv` + `pip install -r requirements.txt`)
- [ ] `./run_demo_and_tests.sh` **or** `pytest tests/ -v` then `python -m app.main demo` — all green; demo table shows `mini_repo_tests:OK`
- [ ] Open `generated/.../reports/evidence_pack.md` and skim in under two minutes
- [ ] Confirm `mini_repo/` is unpatched unless you intentionally used `--apply-candidate-patch`
- [ ] No `.env` with real secrets committed (use `.env.example` only)

## License

Submission / portfolio use unless otherwise specified.
