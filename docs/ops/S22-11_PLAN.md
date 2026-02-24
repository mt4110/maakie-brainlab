# S22-11_PLAN: Milestone "意識ゼロ化" (zero-thought) v1

## 目的

milestone\_required を「人間の注意力」に依存させない。
PR作成〜マージまで、milestone を意識しなくても勝手に付く/最後に治る、を達成する。

## 方式（二重化）

A) GitHub側（自動修復）

- PRイベントで、milestone 未設定ならブランチ名から推測して自動付与する

B) ローカル側（最後の関所）

- ops/pr\_merge\_guard.sh が milestone 未設定を検知したら
  - ブランチ名から推測 → milestone を自動付与（可能なら）
  - 付与できなければ ERROR を出して "mergeしない" で止める（プロセスは落とさない）

## 絶対条件（運用不変）

- stopless：失敗してもプロセス終了で制御しない（exit/return非0/set -e/trap EXIT 禁止）
- 判定は stdout の OK/ERROR/SKIP で行う（ログが真実）
- 重い処理は分割（1ステップ1目的）
- glob禁止：探索は rg / 明示パスで行う

## 推測ルール（ブランチ名 → milestone）

- 例: s22-11-... → S22-11
- 正規表現: /s\\d{2}-\\d{2}/i を最初に拾い、先頭 s を S にして milestone title 化

## 実装対象（固定パス）

- 新規: .github/workflows/s22\_milestone\_autofill.yml
- 既存: ops/pr\_merge\_guard.sh
- 既存: docs/ops/STATUS.md
- 新規: docs/ops/S22-11\_PLAN.md / docs/ops/S22-11\_TASK.md

## DoD（Definition of Done）

- PRを milestone 未設定で作っても、GitHub側が自動で milestone を付与できる
- GitHub側が何らかで失敗しても、merge guard が最終的に milestone を付与してから merge できる
- milestone\_required が "missing milestone" で詰まらない（=人間の意識不要）
- SOT（STATUS.md）更新：S22-11 が 100% でクローズできる
