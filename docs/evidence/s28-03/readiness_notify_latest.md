# S28-03 Readiness Notify (Latest)

- CapturedAtUTC: `2026-02-27T08:06:03Z`
- Branch: `ops/S28-01-S28-10`
- HeadSHA: `55d5d962dd6b70a577e42f33ae301a6ab76e4f7d`

## Summary

- status: `WARN`
- reason_code: `NOTIFY_DRY_RUN`
- notify_sent: `False`
- delivery_state: `NOT_ATTEMPTED`
- delivery_rate: `None`
- channel: `#ops-release`

## Message

- payload: `[Ops Readiness] channel=#ops-release | readiness=BLOCKED | status=FAIL | reason=HARD_SLO_VIOLATION | blocked_total=4 | schedule_status=PASS | schedule_reason=`

## PR Body Snippet

```md
### S28-03 Readiness Notify
- status: WARN
- reason_code: NOTIFY_DRY_RUN
- notify_sent: False
- channel: #ops-release
- artifact: docs/evidence/s28-03/readiness_notify_latest.json
```
