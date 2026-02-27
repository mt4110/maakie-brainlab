# S30-02 Quality Burndown (Latest)

- CapturedAtUTC: `2026-02-27T13:54:08Z`
- Branch: `ops/S30-1-S30-900`
- HeadSHA: `4e9cc501523f159c39db9894e1a61549043c6917`

## Summary

- status: `WARN`
- total_checks: `19`
- done_checks: `1`
- remaining_checks: `18`
- waiver_done/total: `0/5`
- risk_done/total: `1/14`

## Checks

- [WARN] WVR-01 (waiver_exit) skip_rate trailing non-pass streak < 3 | target=streak < 3 | observed=3
- [WARN] WVR-02 (waiver_exit) unknown_ratio <= 0.03 | target=<= 0.03 | observed=0.3125
- [WARN] WVR-03 (waiver_exit) notify channels return 2xx at least once | target=all channels attempted+sent with HTTP 2xx | observed={"all_ok": false, "channel_count": 2}
- [WARN] WVR-04 (waiver_exit) recovery_success_rate streak condition | target=streak < 3 | observed=3
- [WARN] WVR-05 (waiver_exit) reliability soak rerun with enough runs | target=total_runs >= 24 and status PASS | observed={"status": "WARN", "total_runs": 3}
- [WARN] RSK-01 (unresolved_risk) skip_rate soft SLO monitor | target=<= 0.15 | observed=1.0
- [WARN] RSK-02 (unresolved_risk) unknown_ratio soft SLO monitor | target=<= 0.03 | observed=0.3125
- [WARN] RSK-03 (unresolved_risk) notify_delivery_rate soft SLO monitor | target=>= 1.0 | observed=0.0
- [WARN] RSK-04 (unresolved_risk) recovery_success_rate soft SLO monitor | target=>= 0.8 | observed=0.0
- [WARN] RSK-05 (unresolved_risk) reliability_total_runs soft SLO monitor | target=>= 24 | observed=3
- [WARN] RSK-06 (unresolved_risk) skip_rate waiver removed | target=waived_hard does not include skip_rate | observed=["notify_delivery_rate", "recovery_success_rate", "reliability_total_runs", "skip_rate", "unknown_ratio"]
- [WARN] RSK-07 (unresolved_risk) unknown_ratio waiver removed | target=waived_hard does not include unknown_ratio | observed=["notify_delivery_rate", "recovery_success_rate", "reliability_total_runs", "skip_rate", "unknown_ratio"]
- [WARN] RSK-08 (unresolved_risk) notify_delivery_rate waiver removed | target=waived_hard does not include notify_delivery_rate | observed=["notify_delivery_rate", "recovery_success_rate", "reliability_total_runs", "skip_rate", "unknown_ratio"]
- [WARN] RSK-09 (unresolved_risk) recovery_success_rate waiver removed | target=waived_hard does not include recovery_success_rate | observed=["notify_delivery_rate", "recovery_success_rate", "reliability_total_runs", "skip_rate", "unknown_ratio"]
- [WARN] RSK-10 (unresolved_risk) reliability_total_runs waiver removed | target=waived_hard does not include reliability_total_runs | observed=["notify_delivery_rate", "recovery_success_rate", "reliability_total_runs", "skip_rate", "unknown_ratio"]
- [WARN] RSK-11 (unresolved_risk) evidence trend warning phases reduced to 0 | target=warn_count == 0 | observed=5
- [WARN] RSK-12 (unresolved_risk) provider env gap skip chronicity resolved | target=env_skip_rate < 0.8 | observed=1.0
- [PASS] RSK-13 (unresolved_risk) retry/backoff tuning validated | target=max_retries>=2 and retry_backoff_sec>=1.0 | observed={"max_retries": 2, "retry_backoff_sec": 1.0}
- [WARN] RSK-14 (unresolved_risk) unknown taxonomy chronic issue resolved | target=unknown_ratio<=0.03 and candidate_count<=2 | observed={"candidate_count": 5, "unknown_ratio": 0.3125}
