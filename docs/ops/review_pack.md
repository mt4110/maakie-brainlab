# review_pack 運用メモ

## 目的

第三者が `review_pack_*.tar.gz` だけで「再現可能な検証」と「証拠確認」をできる状態にする。

> [!IMPORTANT]
> **v2 (Go CLI)** に移行しました。
> 旧シェルスクリプト `ops/review_pack.sh` は廃止されました。

## 使い方 (Go CLI)

`reviewpack` ツール（Go製）を直接使用します。

```bash
# Pack生成
go run cmd/reviewpack/main.go pack [--timebox 300] [--skip-eval] [N_COMMITS]

# パック生成の例（evalスキップ、直近1コミット）
go run cmd/reviewpack/main.go pack --skip-eval 1

# 検証（展開ディレクトリ or tar.gz）
go run cmd/reviewpack/main.go verify review_pack_2026xxxx.tar.gz

# 再現性チェック
go run cmd/reviewpack/main.go repro-check
```

## 仕様 (Guarantees)

### 1. 決定論的アーカイブ (Deterministic Tar)

- `go run cmd/reviewpack/main.go pack` が生成する `tar.gz` は、入力（Git Commit + ファイル内容）が同じなら**常に同一の SHA256** になります。
- タイムスタンプ（ModTime）は Epoch 0 に固定。
- ユーザーID/グループIDは 0 に固定。
- ファイル順序はパス名順にソート。

### 2. Strict Verification

- `verify` コマンドは `CHECKSUMS.sha256` に記載されたファイル**以外**が存在すると**失敗**します（Exit Code 11）。
  - 例外：`CHECKSUMS.sha256`, `40_self_verify.log` のみ。
- これにより、「検証環境にゴミが混入している」状態を確実に検出します。

### 3. プロセス制御 (Timeout)

- `make test` や `make run-eval` がタイムアウト（`TIMEBOX_SEC`）した場合、プロセスグループ全体に `SIGTERM` -> `SIGKILL` を送り、孫プロセス（Python等）が残留するのを防ぎます。

### 4. Secrets Fail-Fast

- Git管理下のファイルに秘密鍵やトークン（`sk-...`）が含まれる場合、即座に失敗し、アーカイブを生成しません。
- 証拠は `20_secrets_scan.txt` に残ります。
