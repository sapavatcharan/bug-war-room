# Architecture (one page)

## Pipeline stages

1. **LOADED** — `RunContext` + per-run dirs under `generated/<run_id>/`.
2. **TRIAGED** — Parse bug report; seed log keywords.
3. **LOGS_ANALYZED** — Stack excerpt, error signature, correlated lines.
4. **REPO_NAVIGATED** — Suspect files/symbols; regex search over `mini_repo`.
5. **REPRO_ATTEMPTED** — Write pytest repro (+ optional minimization); run pytest.
6. **FIX_PLANNED** — Hypotheses table, patch plan, `candidate_patch.diff`.
7. **PATCH_VALIDATED** — Copy repo → `patch` → same repro + regression on **`patched_workspace/`** only.
8. **REVIEWED** — Secondary repo pass + critique strings.
9. **REPORTED** — `final_report.*`, **`evidence_pack.md`**, **`run_trace.md`**, JSONL trace.

Order is fixed in **`app/orchestrator.py`** (state machine, no dynamic replanning).

## Agent responsibilities

| Agent | Role |
|-------|------|
| **TriageAgent** | Title, symptoms, search keywords |
| **LogAnalystAgent** | Trace + signature + high-signal lines |
| **RepoNavigatorAgent** | Suspects + `search_repo` summaries |
| **ReproductionAgent** | Repro artifacts + pytest |
| **FixPlannerAgent** | Hypotheses, RCA table, diff |
| **ReviewerAgent** | Challenges / edge cases |
| **ReportAgent** | Final JSON schema, evidence pack, trace MD, confidence |

## Tool boundaries

- **Tools** perform I/O: read logs, run subprocesses, write files, append **JSONL** trace rows.
- **Agents** call tools and assemble **handoff** dataclasses; they do not write artifacts directly except via tools.
- **`TraceWriter`** tags each row with **`run_id`**, **`agent_name`**, **`timestamp`**, optional **`command_executed`** / **`files_touched`**.

## Artifact flow

```
inputs/  →  agents  →  tools  →  generated/<run_id>/
                              ├── traces/run_trace.jsonl + run_trace.md
                              ├── repro/
                              ├── patches/candidate_patch.diff
                              ├── patched_workspace/   (validation only)
                              └── reports/final_report.{json,yaml}, evidence_pack.md
```

## Why deterministic orchestration

- **Auditable**: same inputs → same stage order and comparable artifacts.
- **Assessment-friendly**: no hidden LLM path in the default run; reviewers can diff reports and traces.
- **Patch safety**: real `mini_repo/` is untouched unless **`--apply-candidate-patch`** is passed explicitly.

See also **`README.md`** (reviewer-oriented) and **`app/schemas.py`** (canonical field definitions).
