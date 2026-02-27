# S21 TASK — Ops Hygiene (Outer Wall)

## Always (運用の外壁)
- [x] STATUS を単一の入口として維持する（ACTIVE/NEXT/PARKED/GRAVEYARD）
- [x] “単一SOT原則” を守る（漂流backlog項目を作らない）
- [x] Triage 儀式を定期実行できる形で残す（手で回せることが最優先）

## Backlog Index (MIGRATED SOT)
> ここが「移植先の単一SOT」。
> 古いSxxのbacklog項目は、必要ならここへ移植して“参照化”する。

### From S8_TASK.md
- [x] S21-MIG-S8-0001: if `git status --porcelain=v1` が空 ではない:
- [x] S21-MIG-S8-0002: error: 「作業ツリーが汚れている。stash/commitしてからやり直し」→ STOP
- [x] S21-MIG-S8-0003: if 現在ブランチ != main:
- [x] S21-MIG-S8-0004: `git switch main`
- [x] S21-MIG-S8-0005: `git pull --ff-only`
- [x] S21-MIG-S8-0006: `git fetch origin --prune`
- [x] S21-MIG-S8-0007: `git switch -c s8-00-audit-tightening-v1`
- [x] S21-MIG-S8-0008: `ls -la internal/reviewpack` を実行して存在確認
- [x] S21-MIG-S8-0009: if `internal/reviewpack` が存在しない:
- [x] S21-MIG-S8-0010: error: 「想定ディレクトリが無い。repo構成が違う」→ STOP

### From S15_07_KICKOFF_TASK.md
- [x] S21-MIG-S15-07-KICKOFF-0001: cd repo root
- [x] S21-MIG-S15-07-KICKOFF-0002: git status clean (or explicitly note dirty reason and STOP)
- [x] S21-MIG-S15-07-KICKOFF-0003: create branch: s15-07-kickoff-07-10-design-v1
- [x] S21-MIG-S15-07-KICKOFF-0004: list docs/ops for S15-07..10 (name variants)
- [x] S21-MIG-S15-07-KICKOFF-0005: rg S15-07..10 in S15_PLAN.md / S15_TASK.md
- [x] S21-MIG-S15-07-KICKOFF-0006: collect titles/intent lines (paste into matrix draft)
- [x] S21-MIG-S15-07-KICKOFF-0007: ensure kickoff plan/task files exist
- [x] S21-MIG-S15-07-KICKOFF-0008: ensure dependency matrix file exists
- [x] S21-MIG-S15-07-KICKOFF-0009: plan exists, aligned to template sections
- [x] S21-MIG-S15-07-KICKOFF-0010: task exists, ordered checkboxes + STOP conditions

### From S15_07_TASK.md
- [x] S21-MIG-S15-07-0001: confirm branch and clean status
- [x] S21-MIG-S15-07-0002: capture baseline pointers (HEAD sha etc)
- [x] S21-MIG-S15-07-0003: run relevant tests / gates (`make verify-il`, `.venv/bin/python scripts/il_exec_selftest.py`, `python3 -m compileall scripts`)
- [x] S21-MIG-S15-07-0004: record evidence artifact paths (`.local/obs/s15-07-resolution/20260227T133703Z/10_make_verify_il.log`, `.local/obs/s15-07-resolution/20260227T133703Z/20_il_exec_selftest.log`, `.local/obs/s15-07-resolution/20260227T133703Z/30_compileall_scripts.log`)
- [x] S21-MIG-S15-07-0005: commit with scoped message
- [x] S21-MIG-S15-07-0006: push branch
- [x] S21-MIG-S15-07-0007: PR body includes evidence + risks + rollback note

