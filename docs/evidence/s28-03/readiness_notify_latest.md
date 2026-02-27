# S28-03 Readiness Notify (Latest)

- CapturedAtUTC: `2026-02-27T10:16:33Z`
- Branch: `ops/S28-01-S28-10`
- HeadSHA: `2a3af57247941708ebc55133a88ee4900018b6aa`

## Summary

- status: `WARN`
- reason_code: `NOTIFY_DRY_RUN`
- notify_sent: `False`
- delivery_state: `NOT_ATTEMPTED`
- delivery_rate: `None`
- channel: `#ops-release`

## Message

- payload: `[Ops Readiness] channel=#ops-release | readiness=WARN_ONLY | status=WARN | reason=SOFT_SLO_WARN | blocked_total=0 | schedule_status=PASS | schedule_reason=`

## PR Body Snippet

```md
### S28-03 Readiness Notify
- status: WARN
- reason_code: NOTIFY_DRY_RUN
- notify_sent: False
- channel: #ops-release
- artifact: docs/evidence/s28-03/readiness_notify_latest.json
```
