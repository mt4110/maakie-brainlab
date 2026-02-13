# S15-02: os.MkdirAll Error Hardening

## Goal
os.MkdirAll のエラーが握りつぶされてる箇所をゼロにし、失敗時に診断可能なエラーメッセージと共に fail-fast させる。

## Background
- os.MkdirAll のエラーが握りつぶされていると、その後の WriteFile 等が静かに失敗（あるいは別のエラーとして発生）し、根本原因（ディレクトリ作成失敗）の特定が困難になる。
- CI(test) での `log.Fatal` 引数不正（複数引数渡し）によるビルドエラーを根治する。

## Non-goals
- 機能追加
- 出力形式変更
- 大規模リファクタ

## Implementation Strategy

### 1) 診断性向上のための設計
- 内部 helper (`ensureDir`, `generatePlaceholderLog`) は `error` を返す（ユニットテスト可能にするため）。
- 外部コマンド層（`submit`, `pack` 等）は helper のエラーを受けて `log.Fatalf` で即座に終了する。
- エラーメッセージには必ず対象のディレクトリパスを含める。

### 2) テストコードの硬化
- `diff_test.go` 等のテストフィクスチャ作成時における `os.WriteFile` や `os.MkdirAll` のエラーをすべて `t.Fatal` で拾うようにし、テスト環境の不備を隠蔽しない。

### 3) 決定論的失敗テスト
- `mkdir_test.go` にて、既存ファイル配下にディレクトリを作成しようとして意図的に失敗させ、エラーメッセージの内容（pathの含有）と伝播を検証する。

## Gates
- make ci-test PASS
- go test ./... PASS
- 変更差分が mkdir 周辺およびテストフィクスチャ修正に限定されていること