### From S15_08_TASK.md
- [x] S21-MIG-S15-08-0001: git fetch -p origin を実行
- [x] S21-MIG-S15-08-0002: git status -sb が クリーン
- [x] S21-MIG-S15-08-0003: main の S15 docs が存在する（存在確認できない場合は error）
- [x] S21-MIG-S15-08-0004: test -f docs/ops/S15_07_10_DEPENDENCY_MATRIX.md を確認
- [x] S21-MIG-S15-08-0005: 確定：docs/ops/S15_07_10_DEPENDENCY_MATRIX.md を採用
- [x] S21-MIG-S15-08-0006: S15_08_PLAN.md 内が全確定済み (no unresolved placeholder)
- [x] S21-MIG-S15-08-0007: PR分割ルール（原則/例外/例外判定）が 機械的に書かれている
- [x] S21-MIG-S15-08-0008: DependsOn / Touch / NoTouch / Gate の確定方針が書かれている
- [x] S21-MIG-S15-08-0009: Done条件が “検証可能” な形で書かれている
- [x] S21-MIG-S15-08-0010: S15_08_TASK.md 内が全確定済み (no unresolved placeholder)

### From S16_TASK.md
- [x] S21-MIG-S16-0001: Create/Update: docs/ops/S16-02_PLAN.md
- [x] S21-MIG-S16-0002: Create/Update: docs/ops/S16-02_TASK.md
- [x] S21-MIG-S16-0003: Gate (S16-02): bash -lc 'cd "$(git rev-parse --show-toplevel)"; PAT="$(printf "%c%c%c%c%c%c%c" 102 105 108 101 58 47 47)"; if git ls-files -z | xargs -0 rg -n "$PAT"; then echo "[FAIL] forbidden file URL found" >&2; exit 1; else echo "[OK] none"; fi'
- [x] S21-MIG-S16-0004: Create/Update: docs/ops/S16-03_PLAN.md
- [x] S21-MIG-S16-0005: Create/Update: docs/ops/S16-03_TASK.md
- [x] S21-MIG-S16-0006: bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; make test'
- [x] S21-MIG-S16-0007: bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; go run cmd/reviewpack/main.go submit --mode verify-only'
- [x] S21-MIG-S16-0008: bash -lc 'cd "$(git rev-parse --show-toplevel)"; PAT="$(printf "%c%c%c%c%c%c%c" 102 105 108 101 58 47 47)"; if git ls-files -z | xargs -0 rg -n "$PAT"; then echo "[FAIL] forbidden file URL found" >&2; exit 1; else echo "[OK] none"; fi'
- [x] S21-MIG-S16-0009: bash -lc 'cd "$(git rev-parse --show-toplevel)"; git add docs/ops/S16_PLAN.md docs/ops/S16_TASK.md docs/ops/S16-02_PLAN.md docs/ops/S16-02_TASK.md'
- [x] S21-MIG-S16-0010: bash -lc 'cd "$(git rev-parse --show-toplevel)"; git commit -m "chore(docs): lock S16 milestones + fix file-url scan recipe"'

### From S15_TASK.md
- [x] S21-MIG-S15-0001: cd "$(git rev-parse --show-toplevel)"
- [x] S21-MIG-S15-0002: git status -sb を確認
- [x] S21-MIG-S15-0003: if working tree dirty → STOP（stash/commit してから）
- [x] S21-MIG-S15-0004: WF=".github/workflows/verify_pack.yml" を固定
- [x] S21-MIG-S15-0005: if test -f "$WF" が false → error STOP（パス違い）
- [x] S21-MIG-S15-0006: for pat in ["- name: Pack Delta Report", "main-worktree", "pack_delta"]:
- [x] S21-MIG-S15-0007: rg -n "$pat" "$WF" -n
- [x] S21-MIG-S15-0008: if hit → break
- [x] S21-MIG-S15-0009: else continue
- [x] S21-MIG-S15-0010: if 最後まで hit 0 → error STOP（別workflow/別stepの可能性、勝手に決めない）

