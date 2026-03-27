# S25-08 RAG Tuning Loop (Latest)

- CapturedAtUTC: `2026-03-04T04:12:49Z`
- Branch: `ops/dashboardV1`
- HeadSHA: `c211b3df87aa81e7113449dbba2725345f32c39b`
- Config: `docs/ops/S25-08_RAG_TUNING.toml`

## Comparison

- Status: `PASS`
- delta_hit_rate: `0.0`
- delta_latency_ms: `-0.212`
- min_hit_rate_delta: `-0.05`

## Baseline Metrics

- hit_rate: `1.0`
- avg_latency_ms: `0.723`
- chunk_size/overlap/top_k: `1200/200/1`

## Candidate Metrics

- hit_rate: `1.0`
- avg_latency_ms: `0.511`
- chunk_size/overlap/top_k: `800/100/3`

## PR Body Snippet

```md
### S25-08 RAG Tuning Loop
- status: PASS
- baseline_hit_rate: 1.0
- candidate_hit_rate: 1.0
- delta_hit_rate: 0.0
- delta_latency_ms: -0.212
- artifact: docs/evidence/s25-08/rag_tuning_latest.json
```
