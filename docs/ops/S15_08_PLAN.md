# S15-08 PLAN — Implementation PR Slicing + Dependency Lock

## ゴール
S15-07 までで固めた「07-10の設計地図」を、**実装PRへ安全に分解できる形に“機械化”**する。
具体的には：
- 未確定項目を全消し（S15-08 PLAN/TASK 内）
- 依存関係を確定（Dependency Matrix 更新）
- “触る場所（files/dirs）”を確定（各 step が変更してよい領域をロック）
- PR 分割ルールを固定（原則 1 step = 1 PR、例外もルール化）

## 非ゴール（やらない）
- 実装自体（コード変更・挙動変更）は S15-09以降
- 新しい設計（07-10の設計凍結を壊す行為）は 禁止

## 前提（完了済み）
- S15-06：merged
- S15-07：merged (kickoff progress)
- 07-10 の plans/tasks と dependency matrix が repo に存在

## 成果物（このステップで必ず出す）
- docs/ops/S15_08_PLAN.md（本書：確定済み）
- docs/ops/S15_08_TASK.md（実行順固定・確定済み）
- Dependency matrix の更新（docs/ops/S15_07_10_DEPENDENCY_MATRIX.md）
- “PR分割ルール”の明文化（PLANにもTASKにも1箇所は必ず書く）

## 重要ルール（決定論・監査耐性）
- 曖昧語を残さない：未確定プレースホルダ / maybe / might / later を残したら未完
- 分岐は停止条件つき：迷ったら止まる（嘘をつかない）
- 探索（for）は「候補パス特定」にのみ使う：見つけたら break / 見つからなければ continue
- skip は理由を1行で残す：未来の監査ログ
- error はその場で終了：その場で止まる＝正しさ

## 依存関係の確定方針
### 依存の種類
- Doc依存：仕様・用語・契約（ドキュメントの前提）
- Code依存：共通関数・共通型・ユーティリティが先に必要
- Gate依存：テスト/verify-only が先に整ってないと詰む

### ロックの形式
各 step について以下を必ず確定する：
- DependsOn：先に merged されているべき step/PR
- Touch：変更してよい領域（files/dirs）
- NoTouch：触ってはいけない領域（明示）
- Shared：共有化が必要になった場合の逃がし先（例外ルール）

## PR分割ルール（機械的）
### 原則
- 1 step = 1 PR
- PR は docs-only か code-change か を最初に分類し、儀式（ゲート）を切り替える

### 例外（共有コードが出たとき）
共有コードが出た場合は、次のどちらかに必ず決め打ちする：
- 例外A：先行“shared PR”を1本作る
  - 共有ユーティリティ/型/関数だけを切り出し
  - 後続 step PR は shared PR に依存する（DependsOn に追加）
- 例外B：共有を禁止し、重複を許容（ただし “期限付き” の注記を残す）
  - 次の整理ステップ（後日）を別stepとして作る（未来に借金を押し付けるなら、借用書を書く）

### 例外判定（停止条件つき）
- 共有候補が「2 step 以上で確実に再利用される」→ 例外A を優先
- 共有候補が「将来変わりやすい/仕様未確定」→ 例外B（凍結を壊さない）

## 実行の疑似コード
1) Verify base (git status)
2) Locate dependency matrix file
3) Fill S15_08 PLAN/TASK (finalize)
4) Update matrix (DependsOn, Touch, NoTouch, Gate)
5) Decide PR naming conventions
6) Gates (verify-only)

## Done条件（監査用）
- docs/ops/S15_08_PLAN.md に 未確定プレースホルダが0件
- docs/ops/S15_08_TASK.md に 未確定プレースホルダが0件
- Dependency matrix が更新され、各 step に以下が揃っている：
  - DependsOn / Touch / NoTouch / Gate / PR unit
- PR分割ルールが PLAN/TASK のどちらにも明記されている
- docs-only であることが git diff --stat から明白
- reviewpack verify-only が成功している
