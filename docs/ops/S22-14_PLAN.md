# S22-14_PLAN: IL入口の単一化（P0）+ 常時検証 v1

## 背景
ILの入口が複数あると、仕様分岐・テスト片落ち・ログ揺れが起きる。
入口統一は以後の executor/eval/guard を加速する土台。

## ゴール（入口=1）
- Canonical Entrypoint を 1つに定義する
- 旧入口は canonical へ委譲（wrapper化）または明示禁止
- 常時検証で「canonical以外の入口参照」を検知して ERROR を出す（exitでは止めない）

## Canonical（TODO: discovery後に確定）
- CANONICAL_ENTRYPOINT: **scripts/il_entry.py**
- LEGACY_WRAPPERS: discovery結果に基づき列挙（wrapper化する場合）
- INTERNAL_REFERENCES: Makefile/ops/workflow/docs からの参照は canonical に寄せる

## 実装方針（疑似コード / stopless）
try:
  OBSを作る
  if repoが無い:
    error("not in repo"); STOP=1
  else:
    # discovery（CPU軽）
    for dir in [scripts, src, ops, docs, .github]:
      if dirが無い:
        continue (SKIPを1行)
      else:
        rgで入口候補を探索してOBSへ保存

    if 候補がゼロ:
      error("no candidates; expand search carefully"); STOP=1
    else:
      # canonical選定
      if 既存で最も利用されている入口がある:
        CANONICAL = それ
      else:
        CANONICAL = scripts/il_entry.py を新設し、既存入口はwrapperへ

      # refactor
      for each legacy_entrypoint in discovered:
        if legacy_entrypoint == CANONICAL:
          continue
        else:
          wrapperへ置換（canonicalへ委譲）または禁止を明記

      # always-on guard
      guardを追加し、repo内参照がcanonical以外なら ERROR を出す
      docs/STATUS を更新

catch Exception as e:
  error("unexpected"); STOP=1
