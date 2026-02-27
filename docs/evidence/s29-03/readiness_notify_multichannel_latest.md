# S29-03 Readiness Notify Multi-channel v2 (Latest)

- CapturedAtUTC: `2026-02-27T11:50:23Z`
- Branch: `ops/S29-01-S29-10`
- HeadSHA: `2971732a2c6df3a57166589d92e528ab65e49038`

## Summary

- status: `WARN`
- reason_code: `NOTIFY_SEND_FAILED`
- notify_sent: `False`
- delivery_state: `FAILED`
- delivery_rate: `0.0`
- attempted_channels: `2`
- sent_channels: `0/2`

## Channels

- channel=`#ops-release` state=`FAILED` attempted=`True` sent=`False`
- channel=`#ops-oncall` state=`FAILED` attempted=`True` sent=`False`

## PR Body Snippet

```md
### S29-03 Readiness Notify Multi-channel v2
- status: WARN
- reason_code: NOTIFY_SEND_FAILED
- notify_sent: False
- attempted_channels: 2
- sent_channels: 0/2
- artifact: docs/evidence/s29-03/readiness_notify_multichannel_latest.json
```
