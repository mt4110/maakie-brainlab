# PLAN: S17-03 Final Audit Closeout (Canonical Fixation)
Status: IN_PROGRESS
Owner: ambi
Progress: 0%

## Goal
- S17-03 の「無限ドリフト」を停止し、監査矛盾ゼロで closeout する。
- Canonical を「commit固定」にし、以後の verify-only 生成物は Observation（観測）として扱う。

## Canonical (Single Source of Truth)
- **See PR Body "Canonical Ritual" block** (to prevent infinite drift)

## Historical (Demoted; NOT Canonical)
- 121251 / 03cc... は過去の状態として残す（参考ログ）。
- “Canonical” として引用・ピン留めしてはならない。

## Invariants (Zero-Contradiction Contract)
- repo 内（git tracked）の docs/ / ops/ / .github/ / internal/ に `file:/{2}` が存在してはならない。
- “Canonical” と明記する場所は必ず上記 Canonical の3点（commit/bundle/sha）を使う。
- verify-only を実行すると bundle 名/sha は変わり得る。これは Observation であり Canonical を更新してはならない。
- 「通った」事実は Gate の PASS として記録し、Canonical の更新とは切り離す。

## Plan Pseudocode (Ambi v1)
### P0: Snapshot
- repo_root := `cd "$(git rev-parse --show-toplevel)"`
- branch := `git rev-parse --abbrev-ref HEAD`
- if branch == "main": error("do not finalize on main")
- require git status clean OR explicitly commit before gates

### P1: Hygiene (file URI ban)
- paths := ["docs", "docs/ops", "ops", ".github", "internal"]
- for p in paths:
  - if exists(p):
    - hits := rg('file:/{2}', p)
    - if hits > 0:
      - error("forbidden file:/{2} found; must obfuscate to [FILE_URI] or remove")
  - else:
    - skip("path missing: " + p)

### P2: Canonical Drift Sweep (stop infinite drift)
- deny_terms := [
  "review_bundle_20260215_121251.tar.gz",
  "03cc0575170393c7481c96452d9a0aae5feef7480901993c71ab7b0a89416fff"
]
- allow_terms_in := ["docs/evidence/s17-03/log_*", "docs/evidence/s17-03/run_*.json"]  # historical evidence only
- for term in deny_terms:
  - hits := rg(term, "docs", "ops", ".github")
  - if hits > 0:
    - if all hits are under allow_terms_in:
      - continue
    - else:
      - error("legacy canonical leaked into non-evidence docs: " + term)

### P3: Canonical Pin Updates
- Update these to Canonical:
  - docs/ops/S17-03_TASK.md (canonical block)
  - docs/ops/S17-03_FINALIZE_PLAN.md (this file)
  - docs/ops/S17-03_FINALIZE_TASK.md
  - docs/evidence/s17-03/fix_evidence.txt
  - docs/evidence/s17-03/fix_summary.md
  - WALKTHROUGH.md (canonical audit note)
  - PR #51 body (Canonical Ritual block)

### P4: Gates (truthful, reproducible)
- Run:
  - `make test`
  - `go run cmd/reviewpack/main.go submit --mode verify-only`
- Note:
  - verify-only output bundle name/sha is Observation
  - Canonical is NOT updated by this run

### P5: Done
- if all gates PASS and rg('file:/{2}') == 0 and drift sweep PASS:
  - mark FINALIZE_TASK as DONE (100%)
  - update PR body ritual
- else:
  - error("closeout blocked; fix failures first")
