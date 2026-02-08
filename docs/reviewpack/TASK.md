# Reviewpack Tasks (S4)

- [x] Preflight: `git status --porcelain` が非空なら tar.gz 作成前に fail-fast
- [x] `01_status.txt` はログとして残す（判定には使わない）
- [x] Eval bundling: `eval/results/*.jsonl` の最新を `src_snapshot/eval/results/latest.jsonl` として同梱
- [x] `eval/results/*.jsonl` が無い場合は fail-fast（run-eval を促す）
- [x] submit が Gate-1 verify-only まで PASS することを実測ログで確認
- [x] pack に symlink が無いことを確認