### From S18-00_TASK.md
- [x] S21-MIG-S18-0001: cd repo root:
- [x] S21-MIG-S18-0002: fetch:
- [x] S21-MIG-S18-0003: observe status:
- [x] S21-MIG-S18-0004: if ahead:
- [x] S21-MIG-S18-0005: either push:
- [x] S21-MIG-S18-0006: OR record reason (1 line) and proceed (no silent continue)
- [x] S21-MIG-S18-0007: if dirty:
- [x] S21-MIG-S18-0008: inspect:
- [x] S21-MIG-S18-0009: resolve to clean (docs-only is preferred):
- [x] S21-MIG-S18-0010: stage docs if appropriate:

### From S17-01_TASK.md
- [x] S21-MIG-S17-01-0001: cd "$(git rev-parse --show-toplevel)"; git status -sb
- [x] S21-MIG-S17-01-0002: git rev-parse --abbrev-ref HEAD
- [x] S21-MIG-S17-01-0003: git log -1 --oneline --decorate
- [x] S21-MIG-S17-01-0004: Create docs/il/IL_CONTRACT_v1.md
- [x] S21-MIG-S17-01-0005: Create docs/il/il.schema.json
- [x] S21-MIG-S17-01-0006: Create docs/il/examples/good_min.json
- [x] S21-MIG-S17-01-0007: Create docs/il/examples/bad_min.json
- [x] S21-MIG-S17-01-0008: Create docs/il/examples/bad_forbidden_timestamp.json
- [x] S21-MIG-S17-01-0009: Purpose / Terms
- [x] S21-MIG-S17-01-0010: Input / Output schema（人間向け）

### From S19-01_TASK.md
- [x] S21-MIG-S19-01-0001: [T0] Safety Snapshot（状況固定）
- [x] S21-MIG-S19-01-0002: git status -sb が clean である
- [x] S21-MIG-S19-01-0003: ブランチが s19-01-prkit-v1 である
- [x] S21-MIG-S19-01-0004: [T1] 修正：cmd/prkit/main.go を “--fill依存” から脱却
- [x] S21-MIG-S19-01-0005: dirty なら STOP（git status --porcelain）
- [x] S21-MIG-S19-01-0006: diff commits=0 なら STOP（upstream..HEAD）
- [x] S21-MIG-S19-01-0007: title = 最新コミット件名
- [x] S21-MIG-S19-01-0008: body = template読み込み → sentinel(prefix)除去 → evidence 注入 → 最小保証
- [x] S21-MIG-S19-01-0009: gh pr create --title/--body-file を実行
- [x] S21-MIG-S19-01-0010: PR既存なら “作らず PASS” にする

### From S16-01_TASK.md
- [x] S21-MIG-S16-01-0001: bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; git status -sb'
- [x] S21-MIG-S16-01-0002: bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; test "$(git rev-parse --abbrev-ref HEAD)" != "main"'
- [x] S21-MIG-S16-01-0003: bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; rg -n "PACK_VERSION|logs/portable|rules-v1\\.json|CONTRACT_v1" internal/reviewpack | sed -n "1,120p"'
- [x] S21-MIG-S16-01-0004: bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; rg -n "PACK_VERSION" internal/reviewpack/artifacts.go internal/reviewpack/verify.go internal/reviewpack/submit.go'
- [x] S21-MIG-S16-01-0005: bash -lc 'set -euo pipefail; cd "$(git rev-parse --show-toplevel)"; rg -n "\"1\\\\n\"|PACK_VERSION.*1" internal/reviewpack | sed -n "1,120p"'
- [x] S21-MIG-S16-01-0006: （提案）契約定義を1箇所に集約（例：internal/reviewpack/contract_v1.go を作る or verify.go に節として置く）
- [x] S21-MIG-S16-01-0007: PACK_VERSION >= 2 のとき、pack root に CONTRACT_v1 を 必ず生成
- [x] S21-MIG-S16-01-0008: verify-only は PACK_VERSION を読み、>=2 のとき Contract v1 を強制検証する
- [x] S21-MIG-S16-01-0009: PACK_VERSION の現行値が "1\n" なら、今回から "2\n" を生成するよう更新
- [x] S21-MIG-S16-01-0010: 互換性：verify側は 1 も検証できるように残す
