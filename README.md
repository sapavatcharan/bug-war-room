# bug-war-room

Deterministic **multi-agent CLI** for bug triage: logs → repo search → minimal **pytest repro** → ranked hypotheses → **candidate patch** → **validation on an isolated copy** → JSON/YAML reports, **JSONL trace**, **`run_trace.md`**, and **`evidence_pack.md`**.

Runs **offline** by default (no cloud LLM on the default path). Python **3.9+** (`pyproject.toml`).

## Quick start

```bash
cd bug-war-room
chmod +x setup.sh run_demo_and_tests.sh && ./setup.sh
source .venv/bin/activate
./run_demo_and_tests.sh
```

Creates `.venv` if needed, runs **`demo`** (full pipeline + visible repro), then **`pytest`**. Expect **1 passed** on the visible repro (patched copy) and **12 passed** on the suite.

**zsh:** Don’t paste prose lines with `( ... )` unless they start with `#`, or you may get `no matches found`.

## Commands

| Command | Purpose |
|---------|---------|
| `python -m app.main demo` | Clean `generated/`, full run, summary table |
| `python -m app.main run --bug-report inputs/bug_report.md --log-file inputs/app.log --repo-path mini_repo` | Full pipeline |
| `python -m app.main test-repro` | Re-run repro from last report |
| `python -m app.main clean --yes` | Remove generated run dirs |
| `python -m app.main run --apply-candidate-patch` | Apply patch to **root** `mini_repo` (optional) |

## What you get

| Area | Detail |
|------|--------|
| Patch loop | Copy `mini_repo` → `patch` → same repro with `BUG_WAR_ROOM_REPO_SRC` → `mini_repo/tests` on copy → `patch_validation` in report |
| Repro | Primary pytest + optional **minimized** test if same failure class and smaller |
| Report | Top **3** hypotheses (evidence / conflicts / status), weighted `overall_confidence.components`, `degradation` notes |
| Evidence | **`evidence_pack.md`** for a quick reviewer read |
| Search | **`rg`** if on `PATH`; else built-in Python scan (macOS: `brew install ripgrep` for speed) |

Pipeline order: **Triage → LogAnalyst → RepoNav → Repro → FixPlanner → PatchValidation → Reviewer → Report** (`app/orchestrator.py`). Agents live under `app/agents/`; side effects and tracing under `app/tools/`.

## Artifacts (under `generated/<run_id>/`)

| Path | Use |
|------|-----|
| `reports/evidence_pack.md` | **Start here** |
| `reports/final_report.json` | Machine-readable (RCA, patch validation, confidence) |
| `traces/run_trace.md` / `run_trace.jsonl` | Tool audit |
| `repro/test_repro_*.py` | Generated repro tests |
| `patches/candidate_patch.diff` | Candidate patch |
| `patched_workspace/` | Isolated copy used for validation |

## Bundled scenario (`mini_repo`)

Timezone bug: **`scheduler.py`** uses naive `datetime.now()`; **`parser.py`** yields aware UTC for `Z` ISO strings; **`service.py`** compares them → `TypeError`. Sample noise in `inputs/app.log`. Root **`mini_repo/`** stays unpatched unless you use `--apply-candidate-patch`.

## Environment

Optional keys: **`.env.example`**. `BUG_WAR_ROOM_REPO_SRC` is set internally during patch validation.

## Tests

```bash
pytest tests/ -v
```

## Limitations

Sequential pipeline only; **`patch`** binary required for validation; stack parsing assumes **CPython** tracebacks; regression is **`mini_repo/tests`** only.

## Submission checklist

- [ ] `./setup.sh` (or `python3.11` / `python3` venv + `pip install -r requirements.txt`)
- [ ] `./run_demo_and_tests.sh` — suite green; demo table shows `mini_repo_tests:OK` / `repro_passed_patch_verified`
- [ ] Skim `generated/.../reports/evidence_pack.md`
- [ ] Root `mini_repo/` unpatched unless you chose `--apply-candidate-patch`
- [ ] No secrets in `.env` committed (keep `.env.example` only)

## License

Submission / portfolio use unless otherwise specified.
