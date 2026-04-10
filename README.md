# bug-war-room

Deterministic **multi-agent CLI** for bug triage: logs → repo search → minimal **pytest repro** → ranked hypotheses → **candidate patch** → **validation on an isolated copy** → structured **`final_report`**, **JSONL trace** (`run_trace.jsonl`), **`run_trace.md`**, and **`evidence_pack.md`**.

Runs **offline** by default (no cloud LLM on the default path). Python **3.9+** (`pyproject.toml`).

## Why this is reviewer-friendly

- **Offline by default** — no API keys required on the default path; deterministic tooling only.  
- **Real generated repro** — pytest artifact under `generated/<run_id>/repro/`, executed during the run.  
- **Isolated patch validation** — candidate diff is applied only under **`patched_workspace/`**; repro and regression re-run there before any claim of “fix verified.”  
- **Evidence-first outputs** — start from **`evidence_pack.md`**, then JSON and trace; paths are echoed at the end of **demo**.

See **`SUBMISSION_GUIDE.md`** for a short reviewer checklist and inspection order.

## Why this submission is stronger than a basic agent demo

| Differentiator | What you get |
|----------------|--------------|
| **Verified patch loop** | Candidate diff is applied only under **`patched_workspace/`**; the **same pytest repro** and **`mini_repo/tests`** run on that copy; results are explicit in **`patch_validation`** (before/after signatures, repro match flags, safety summary, confidence note). |
| **Forensic report** | `evidence.*` includes **error signature**, **exact log lines**, **repo search hit summaries**, and **correlation reasoning**; `reproduction.*` carries **exit code**, **stdout/stderr excerpts**, and **signature match**; `patch_plan.*` lists **functions impacted** and **why_this_fix_matches_the_evidence**. |
| **Rich trace** | Every tool row records **UTC timestamp**, **agent_name**, **command_executed** (when applicable), **files_touched**, duration, and success — JSONL plus an expanded **markdown** table. |
| **Reviewer handoff** | **`evidence_pack.md`** is structured for a **~90 second** read: hypotheses (why two lost), validation narrative, artifact paths, trace pointers. |
| **No magic** | Fixed pipeline in **`orchestrator.py`**; behavior is repeatable without API keys. |

## How offline mode works

All agents use **deterministic** parsing, regex, ripgrep (or Python fallback), and subprocess calls. Variables in **`.env.example`** are optional extensions only — **there is no default LLM completion path** in this codebase.

## Investigation flow

1. **Load** bug report + log paths into `RunContext`.  
2. **Triage** — keywords and title.  
3. **Log analysis** — stack excerpt, signature, high-signal lines.  
4. **Repo navigation** — suspects + `search_repo`.  
5. **Reproduction** — write repro, run pytest (+ optional minimization).  
6. **Fix planning** — top-3 hypotheses, patch plan, `candidate_patch.diff`.  
7. **Patch validation** — copy → `patch` → repro on copy → regression tests.  
8. **Review** — sanity `search_repo` + critique.  
9. **Report** — JSON/YAML/MD summary + **`evidence_pack.md`** + enriched trace MD.

## Demo flow (for reviewers)

1. From the **`bug-war-room`** directory (not a parent folder), activate the venv and run **`./run_demo_and_tests.sh`** (or **`python -m app.main demo`** followed by **`pytest tests/ -v`**).  
2. The CLI **cleans `generated/`** for that demo, runs the **full pipeline** (triage through report), and writes artifacts under **`generated/<run_id>/`**.  
3. **Visible repro:** When patch validation succeeds, the demo **re-runs the same generated pytest file** with **`PYTHONPATH`** / **`BUG_WAR_ROOM_REPO_SRC`** set to **`generated/<run_id>/patched_workspace/src`** — i.e. the **isolated patched copy**, not the tree at repo root. You should see **1 passed** there; that matches what validation already proved.  
4. The terminal then shows the **summary table**, **patch validation conclusion**, and **Reviewer snapshot** with paths to **`final_report.json`**, **`evidence_pack.md`**, and traces.  
5. **Root `mini_repo/`** (at the repository root) remains **intentionally unpatched** and still contains the bug for inspection and for the assignment scenario. It is **not** modified by validation. The only way to patch that root copy is to run **`python -m app.main run --apply-candidate-patch`** explicitly.

## Architecture at a glance

