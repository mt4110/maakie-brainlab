# Evidence Pack Specification (v1)

## Metadata (`00_meta.txt`)
In addition to basic pack info, specific evaluation metadata is recorded:

- `eval_mode`: `strict` (ran eval) or `verify-only` (reused result)
- `eval_source`: `strict_run` or `reuse_latest`
- `eval_result_sha256`: SHA256 of the jsonl result used (snapshot)
- `eval_result_bytes`: Size in bytes (snapshot)
- `eval_source_path`: Relative path of source eval result in repo (e.g. `eval/results/2026...jsonl`)
- `eval_source_sha256`: SHA256 of source file
- `eval_source_bytes`: Size of source file
