# S8_TASK — Determinism / Audit Tightening
(あんびちゃそ実装タスク：迷子防止の制御構文つき)

## 0) Preflight (必須)
- [ ] if `git status --porcelain=v1` が空 ではない:
      - [ ] error: 「作業ツリーが汚れている。stash/commitしてからやり直し」→ STOP
- [ ] if 現在ブランチ != main:
      - [ ] `git switch main`
- [ ] `git pull --ff-only`
- [ ] `git fetch origin --prune`

## 1) ブランチ作成
- [ ] `git switch -c s8-00-audit-tightening-v1`

## 2) 編集対象ファイルパスの確定（勝手に決めない）
- [ ] `ls -la internal/reviewpack` を実行して存在確認
- [ ] if `internal/reviewpack` が存在しない:
      - [ ] error: 「想定ディレクトリが無い。repo構成が違う」→ STOP
- [ ] `rg -n "go test" -S .` を実行
- [ ] if ヒット0件:
      - [ ] `rg -n "exec\\.Command\\(\"go\"|\\bgo\\b.*test" -S internal cmd ops .` を実行
- [ ] if それでもヒット0件:
      - [ ] error: 「go test 実行箇所が見つからない。実装方針が立てられない」→ STOP
- [ ] for ヒットした箇所を上から確認:
      - [ ] if “reviewpack の実行ステップ” で go test を呼んでいる箇所を見つけた:
            - [ ] break（そのファイルがS8의 主戦場）
      - [ ] else:
            - [ ] continue

## 3) PR33相当: go test 実行オプション設計を実装（最小差分）
### 3.1 方針
- CI(strict) では `-count=1 -mod=readonly` を必ず付与
- Local(permissive) は既存挙動維持（破壊しない）
- Localで strict を opt-in できる導線を作る（環境変数 or 既存modeに統合。新フラグ乱立は避ける）

### 3.2 実装手順
- [ ] if go test コマンド組み立てが “直書き”:
      - [ ] 最小のヘルパー関数/分岐を同一ファイル内に追加して引数を組み立てる
- [ ] else if 既に “mode(strict/permissive)” っぽい概念がある:
      - [ ] その分岐に乗せて `-count=1 -mod=readonly` を CI(strict) 側だけに追加
- [ ] else:
      - [ ] error: 「既存の設計軸が無いのに新軸を作ると破綻する。設計見直し」→ STOP

### 3.3 失敗時UX（-mod=readonly 系）
- [ ] go test が失敗したとき:
      - [ ] if stderr に `-mod=readonly` 由来の文言が含まれる（例: updates to go.mod needed / go.sum updates needed 等）:
            - [ ] “補助メッセージ” を追加（rawはそのまま）
      - [ ] else:
            - [ ] 既存のエラー出しを維持（捏造しない）

## 4) PR34相当: ログノイズ抑制（抑制→置換の順、監査ガード付き）
### 4.1 まず現状把握
- [ ] `rg -n "log(s)?/|bundle.*log|portable|sanitize|redact" -S internal/reviewpack docs .` を実行
- [ ] if bundle にログ同梱が無い:
      - [ ] skip: 「S8のportable view設計は“保存先”が無いと成立しない」→ STOP（設計見直し）
- [ ] else:
      - [ ] continue

### 4.2 実装ルール（絶対に守る）
- raw log は削らない（監査の真実）
- portable view は “表示/比較用” として追加するだけ
- portable ルールは versioned（rules-v1 など）で同梱する
- raw の sha256 を同梱する（監査ガード）

### 4.3 ノイズ抑制の実装（最小）
- [ ] ノイズ候補を正規表現で列挙（rules-v1 に定義）
- [ ] for 各ログ行:
      - [ ] if “監査クリティカル（エラー/コマンド/判定/失敗理由）” に該当:
            - [ ] portable に必ず残す
            - [ ] continue
      - [ ] else if “ノイズ（temp dir / timing / 乱数風）” に該当:
            - [ ] portable から抑制（除外）
            - [ ] continue
      - [ ] else:
            - [ ] portable にそのまま残す
- [ ] if “抑制だけだと比較不能” なケースが実測で発生:
      - [ ] replace を検討（portable のみ）
      - [ ] else:
            - [ ] skip（置換は最後）

## 5) docs 更新
- [x] `docs/ops/S8_PLAN.md` を追加/更新
- [x] `docs/ops/S8_TASK.md` を追加/更新
- [ ] if RUNBOOK/Walkthrough が repo に存在する:
      - [ ] `rg -n "RUNBOOK|Walkthrough" -S docs .` でパス確定
      - [ ] 1節だけ S8方針（CI strict / portable view / raw保持）を追記
- [ ] else:
      - [ ] skip（無理に新設しない）

## 6) 検証（必須）
- [ ] `go test ./...`（repo流儀に合わせる）
- [ ] if Makefile がある:
      - [ ] `make test`
      - [ ] `make smoke`（存在するなら）
- [ ] if reviewpack submit/verify がある:
      - [ ] verify-only を実行して PASS を確認
- [ ] if いずれかFAIL:
      - [ ] error: 「verify-only PASS を壊した」→ 原因特定して修正、再実行

## 7) 仕上げ（コミット）
- [ ] git diff を見て差分が “最小差分” になっているか確認
- [ ] if 余計な変更（fmt以外で無関係）が混入:
      - [ ] error: 「S8の境界が崩れている」→ 戻してやり直し
- [ ] else:
      - [ ] `git add -A`
      - [ ] `git commit -m "feat(s8): audit tightening (go test strict + portable logs)"`

## 8) Push / PR
- [ ] `git push -u origin s8-00-audit-tightening-v1`
- [ ] if gh が使える:
      - [ ] `gh pr create --fill`
- [ ] else:
      - [ ] skip（手動PR）

## 9) 完了条件
- [ ] CI strict で `-count=1 -mod=readonly` が確認できる（ログ/実装上）
- [ ] verify-only PASS 維持
- [ ] raw log と portable view が bundle に入り、raw.sha256 と rules-v1 が同梱
- [ ] ノイズ抑制は抑制優先で、置換は最終手段として設計に残っている