```
                    ┌─────────────┐
                    │ Typer CLI   │
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │ Orchestrator │  (fixed stage order)
                    └──────┬──────┘
     Triage → LogAnalyst → RepoNav → Repro → FixPlanner
                           → PatchValidation (temp copy)
                           → Reviewer → ReportAgent
                           ▼
              generated/<run_id>/  (traces, repro, patches, reports)
```

See **`ARCHITECTURE.md`** for stage names, agent/tool boundaries, and artifact flow.

## How repro generation works

- **Primary** pytest module resolves `mini_repo/src` via `Path(__file__).parents[...]` **or** obeys **`BUG_WAR_ROOM_REPO_SRC`** (used during patch validation).  
- **Minimized** sibling is kept only if it preserves the **same failure class** and has **fewer lines**.  
- **Fallback** standalone script if pytest does not fail as expected.

## How patch validation works

1. **`shutil.copytree`** of `mini_repo` → `generated/<run_id>/patched_workspace`.  
2. **`patch -p1`** applies **`candidate_patch.diff`** on that copy only.  
3. **Same** pytest argv as documented in **`patch_validation.repro_command`**, with **`BUG_WAR_ROOM_REPO_SRC`** pointing at the copy’s `src`.  
4. **`pytest`** on **`mini_repo/tests`** inside the copy.  
5. Report records **repro_match_before/after**, **original_failure_resolved**, **failure_changed_after_patch**, **safety_summary**, and **confidence_note**.

## Where to inspect evidence quickly

| File | Purpose |
|------|---------|
| **`generated/<run_id>/reports/evidence_pack.md`** | **Start here** — single narrative for reviewers. |
| **`generated/<run_id>/reports/final_report.json`** | Full schema: evidence, reproduction, patch_plan, patch_validation, traceability.tool_calls. |
| **`generated/<run_id>/traces/run_trace.md`** | Human-readable tool table (timestamp, agent, command). |
| **`generated/<run_id>/traces/run_trace.jsonl`** | Auditable machine trace. |

## Quick start

Run these **from inside `bug-war-room`** (clone path may differ; adjust `cd`).

```bash
cd bug-war-room
chmod +x setup.sh run_demo_and_tests.sh
./setup.sh
source .venv/bin/activate
./run_demo_and_tests.sh
```

After **`./setup.sh`**, you can skip it on later runs if `.venv` already exists.

**What to expect:** **`demo`** finishes with a visible pytest run (**1 passed** when validation used **`patched_workspace`**), then **`pytest tests/ -v`** reports **18 passed** for the project test suite.

**Paste safety (zsh):** Use only the lines inside the block above. Do not paste prose or parenthetical lines into the shell. If a line in chat starts with `#`, your shell may try to run it as a command — omit those lines.

To run the test suite alone (optional):

```bash
cd bug-war-room
source .venv/bin/activate
pytest tests/ -v
```

## Commands

| Command | Purpose |
|---------|---------|
| `python -m app.main demo` | Clean `generated/`, full run, tables + **Reviewer snapshot** panel |
| `python -m app.main run --bug-report inputs/bug_report.md --log-file inputs/app.log --repo-path mini_repo` | Full pipeline |
| `python -m app.main test-repro` | Re-run repro from last report |
| `python -m app.main clean --yes` | Remove generated run dirs |
| `python -m app.main run --apply-candidate-patch` | Apply patch to **root** `mini_repo` (optional; mutates the bundled scenario) |

## Bundled scenario (`mini_repo`)

Timezone bug: **`scheduler.py`** uses naive `datetime.now()`; **`parser.py`** yields aware UTC for `Z` ISO strings; **`service.py`** compares them → `TypeError`. **`config.py`** carries deploy markers; **`inputs/app.log`** includes deploy line, **feature-flag** and **slow-query** red herrings off the crash path.

## Environment

Optional keys: **`.env.example`**. `BUG_WAR_ROOM_REPO_SRC` is set internally during patch validation.

## Tests

```bash
cd bug-war-room
source .venv/bin/activate
pytest tests/ -v
```

## Limitations

Sequential pipeline only; **`patch`** binary required for validation; stack parsing assumes **CPython** tracebacks; regression is **`mini_repo/tests`** only.

## Future extensions

Optional LLM rewrite of narrative fields with guardrails; AST/dataflow for stronger repo alignment; JUnit/SARIF export for CI.

## License

Submission / portfolio use unless otherwise specified.
