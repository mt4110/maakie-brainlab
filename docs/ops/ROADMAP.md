# docs/ops ROADMAP (入口)

この1枚が「入口」。迷ったらまずここを見る。

## どのドキュメントを見れば何が分かるか（最短回答）

- **全体図（マイルストーン / そのSシリーズの設計と到達点）**  
  → `docs/ops/Sxx_PLAN.md`
- **実行チェックリスト（今やること / 手順 / Gate）**  
  → `docs/ops/Sxx_TASK.md`
- **シリーズ内の個別フェーズ（分割された作業単位）**  
  → `docs/ops/Sxx-yy_PLAN.md` / `docs/ops/Sxx-yy_TASK.md`
- **横断の運用ルール（地図の凡例）**  
  → `docs/ops/PR_WORKFLOW.md` / `docs/ops/CI_REQUIRED_CHECKS.md` / repo ルート `SPEC.md`

---

## シリーズ俯瞰（S15〜S20）

> ステータスは「完了/進行中/迷子ポイント」を正直に書く。  
> 完了しててもテンプレ残骸があるなら、そこも書く（迷子の根絶）。

### S15（Diagnostics / まわりの基盤整備）
- 全体図: `docs/ops/S15_PLAN.md`
- 実行: `docs/ops/S15_TASK.md`
- 状態: **進行中**（※0-06は完了済みっぽい / 07-10は未着手）

### S16
- 全体図: `docs/ops/S16_PLAN.md`
- 実行: `docs/ops/S16_TASK.md`
- 状態: （ここに現状を書く）

### S17
- 全体図: `docs/ops/S17_PLAN.md`
- 実行: `docs/ops/S17_TASK.md`
- 状態: （ここに現状を書く）

### S18
- 全体図: `docs/ops/S18_PLAN.md`
- 実行: `docs/ops/S18_TASK.md`
- 状態: （ここに現状を書く）

### S19（PR Body Fixer）
- 全体図: `docs/ops/S19_PLAN.md`
- 実行: `docs/ops/S19_TASK.md`
- 状態: **実質完了 ✅**（S19-02 merged / mainゲート再実行PASS）  
  - 注意: **S19_PLAN / S19_TASK がテンプレのままだと迷子が再発** → S20で修正済みにする

### S20（Ops Roadmap Index / 迷子防止の入口整備）
- 全体図: `docs/ops/S20_PLAN.md`
- 実行: `docs/ops/S20_TASK.md`
- 状態: **これから（0%）**

---

## 運用ルール（再発防止）

- **新しいSを開始したら、必ずこの `ROADMAP.md` に1行追加する。**
- 完了したSでも、テンプレ残骸や迷子ポイントがあれば「注意」として残す。

---

## このROADMAPを壊さないための最低チェック

- リンク先ファイルが存在すること（相対パス）
- `file://` などローカル絶対リンクを混ぜない

