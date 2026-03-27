# S30-02 Quality Burndown (Latest)

- CapturedAtUTC: `2026-02-28T09:50:13Z`
- Branch: `ops/dashboardV1`
- HeadSHA: `c211b3df87aa81e7113449dbba2725345f32c39b`

## Summary

- status: `PASS`
- total_checks: `19`
- done_checks: `19`
- remaining_checks: `0`
- waiver_done/total: `5/5`
- risk_done/total: `14/14`

## Checks

- [PASS] WVR-01 (waiver_exit) skip_rate trailing non-pass streak < 3 | target=streak < 3 | observed=0
- [PASS] WVR-02 (waiver_exit) unknown_ratio <= 0.03 | target=<= 0.03 | observed=0.01
- [PASS] WVR-03 (waiver_exit) notify channels return 2xx at least once | target=all channels attempted+sent with HTTP 2xx | observed={"all_ok": true, "channel_count": 2}
- [PASS] WVR-04 (waiver_exit) recovery_success_rate streak condition | target=streak < 3 | observed=0
- [PASS] WVR-05 (waiver_exit) reliability soak rerun with enough runs | target=total_runs >= 24 and status PASS | observed={"status": "PASS", "total_runs": 24}
- [PASS] RSK-01 (unresolved_risk) skip_rate soft SLO monitor | target=<= 0.15 | observed=0.0833
- [PASS] RSK-02 (unresolved_risk) unknown_ratio soft SLO monitor | target=<= 0.03 | observed=0.01
- [PASS] RSK-03 (unresolved_risk) notify_delivery_rate soft SLO monitor | target=>= 1.0 | observed=1.0
- [PASS] RSK-04 (unresolved_risk) recovery_success_rate soft SLO monitor | target=>= 0.8 | observed=1.0
- [PASS] RSK-05 (unresolved_risk) reliability_total_runs soft SLO monitor | target=>= 24 | observed=24
- [PASS] RSK-06 (unresolved_risk) skip_rate waiver removed | target=waived_hard does not include skip_rate | observed=[]
- [PASS] RSK-07 (unresolved_risk) unknown_ratio waiver removed | target=waived_hard does not include unknown_ratio | observed=[]
- [PASS] RSK-08 (unresolved_risk) notify_delivery_rate waiver removed | target=waived_hard does not include notify_delivery_rate | observed=[]
- [PASS] RSK-09 (unresolved_risk) recovery_success_rate waiver removed | target=waived_hard does not include recovery_success_rate | observed=[]
- [PASS] RSK-10 (unresolved_risk) reliability_total_runs waiver removed | target=waived_hard does not include reliability_total_runs | observed=[]
- [PASS] RSK-11 (unresolved_risk) evidence trend warning phases reduced to 0 | target=warn_count == 0 | observed=0
- [PASS] RSK-12 (unresolved_risk) provider env gap skip chronicity resolved | target=env_skip_rate < 0.8 | observed=0.5
- [PASS] RSK-13 (unresolved_risk) retry/backoff tuning validated | target=max_retries>=2 and retry_backoff_sec>=1.0 | observed={"max_retries": 2, "retry_backoff_sec": 1.0}
- [PASS] RSK-14 (unresolved_risk) unknown taxonomy chronic issue resolved | target=unknown_ratio<=0.03 and candidate_count<=2 | observed={"candidate_count": 0, "unknown_ratio": 0.01}
