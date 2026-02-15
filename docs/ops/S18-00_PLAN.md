# S18-00 PLAN — Deterministic Template Kit Bootstrap (v2)

## Goal (1 sentence, SCOPE LOCK)
Deterministic ops templates (v1) を導入し、以後の全フェーズの Plan/Task 生成を決定論に固定する（このPRでスコープを閉じる）。

## Scope (LOCKED — no ex-post-facto)
This phase (S18-00) includes ONLY:
1) `docs/ops/meta/` の作成（存在しなければ）
2) 2つの決定論テンプレの新規導入（存在する場合は**上書き禁止**）
   - `docs/ops/meta/DETERMINISTIC_PLAN_TEMPLATE.md`
   - `docs/ops/meta/DETERMINISTIC_TASK_TEMPLATE.md`
3) 上記テンプレを用いた S18 の骨格 docs を生成（無ければコピー）
   - `docs/ops/S18_PLAN.md`
   - `docs/ops/S18_TASK.md`
   - `docs/ops/S18-00_PLAN.md`
   - `docs/ops/S18-00_TASK.md`
4) Local gates を通し、Canonical を **このPRの1回だけ** pin する

Non-Goals (explicitly excluded; MUST be S18-01+):
- S18-01 以降の具体スコープ定義（TBDのまま）
- 実装コードの変更（docs/ops のみ）
- 既存テンプレや既存 docs の内容改変（S18-00の必須ではない）

## Invariants (Must Hold)
- **後出し禁止**：このPLANの Scope 範囲外の作業は行わない（必要なら S18-01 を新規に ops docs で定義してから開始）
- **上書き禁止**：`docs/ops/meta/DETERMINISTIC_*` が存在する場合、内容は変更しない（SKIP理由を1行で残す）
- Plan は分岐と停止条件（嘘をつかない）
- Task はチェックボックスで順序固定（再現可能）
- skip は理由を1行、error はその場で停止（握りつぶし禁止）
- Canonical は **このPRで1回だけ固定**。以降の verify-only 生成物は Observations（Canonical更新禁止）

## Inputs (Source of Truth)
- Repo state (git HEAD / status)
- Existing ops docs (S17までの完了状態は変更しない)
- Local gates outputs (make test / reviewpack verify-only)

## Deliverables (Concrete Outputs)
A) Template Kit (v1)
- docs/ops/meta/DETERMINISTIC_PLAN_TEMPLATE.md
- docs/ops/meta/DETERMINISTIC_TASK_TEMPLATE.md

B) S18 Skeleton Docs
- docs/ops/S18_PLAN.md
- docs/ops/S18_TASK.md
- docs/ops/S18-00_PLAN.md
- docs/ops/S18-00_TASK.md

C) Evidence (Canonical pin for this PR)
- Commit SHA
- review_bundle filename
- SHA256

## Gates (Must Pass)
- `make test` PASS
- `go run cmd/reviewpack/main.go submit --mode verify-only` PASS

## STOP Conditions (minimal; avoid unnecessary HALT)
STOP (hard stop) ONLY when:
1) Template bootstrap 実行後もテンプレファイルが存在しない
   - (例) 権限/パス異常/ディスク問題で write できない
2) Gates が失敗し、修正しても再現的に PASS に戻せない
3) `git status -sb` が解消不能な dirty/ahead 状態で、原因不明（手元作業の混線）

NOT a STOP (must continue via repair path):
- docs/ops/meta が無い → 作る
- テンプレが無い → **S18-00の成果物として作る**
- ブランチが既にある → SKIP理由1行で継続
- S18 docs が既にある → SKIP理由1行で継続（上書きしない）

---

# Phase 0 — Safety Snapshot (Recover-first, no silent stop)
do:
- observe: `git status -sb`
- if ahead:
  - resolve: push OR explicitly decide to keep local-only (record reason)
- if dirty:
  - resolve: commit/stash/etc.（本フェーズは docs-only が基本なので、まず docs を固めて clean に戻す）

stop when:
- working tree is clean OR the reason for not being clean is explicitly recorded (no ambiguity)

---

# Phase 1 — Template Bootstrap (core)
## 1.1 Ensure meta dir
- if `docs/ops/meta/` missing:
  - create it

## 1.2 Write templates if missing (NO overwrite)
- if either template missing:
  - create missing ones deterministically (exact paths)
- if both exist:
  - SKIP (理由1行)

STOP if:
- after creation attempt, `test -f` still fails (write failure)

---

# Phase 2 — Generate S18 skeleton docs (copy from templates if missing)
- copy templates to S18 docs ONLY if target files are missing
- never overwrite existing S18 docs in this phase

stop when:
- required 4 docs exist (S18 + S18-00 PLAN/TASK)

---

# Phase 3 — Scope Pin (write now, prevent ex-post)
- In `docs/ops/S18_PLAN.md`, write minimal statement:
  - S18-00 is this bootstrap
  - S18-01+ is TBD and MUST be defined in ops docs before starting
- In `docs/ops/S18-00_PLAN.md`, ensure Goal + Scope + Deliverables are consistent (this file)

stop when:
- third party can read docs/ops only and understand:
  - what S18-00 does
  - what is forbidden in S18-00
  - where S18-01 should begin (but not defined here)

---

# Phase 4 — Local Gates & Canonical Pin (single)
run:
- `make test`
- `reviewpack submit --mode verify-only`

pin ONCE:
- Commit SHA
- review_bundle filename
- sha256

note:
- future verify-only outputs are Observations; Canonical is NOT updated

---

# Phase 5 — PR Ritual
ensure:
- git status clean
- PR body includes Canonical block exactly once
- SOT block matches Scope (no extra deliverables)

done.
