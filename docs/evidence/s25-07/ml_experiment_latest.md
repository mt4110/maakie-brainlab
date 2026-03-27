# S25-07 ML Experiment (Latest)

- CapturedAtUTC: `2026-02-28T09:50:13.878670+00:00`
- Branch: `ops/dashboardV1`
- HeadSHA: `c211b3df87aa81e7113449dbba2725345f32c39b`
- ExperimentId: `s25-07-il-compile-bench-v1`
- Seed: `7`

## Metrics

- Status: `PASS`
- Duration: `0.038 sec`
- BenchRC: `0`
- Failures: `0`

## Threshold Checks

- `PASS` `expected_match_rate` `actual=1.0` `>= 1.0`
- `PASS` `reproducible_rate` `actual=1.0` `>= 1.0`
- `PASS` `il_validity_rate` `actual=1.0` `>= 0.8`
- `PASS` `objective_score` `actual=1.0` `>= 0.9`

## PR Body Snippet

```md
### S25-07 ML Experiment Loop
- template: docs/ops/S25-07_ML_EXPERIMENT_TEMPLATE.json
- seed: 7
- status: PASS
- duration: 0.038 sec
- failures: 0
- artifact: docs/evidence/s25-07/ml_experiment_latest.json
```
