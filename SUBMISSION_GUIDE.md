# Submission guide (reviewers)

**bug-war-room** is a small, offline-by-default CLI that walks a fixed pipeline from bug report + logs → minimal pytest repro → ranked hypotheses → candidate unified diff → **verified apply + repro + regression on an isolated copy** of the bundled `mini_repo`, then writes **`evidence_pack.md`**, **`final_report.json`**, and **`run_trace.*`** under `generated/<run_id>/`.

## Setup

```bash
cd bug-war-room
chmod +x setup.sh run_demo_and_tests.sh
./setup.sh
source .venv/bin/activate
```

## Run (recommended)

```bash
./run_demo_and_tests.sh
```

That runs the full **demo** (pipeline + visible repro + summary panels) and then **`pytest tests/ -v`**. Expect **18** tests passed and **1** passed on the demo’s visible repro when patch validation succeeds.

## Look here first

Open the newest run’s **`generated/<run_id>/reports/evidence_pack.md`** — it is the single-file narrative for the run.

## Suggested inspection order

1. **`reports/evidence_pack.md`** — story, evidence, hypotheses, validation, paths  
2. **`reports/final_report.json`** — full structured report (evidence, reproduction, patch_validation, traceability)  
3. **`traces/run_trace.md`** — tool calls (agent, timestamp, commands)  
4. **`patches/candidate_patch.diff`** — candidate fix as a unified diff  

## `patched_workspace` vs root `mini_repo`

- **`generated/<run_id>/patched_workspace/`** — temporary copy where the candidate patch is applied and repro/regression run. Safe to inspect; thrown away on the next clean run.  
- **`mini_repo/`** at the **repository root** — the **intentional buggy sample**; it stays unpatched unless you explicitly run `python -m app.main run --apply-candidate-patch`.

For more detail, see **`README.md`** and **`ARCHITECTURE.md`**.
