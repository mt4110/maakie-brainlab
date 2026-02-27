# S29-03 Readiness Notify Multi-channel v2 (Latest)

- CapturedAtUTC: `2026-02-27T11:27:55Z`
- Branch: `ops/S29-01-S29-10`
- HeadSHA: `d968bc83a6767578fffbc56c901cf072f5b33255`

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
