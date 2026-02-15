# PLAN: S17-03 Stabilization of run_always_1h
Status: DONE
Owner: ambi
Progress: 100%

## Goal（目的）
- 署名必須ポリシー (`require_signature_in_ci = true`) 下での `run_always_1h` スケジュール実行失敗を解消する。
- `reviewpack submit` への署名フラグ追加と、`run_always_1h.sh` での適切な鍵の受け渡し・診断ログ強化を実現する。

## Non-Goal（やらないこと）
- `reviewpack` コアロジックの大規模リファクタリング。
- 基盤側（GitHub Actions 秘密情報管理）の設計変更。

## Inputs（入力）
- Repo: `git rev-parse --show-toplevel`
- Target branch: `s17-03-run-always-1h-fix-v1`
- Target files:
    - `internal/reviewpack/submit.go`
    - `ops/run_always_1h.sh`
    - `docs/ops/S17-03_PLAN.md`
    - `docs/ops/S17-03_TASK.md`

## Outputs（出力）
- Code changes: `submit.go` (--sign-key 対応), `run_always_1h.sh` (鍵管理修正).
- Evidence: `docs/evidence/s17-03/fix_evidence.txt`
- PR: #51 (Create/Update)

## Invariants（絶対に壊さないもの）
- Determinism: 署名後の bundle ハッシュが一意に定まること。
- Auditability: 署名失敗時は即停止し、診断ログを残すこと。
- Repro: ローカルで ephemeral key を生成し、全ゲートを通過できること。

## Stop Conditions（停止条件）
- error: `S6_SIGNING_KEY` がセットされているのにファイルが存在しない。
- error: `make test` または `verify-only` が FAIL。
- error: git が dirty（意図しない変更の混入）。

## Plan Pseudocode（疑似コード）
### P0: Safety Snapshot
- `repo_root` 取得、`main` 直作業なら error。
- `git status` が clean でなければ error。

### P1: Resolve Paths
- `SUBMIT_GO = "internal/reviewpack/submit.go"`
- `RUN_ALWAYS_SH = "ops/run_always_1h.sh"`
- ファイル未検出なら error。

### P2: Implement
- `submit.go`: `runSubmit` に `--sign-key` フラグを登録し、`packToTarForSubmit` で利用。
- `run_always_1h.sh`:
    - `EP_SIGNING_KEY` (Ed25519) の自動生成ロジック追加（smoke-test seed 利用）。
    - 診断ログ（`[DIAG]`）の追加。
    - 各ツールへの署名引数の伝播。
- `.gitignore`: `.tmp/` を無視（dirty check 対策）。

### P3: Gates
- `make test` PASS。
- `bash ops/run_always_1h.sh` を local ephemeral key で実行し、`[PASS] All steps passed` を確認。

### P4: Commit/PR
- コミット規約遵守。
- PR #51 本文を Ambi 式（Ritual SHA256 含む）に更新。

## Dead-Angle Check（死角チェック）
- PGP鍵（reviewpack）と Ed25519鍵（evidencepack）の形式不一致問題を、条件分岐と自動生成で解決したか？ → YES。
- 署名付き bundle の検証時に dirty tree 判定されないか？ → `.gitignore` 追加で解決。
- 証拠（SHA256）が ritual 化されているか？ → YES。
