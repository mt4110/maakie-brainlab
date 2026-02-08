# review_pack

## 目的

第三者が `review_pack_*.tar.gz` **だけ**で、次を迷わず実行できる状態にする。

- 改ざん検出（チェックサム）
- 厳密検証（余計なファイル混入の検出）
- Gate-1 の **verify-only** 検証（同梱の `latest.jsonl` を読むだけ）

> [!IMPORTANT]
> **v2 (Go CLI)** に移行しました。
> 旧シェルスクリプト `ops/review_pack.sh` は廃止されています。

---

## 使い方 (Go CLI)

基本はリポジトリの **ルートで** 実行します（`git ls-files` 等が前提）。

```bash
# Pack生成
go run cmd/reviewpack/main.go pack [--timebox 300] [--skip-eval] [N_COMMITS]

# 提出用の “1コマンド儀式” です。pack生成〜検証（verify-only）までを一気に実行し、提出用の SHA256 も表示します。
go run cmd/reviewpack/main.go submit

# Fix: evalスキップ（直近1コミット）
go run cmd/reviewpack/main.go pack --skip-eval 1

# 検証（展開ディレクトリ or tar.gz）
go run cmd/reviewpack/main.go verify review_pack_2026xxxx.tar.gz

# 再現性チェック（※ 現状は tar の決定論性テスト用途で、強い保証ではない）
go run cmd/reviewpack/main.go repro-check
```

---

## pack 内で第三者がやること（推奨手順）

1) **改ざん検出（必須）**

```bash
bash VERIFY.sh
```

2) **厳密検証（任意 / Goが必要）**

```bash
go run ./src_snapshot/cmd/reviewpack/main.go verify .
```

3) **Gate-1 verify-only（任意）**

pack には `src_snapshot/eval/results/latest.jsonl` が同梱されます。

```bash
cd src_snapshot
bash ops/gate1.sh --verify-only
```

---

## 仕様 (Guarantees)

### 1) 改ざん検出（CHECKSUMS.sha256）

- `CHECKSUMS.sha256` に列挙されたファイルについて、SHA256 が一致することを検証します。
- `VERIFY.sh` は「チェックサム検証だけ」を POSIX シェルで実行できる薄いラッパーです。

### 2) Strict Verification（余計なファイル混入を拒否）

- `verify` コマンドは `CHECKSUMS.sha256` に **載っていないファイル** を検出すると失敗します（Exit Code 11）。
- 例外は **`CHECKSUMS.sha256` のみ**（`CHECKSUMS.sha256` 自体は自己参照になるため列挙しない）。

### 3) tar の決定論性（弱い保証）

- tar 内のファイル順序はパス順にソート。
- tar ヘッダの ModTime/Uid/Gid は正規化。

ただし pack には次が含まれるため、**「同じ Git commit + 同じソースなら常に同一 SHA256」**までは保証しません：

- 生成時刻を含むメタ情報
- 実行ログ（`make test` / `make run-eval`）に含まれるテンポラリパス等

> ここで担保したいのは「再生成してハッシュ一致」ではなく、
> **配布された pack が改ざんされていないことを機械的に検出できる**こと。

### 4) Timeout（孫プロセス残留を防ぐ）

- `make test` / `make run-eval` は `TIMEBOX_SEC` でタイムアウトすると、プロセスグループ全体に `SIGTERM` → `SIGKILL` を送ります。

### 5) Secrets Fail-Fast

- Git 管理下のファイルに秘密鍵やトークン（Fix: `sk-...`）が含まれる場合、即座に失敗し、アーカイブを生成しません。
- 証拠は `20_secrets_scan.txt` に残ります。
