# S25-08 RAG Tuning Loop (Latest)

- CapturedAtUTC: `2026-02-27T01:15:35Z`
- Branch: `ops/S25-01-25-10`
- HeadSHA: `ae5c5b867e5927c416478a5e6ec3ab64bc3386cc`
- Config: `docs/ops/S25-08_RAG_TUNING.toml`

## Comparison

- Status: `PASS`
- delta_hit_rate: `0.0`
- delta_latency_ms: `-0.211`
- min_hit_rate_delta: `-0.05`

## Baseline Metrics

- hit_rate: `1.0`
- avg_latency_ms: `0.771`
- chunk_size/overlap/top_k: `1200/200/1`

## Candidate Metrics

- hit_rate: `1.0`
- avg_latency_ms: `0.56`
- chunk_size/overlap/top_k: `800/100/3`

## PR Body Snippet

```md
### S25-08 RAG Tuning Loop
- status: PASS
- baseline_hit_rate: 1.0
- candidate_hit_rate: 1.0
- delta_hit_rate: 0.0
- delta_latency_ms: -0.211
- artifact: docs/evidence/s25-08/rag_tuning_latest.json
```
