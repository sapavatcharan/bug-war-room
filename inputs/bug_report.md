# Reminder API 500 when client sends ISO timestamps with `Z` suffix

## Summary

Production requests that include UTC ISO-8601 strings ending in `Z` intermittently crash the
reminder scheduling path with a 500 error. The same payload without `Z` (local naive string)
appears to succeed in staging.

## Severity

High — customer-facing scheduling endpoint returns 500; retries amplify load.

## Environment

- Python 3.11.8 on Linux (container)
- Service: `reminder-scheduler` v0.4.2
- Region: `us-east-1`

## Expected behavior

The API should accept RFC3339/ISO-8601 timestamps with a `Z` UTC designator, normalize them
consistently, and return `200` with a scheduled window.

## Actual behavior

The worker throws `TypeError: can't compare offset-naive and offset-aware datetimes` while
handling the request. Clients see HTTP 500.

## Reproduction hints

1. Call `POST /v1/reminders` with body containing `"fire_at": "2026-04-10T15:00:00Z"`.
2. Observe worker log for traceback through `service.schedule_reminder`.
3. Compare with naive timestamp without timezone suffix — staging path does not crash.

## Notes

- Redis slow-query warnings appear in the same minute but correlate with unrelated batch jobs.
- Deprecation warning for `legacy_auth_header` is noisy but pre-dates this regression.
