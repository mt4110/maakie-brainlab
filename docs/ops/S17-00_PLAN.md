# S17-00 PLAN（Kickoff: 固定してブレ殺し）

## Goal
S17 の目的・非ゴール・用語・成果物・ゲート・進捗率の基準を固定し、
後続の実装判断をブレさせない。

## Pseudo Code（分岐と停止条件）

### PHASE 0: Safety Snapshot
- branch / repo-root / latest-commit / status を記録
- IF dirty THEN
  - ERROR（混入の説明ができないため停止）
- END

### PHASE 1: Milestone Lock（S17-00..03固定）
- S17 は 4フェーズ固定と明記
- 進捗率の基準（25%×4）を明記
- IF フェーズ追加/削除したい THEN
  - ERROR（本フェーズの目的違反）
- END

### PHASE 2: Deliverables Lock（契約成果物の定義）
- docs: contract本文 / schema / examples / plan/task
- code: canonicalizer / validator / writer / tests（S17-02で確定）
- IF “賢さ” を成果に含める文言が入った THEN
  - ERROR（再現性から逸脱）
- END

### PHASE 3: Gates
- clean tree 前提で `make test`
- clean tree 前提で verify-only submit
- IF gate fail THEN
  - ERROR（証拠付きで停止）
- END
