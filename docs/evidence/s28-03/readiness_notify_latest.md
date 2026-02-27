# S28-03 Readiness Notify (Latest)

- CapturedAtUTC: `2026-02-27T07:40:33Z`
- Branch: `ops/S28-01-S28-10`
- HeadSHA: `2bf4d6c11a1da872cb4c659a78f64e4486010e0b`

## Summary

- status: `WARN`
- reason_code: `NOTIFY_DRY_RUN`
- notify_sent: `False`
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
