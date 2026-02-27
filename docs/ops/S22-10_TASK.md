# S22-10_TASK — Public Hardening v1
Last Updated: 2026-02-24

## Progress (SOT)
- S22-09: 100% (Merged PR #87) ✅
- S22-10: 0% → 1% (WIP after Kickoff commit)

## Rules
- stopless: exit/return non0/終了コード制御/例外停止 禁止
- Python: sys.exit/SystemExit/assert 禁止
- 1ステップ1処理。重い処理は分割し、ログ（OK/ERROR/SKIP）を残す
- glob禁止（必要なら rg/find で探索し、見つけたら break）

---

- [x] 0) repo確認（落ちない）
  - [x] `git rev-parse --show-toplevel` が取れる

- [x] 1) main同期（軽）
  - [x] fetch --prune / switch main / pull --ff-only
  - [x] OBSログ保存

- [x] 2) 未追跡ファイル隔離（混入事故防止）
  - [x] `git status --porcelain` を観測
  - [x] `??` を `.local/tmp/quarantine_untracked_<TS>/` へ移動（削除しない）
  - [x] 移動できないものは SKIP（理由1行）

- [x] 3) ブランチ作成/移動
  - [x] `s22-10-public-hardening-threat-injection-v1`

- [x] 4) Kickoffファイル整備
  - [x] `docs/ops/S22-10_PLAN.md` 作成/更新
  - [x] `docs/ops/S22-10_TASK.md` 作成/更新

- [x] 5) SOT更新（docs/ops/STATUS.md）
  - [x] S22-10 を `1% (WIP)` に（既に正しければ SKIP）

- [x] 6) SECURITY.md（最小）
  - [x] 報告先 / 秘密情報NG / 対応範囲 / Responsible disclosure

- [x] 7) THREAT_MODEL_v1
  - [x] 攻撃面の列挙（IL/pack/CI/依存/アーカイブ）
  - [x] 期待する壊れ方（OK/ERROR/SKIP）と検知点

- [x] 8) INJECTION_SIM_SUITE_v1
  - [x] 5〜10ケース
  - [x] fixture は任意（相対パスのみ）

- [x] 9) Smoke（CPU軽）
  - [x] suite doc を読み、構造と fixture を観測
  - [x] JSON/JSONL の最小妥当性チェック（軽）
  - [x] assert/sys.exit/SystemExit なし
  - [x] 例外で停止しない（捕まえて ERROR ログ）

- [x] 10) 軽い検証（分割）
  - [x] Step10-1: `python3 tests/test_injection_sim_smoke.py` のみ
  - [x] Step10-2: 余力があれば既存 verify を追加（重ければ次ステップへ分割）

- [x] 11) reviewpack verify-only（証拠）
  - [x] `go run cmd/reviewpack/main.go submit --mode verify-only`
  - [x] bundle sha を PR本文へ

- [x] 12) PR作成（milestone必須）
  - [x] milestone: S22-10
  - [x] Copilot review（best-effort）
  - [x] merge-commit only（squash禁止）

- [x] 13) merge guard
  - [x] `ops/pr_merge_guard.sh` dry-run
  - [x] `--merge` 実行

- [x] 14) Closeout（同PR内で可能なら同梱）
  - [x] STATUS を `100% (Merged PR #??)` に
