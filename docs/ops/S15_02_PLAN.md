# S15-02: os.MkdirAll Error Hardening

## Goal
os.MkdirAll のエラーが握りつぶされてる箇所をゼロにし、失敗時に return error で診断可能にする。

## Background
os.MkdirAll のエラーが握りつぶされていると、その後の WriteFile 等が静かに失敗（あるいは別のエラーとして発生）し、根本原因（ディレクトリ作成失敗）の特定が困難になる。

## Non-goals
- 機能追加
- 出力形式変更
- 大規模リファクタ

## Implementation Strategy

plan:
- if main が最新でない → STOP（pullしてから）
- for each hit in rg "MkdirAll\(":
    - if err を無視している (_ = os.MkdirAll / os.MkdirAll(...); の戻り未処理 / || true 相当) → fix対象
    - else continue
- if fix対象が0件 → skip（理由：すでに硬化済み）

implement:
- `if err := os.MkdirAll(dir, 0o755); err != nil { return fmt.Errorf("mkdir %s: %w", dir, err) }`

add tests:
- if テストで MkdirAll を確実に失敗させられない → STOP（嘘テスト禁止）
- 推奨失敗パターン（決定論）：
    - temp dir に ファイルを作って、そのパス配下に dir を掘ろうとして失敗させる（“not a directory”）

## Gates
- make ci-test PASS
- go test ./... PASS
- 変更差分が mkdir 周辺に限定されていること
