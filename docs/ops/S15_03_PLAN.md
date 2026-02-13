# S15-03: Diagnostics & Test Hygiene
mkdir fail-fast の詰め + docs整合 + fixture error handling

## Status (S15 series)
- S15-01 merged (#35): pack delta v1
- S15-02 merged (#36): mkdir error fail-fast
- Next: S15-03 — remaining “red signals” are about diagnostics clarity and tests that validate our code (not the OS).

## Goals
- Diagnostics: log.Fatalf が出るとき、原因が “一撃で特定” できる（失敗した dir/path を必ず含める）
- Test hygiene: テストが嘘をつかない（握りつぶしゼロ、fail-fast を reviewpack 側で検証）
- Docs alignment: S15-02 の仕様・意図と、S15-03 で強化した点が矛盾しない

## Non-goals (Out of scope)
- log.Fatalf を全面的に error return へ置き換える大改修
- CLI UX 全体の刷新
- 大規模なディレクトリ構造変更

## Plan (control-flow oriented)

plan:
- if grep で `_ = os.WriteFile(` が product code に残っている:
  - then: すべて err チェックに置換し、失敗時は log.Fatalf で fail-fast
  - else: 既にゼロなら “維持のためのガード” として grep を evidence に残す
- for each log.Fatalf site that does NOT include a concrete path/dir:
  - update message to include the failing target (dir/path) + err
  - keep message style consistent with existing msgFatal* constants
- if tests currently validate only `os.MkdirAll` behavior (not our fail-fast):
  - then: subprocess/helper pattern で “reviewpack が落ちる/エラーになる” を検証するテストを追加
  - else: テストが reviewpack の挙動を直接検証していることを説明できる形に整える
- if Copilot 指摘が過去版で既に解決済み（diff_test.go が握りつぶしてない等）:
  - then: “already fixed” を示す evidence（grep + code snippet + test output）を PR に残してクローズ
- docs:
  - ensure S15-02 docs と S15-03 の実装が整合
  - add short “Why this matters” (CI が嘘をつかないため)

## Definition of Done
- `log.Fatalf` で落ちるケースで、必ず “どの path/dir が対象だったか” がログに出る
- `_ = os.WriteFile(` が internal/reviewpack の product code から消える（意図的例外があるなら理由をコメントで明記）
- `mkdir_test.go` か新テストで、reviewpack 側の fail-fast を subprocess/helper で検証できている
- `make test` が PASS
- PR に evidence（grep結果 + make testログ）を添付

## Evidence Commands
- rg checks:
  - rg -n "log\.Fatalf" internal/reviewpack
  - rg -n "_ = os\.WriteFile\(" internal/reviewpack
- tests:
  - make test
