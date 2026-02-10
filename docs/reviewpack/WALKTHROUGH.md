# Reviewpack Walkthrough (S4)

このドキュメントは `cmd/reviewpack/main.go submit` が
**pack単体で Gate-1 verify-only まで完走できる**ことを、再現可能な形で示す証跡です。

## 実装の要点

### 1) Preflight: clean working tree を強制
- 判定は `git status --porcelain` のみ（空=clean / 非空=dirty）
- dirty の場合、tar.gz を作る前に fail-fast
- `01_status.txt` はログとして残す（判定には使わない）

対象: `cmd/reviewpack/main.go`（runPack 付近）

### 2) Gate-1 verify-only のために eval 結果を同梱
- `eval/results/*.jsonl` から **ファイル名辞書順で最新**を選び、
  `src_snapshot/eval/results/latest.jsonl` としてコピーして同梱
- `eval/results/*.jsonl` が無い場合は fail-fast（前進するエラー）

対象: `cmd/reviewpack/main.go`（copyLatestEval）

## 検証ログ（Clean state）

実行:
```bash
git status --porcelain
go run cmd/reviewpack/main.go submit

期待:

[OK] created review_pack_*.tar.gz

src_snapshot/eval/results/latest.jsonl が verify に現れる

Gate-1 verify-only が PASSED する

例（抜粋）:

[INFO] bundling latest eval result: <timestamp>.jsonl -> latest.jsonl

Target result: eval/results/latest.jsonl

=== Gate-1 PASSED: System is Truthful & Verified ===
```

## Pack内容チェック（symlink無し + latest.jsonl あり）
```bash
tar -tf review_pack_*.tar.gz | grep 'src_snapshot/eval/results/latest\.jsonl'
tar -tvf review_pack_*.tar.gz | grep ' -> ' || echo "OK: no symlinks"
```
