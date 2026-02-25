# S22-13_PLAN: CI required checks のSOT同期（branch protection drift 根絶）v1

## 目的
GitHubの branch protection（required checks の現実）と
docs/ops/CI_REQUIRED_CHECKS.md（SOT）がズレて「人間の注意力」で埋める運用を根絶する。

## 背景（構造）
- required checks は GitHub設定（外部）で変わり得る
- docs と merge guard が追従しないと、ドキュメントが嘘になる / merge guard が見落とす / 人間が困る

## 方針（勝ち筋）
- CI_REQUIRED_CHECKS.md に “機械可読SOTブロック” を追加（required contexts を固定）
- ops/required_checks_sot.sh を追加
  - gh api で main の branch protection を取得
  - required contexts を抽出
  - SOTブロックの内容と集合比較
  - ずれたら ERROR を出す（stopless：プロセス終了で制御しない）
- ops/pr_merge_guard.sh に “required checks drift 検知” を組み込み
  - drift がある場合：STOP=1（マージ儀式の関所で止める）
  - 取得できない場合：ERROR を出して STOP=1（嘘を付かない）

## 実装対象（固定パス）
- MOD: docs/ops/CI_REQUIRED_CHECKS.md（SOTブロック追加）
- NEW: ops/required_checks_sot.sh
- MOD: ops/pr_merge_guard.sh（SOT drift 検知を追加）
- NEW: docs/ops/S22-13_PLAN.md / S22-13_TASK.md
- MOD: docs/ops/STATUS.md（S22-13: 1% WIP）

## DoD
- ops/required_checks_sot.sh が OK/ERROR を出して drift を検知できる
- merge guard が drift を検知したら STOP=1 で “儀式”を止める（exitは禁止）
- docs/ops/CI_REQUIRED_CHECKS.md が現実と一致する（SOTが嘘にならない）
- 1PRで closeout まで完走（TASK/STATUS 100%）
