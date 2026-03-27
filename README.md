# maakie-brainlab

**maakie-brainlab** は、Maakie AI システムのコード、プロンプト、評価を管理する軽量プロジェクトです。実際のデータやインデックス、モデルを保持する `maakie-brainvault` へのシンボリックリンクを利用して動作します。

> **注意:** 本ソフトウェアは現在開発中（WIP）であり、まだ完成していません。

## 概要とアーキテクチャ

本システムは、AIエージェントの実行と検証ループを促進するために設計されています。複数のエントリーポイントを単一（Canonical）に統合し、一貫性を保つための厳格な検証メカニズムを備えています。

```mermaid
graph TD
    A[ユーザー / CI] --> B{il_entry.py (統合エントリーポイント)}
    B --> C[Guard / 検証処理]
    B --> D[Execution / 実行処理]
    B --> E[Verification / 確認処理]
    C --> F((.local/obs/ ログ))
    D --> F
    E --> F
    
    subgraph レガシー (直接実行禁止)
    G[il_exec.py] -.-> B
    H[il_check.py] -.-> B
    I[il_guard.py] -.-> B
    end
```

**Stopless (停止しない) アーキテクチャ**: アプリケーションが `sys.exit()` などで強制終了することを禁止しています。代わりに `STOP` 変数と `OK`/`ERROR`/`SKIP` を標準出力に返し、安全な監査を実現します。

**OBS ロギング**: すべての操作は詳細なログを `.local/obs/` に保存します。

## マイルストーンの状況

プロジェクトは多数のマイルストーン（S21系、S22系など）に分かれて進行しており、運用基盤の大部分が完了しています。現状（2026年2月）のステータスは以下の通りです：

**完了 (マージ済み)**: S21-02, S21-03, S21-04, S21-05, S21-06, S21-07, S22-01, S22-03, S22-04, S22-05, S22-06, S22-07, S22-08,
S22-09, S22-10, S22-11, S22-12, S22-13, S22-14 (IL入口単一化)

**進行中 / 次のタスク**: AMBI-01, S21-01, S22-02 (レビュー中)

## クイックスタート

### 1) ダッシュボードを使うだけ（`make gate1` は不要）

`make gate1` はCI向け検証です。UI確認だけなら以下の2ターミナルで十分です。

```bash
# ターミナルA: ローカルLLMサーバー起動（起動しっぱなし）
./infra/run-llama-server.sh /Users/takemuramasaki/brainvault/maakie-brainvault/models/Qwen2.5-7B-Instruct-Q4_K_M.gguf
```

```bash
# ターミナルB: ダッシュボード起動
cd ops/dashboard
cp .env.example .env  # 初回のみ
export OPENAI_API_BASE=http://127.0.0.1:11434/v1
npm install
npm run dev
```

ブラウザで `http://127.0.0.1:3033` を開いてください。

### 2) `make gate1` を実行する場合（検証フロー）

`gate1` は以下4つが「外部ストレージへのシンボリックリンク」であることを必須にしています。

- `data`
- `index`
- `logs`
- `models`

また、`gate1` 実行には `go` コマンドが必要です（`make test` 内で `go test ./...` を実行するため）。
`mise` を使う場合は `eval "$(mise activate zsh)"` 後に実行するか、`mise exec -- make gate1` を使用してください。

現在のエラー `[FAIL] 'data' must be a symlink to external storage.` は、この前提未充足によるものです。

```bash
# 例: brainvault を外部ストレージとしてリンク
mv data data.local.bak  # 既存ディレクトリ退避
ln -sfn /Users/takemuramasaki/brainvault/maakie-brainvault/data data
ln -sfn /Users/takemuramasaki/brainvault/maakie-brainvault/index index
ln -sfn /Users/takemuramasaki/brainvault/maakie-brainvault/logs logs
ln -sfn /Users/takemuramasaki/brainvault/maakie-brainvault/models models
```

```bash
# 通常モード (評価を実行)
make gate1

# 検証専用モード (既存の結果をチェックのみ)
bash ops/gate1.sh --verify-only
```

## ライセンス

本プロジェクトは **商用ライセンス (Commercial License)** の下で提供されています。無断での複製、改変、再配布は禁止されています。（現在は個人開発・内部利用のみを想定しています）
