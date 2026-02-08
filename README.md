# maakie-brainlab

Lightweight project (code/prompts/eval) + symlinks to maakie-brainvault (data/index/models).

## 検証 (Gate-1)

システムの真実性を検証するには、以下のコマンドを使用します：

```bash
# 通常モード (評価を実行)
make gate1

# 検証専用モード (既存の結果をチェック)
bash ops/gate1.sh --verify-only
```

配布されたレビューパック内では、`./VERIFY.sh` を実行することで整合性と Gate-1 のパスを確認できます。

## Quickstart

1) Start llama-server
2) Build index
3) Ask
