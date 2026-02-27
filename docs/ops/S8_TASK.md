# S8_TASK — Determinism / Audit Tightening
(あんびちゃそ実装タスク：迷子防止の制御構文つき)

## 0) Preflight (必須)
- MIGRATED: S21-MIG-S8-0001 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S8-0002 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S8-0003 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S8-0004 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S8-0005 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S8-0006 (see docs/ops/S21_TASK.md)

## 1) ブランチ作成
- MIGRATED: S21-MIG-S8-0007 (see docs/ops/S21_TASK.md)

## 2) 編集対象ファイルパスの確定（勝手に決めない）
- MIGRATED: S21-MIG-S8-0008 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S8-0009 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S8-0010 (see docs/ops/S21_TASK.md)
- [x] `rg -n "go test" -S .` を実行
- [x] if ヒット0件:
      - [x] `rg -n "exec\\.Command\\(\"go\"|\\bgo\\b.*test" -S internal cmd ops .` を実行
- [x] if それでもヒット0件:
      - [x] error: 「go test 実行箇所が見つからない。実装方針が立てられない」→ STOP
- [x] for ヒットした箇所を上から確認:
      - [x] if “reviewpack の実行ステップ” で go test を呼んでいる箇所を見つけた:
            - [x] break（そのファイルがS8의 主戦場）
      - [x] else:
            - [x] continue

## 3) PR33相当: go test 実行オプション設計を実装（最小差分）
### 3.1 方針
- CI(strict) では `-count=1 -mod=readonly` を必ず付与
- Local(permissive) は既存挙動維持（破壊しない）
- Localで strict を opt-in できる導線を作る（環境変数 or 既存modeに統合。新フラグ乱立は避ける）

### 3.2 実装手順
- [x] if go test コマンド組み立てが “直書き”:
      - [x] 最小のヘルパー関数/分岐を同一ファイル内に追加して引数を組み立てる
- [x] else if 既に “mode(strict/permissive)” っぽい概念がある:
      - [x] その分岐に乗せて `-count=1 -mod=readonly` を CI(strict) 側だけに追加
- [x] else:
      - [x] error: 「既存の設計軸が無いのに新軸を作ると破綻する。設計見直し」→ STOP

### 3.3 失敗時UX（-mod=readonly 系）
- [x] go test が失敗したとき:
      - [x] if stderr に `-mod=readonly` 由来の文言が含まれる（例: updates to go.mod needed / go.sum updates needed 等）:
            - [x] “補助メッセージ” を追加（rawはそのまま）
      - [x] else:
            - [x] 既存のエラー出しを維持（捏造しない）

## 4) PR34相当: ログノイズ抑制（抑制→置換の順、監査ガード付き）
### 4.1 まず現状把握
- [x] `rg -n "log(s)?/|bundle.*log|portable|sanitize|redact" -S internal/reviewpack docs .` を実行
- [x] if bundle にログ同梱が無い:
      - [x] skip: 「S8のportable view設計は“保存先”が無いと成立しない」→ STOP（設計見直し）
- [x] else:
      - [x] continue

### 4.2 実装ルール（絶対に守る）
- raw log は削らない（監査の真実）
- portable view は “表示/比較用” として追加するだけ
- portable ルールは versioned（rules-v1 など）で同梱する
- raw の sha256 を同梱する（監査ガード）

### 4.3 ノイズ抑制の実装（最小）
- [x] ノイズ候補を正規表現で列挙（rules-v1 に定義）
- [x] for 各ログ行:
      - [x] if “監査クリティカル（エラー/コマンド/判定/失敗理由）” に該当:
            - [x] portable に必ず残す
            - [x] continue
      - [x] else if “ノイズ（temp dir / timing / 乱数風）” に該当:
            - [x] portable から抑制（除外）
            - [x] continue
      - [x] else:
            - [x] portable にそのまま残す
- [x] if “抑制だけだと比較不能” なケースが実測で発生:
      - [x] replace を検討（portable のみ）
      - [x] else:
            - [x] skip（置換は最後）

## 5) docs 更新
- [x] `docs/ops/S8_PLAN.md` を追加/更新
- [x] `docs/ops/S8_TASK.md` を追加/更新
- [x] if RUNBOOK/Walkthrough が repo に存在する:
      - [x] `rg -n "RUNBOOK|Walkthrough" -S docs .` でパス確定
      - [x] 1節だけ S8方針（CI strict / portable view / raw保持）を追記
- [x] else:
      - [x] skip（無理に新設しない）

## 6) 検証（必須）
- [x] `go test ./...`（repo流儀に合わせる）
- [x] if Makefile がある:
      - [x] `make test`
      - [x] `make smoke`（存在するなら）
- [x] if reviewpack submit/verify がある:
      - [x] verify-only を実行して PASS を確認
- [x] if いずれかFAIL:
      - [x] error: 「verify-only PASS を壊した」→ 原因特定して修正、再実行

## 7) 仕上げ（コミット）
- [x] git diff を見て差分が “最小差分” になっているか確認
- [x] if 余計な変更（fmt以外で無関係）が混入:
      - [x] error: 「S8の境界が崩れている」→ 戻してやり直し
- [x] else:
      - [x] `git add -A`
      - [x] `git commit -m "feat(s8): audit tightening (go test strict + portable logs)"`

## 8) Push / PR
- [x] `git push -u origin s8-00-audit-tightening-v1`
- [x] if gh が使える:
      - [x] `gh pr create --fill`
- [x] else:
      - [x] skip（手動PR）

## 9) 完了条件
- [x] CI strict で `-count=1 -mod=readonly` が確認できる（ログ/実装上）
- [x] verify-only PASS 維持
- [x] raw log と portable view が bundle に入り、raw.sha256 と rules-v1 が同梱
- [x] ノイズ抑制は抑制優先で、置換は最終手段として設計に残っている
