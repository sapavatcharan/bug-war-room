# Mini repository (intentional defect)

Sample **reminder-svc** layout used by **bug-war-room**: config/deploy markers, JSON payload layer, and a scheduling core with a deliberate datetime bug.

## Layout

| Path | Role |
|------|------|
| `src/config.py` | Service name, image tag, feature flags (no secrets). |
| `src/models.py` | `ReminderDispatchRequest` dataclass. |
| `src/payloads.py` | `build_reminder_request` — normalizes JSON bodies. |
| `src/parser.py` | ISO-8601; `Z` → **timezone-aware** UTC. |
| `src/scheduler.py` | `compute_next_window` uses **`datetime.now()`** (naive) when `now` omitted. |
| `src/service.py` | `schedule_reminder` / `schedule_reminder_from_payload`. |

## Bug

Ordering `user_dt < next_win` raises **`TypeError: can't compare offset-naive and offset-aware datetimes`** when the user string ends with `Z`.

## Tests

- `tests/test_scheduler_smoke.py` — explicit `now` (passes before/after patch).
- `tests/test_config_smoke.py` — deploy marker string stable.
- `tests/test_reminder_payload_smoke.py` — payload path with **`Z`** suffix (passes once scheduler uses UTC-aware default `now`).

## Local repro

```bash
PYTHONPATH=src python -c "from service import schedule_reminder; schedule_reminder('2026-04-10T15:00:00Z')"
```
