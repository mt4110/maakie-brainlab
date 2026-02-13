# S9_PLAN (DSL-Alignment / V2)

## 0. Goal

S9は「比較可能な監査（bundle間diff）」を完成させる。
“動く”より 嘘をつかない（false-negative禁止） が最優先。

## 1. Non-Negotiable Contract

- **portable-first**: 比較表示は portable が第一選択
- **raw is truth**: raw は監査の真実。portable は比較ビュー（ノイズ除去OK）
- **Raw Nucleus**: logs/raw/**/*.sha256 の内容比較が核
  - raw内の各ログは 必ず sidecar .sha256 を要求
  - 欠落・不正・読めない → error（exit 2）
- **Strict Exit Codes**
  - 0: no diff
  - 1: diff found
  - 2: error（I/O・欠落・契約違反・壊れたbundle等）
- **Error Propagation**
  - diffロジック内で os.Exit / log.Fatal 禁止
  - runDiff は (diffFound bool, err error) で上へ伝播
  - エラー握りつぶし禁止（WalkDir/ReadFile/Hash/exec の err は必ず上へ）
- **Determinism**
  - path順序：lexicographic（スラッシュ区切りで固定）
  - 改行：\n 固定
  - 出力：summary → files の順で固定
  - truncate：固定ルールのみ（上限超過は deterministic に）

## 2. CLI Surface

`reviewpack diff [flags] <bundleA> <bundleB>`

- **flags**:
  - `--kind=portable|raw|both` (default: portable)
  - `--format=text|json` (default: text)
- **help gate**:
  - helpは stderr に出ても拾えるように 2>&1 が前提

## 3. Diff Scope Boundary

### 3.1 portable mode
- **対象**: logs/portable/**
- **処理**: portable は 正規化（noise suppression）OK
  - duration → `<DURATION>`
  - cache marker → `<CACHED>`
  - temp/random suffix/path → `<TMP>/<BUNDLE_ID>` 等（固定ルール）
- **unified diff**:
  - diff -u を使うなら 失敗時は error(2)（監査比較の品質担保）
  - 例外として「diffコマンドが無い環境」をサポートするなら Planに明記し、fallbackは deterministic に

### 3.2 raw mode (nucleus)
- **対象**: logs/raw/**/*.sha256（これが核）
- `.sha256` の内容（hex）を比較する
- logs/raw/`<file>` が存在するなら `<file>.sha256` は必須
- 無い → error(2)

## 4. Output Contract

### 4.1 text
- summary（counts + kind + format）
- file entries（added/removed/modified）
- if --kind both：portable結果 → raw結果 の順（固定）

### 4.2 json
- stdout は JSONのみ（WARN文字列混ぜない）
- **shape**（最低限）:
  ```json
  { "kind": "...", "format": "json", "summary": {...}, "added": [...], "removed": [...], "modified": [...] }
  ```
- 配列は必ずソート（deterministic）

## 5. Gates (PR前に必ずPASS)

- `bash ops/check_no_file_url.sh` PASS
- `rg -n '^[]{4}carousel' docs -S` hits = 0
- `make ci-test` PASS
- `go run cmd/reviewpack/main.go submit --mode verify-only` PASS
- `go run ... diff --help 2>&1 | rg '(-|--)kind|(-|--)format'` PASS
- **bundle reality**:
  - bundle展開後 `src_snapshot/internal/reviewpack/diff.go` が 新実装であること

## 6. Fixed File Paths

- **code**:
  - `internal/reviewpack/diff.go`
  - `internal/reviewpack/diff_test.go`
  - `internal/reviewpack/app.go`
  - `internal/reviewpack/flags.go`
  - `internal/reviewpack/utils.go`
- **docs**:
  - `docs/ops/S9_PLAN.md`
  - `docs/ops/S9_TASK.md`
  - `docs/reviewpack/WALKTHROUGH.md`（またはS9専用）

## 7. Acceptance Criteria

- exit code契約（0/1/2）が壊れていない
- error を 0/1 に落とさない（false-negative禁止）
- raw nucleus の sidecar 要求が強制される
- json が deterministic で機械可読
- verify-only baseline が壊れない
- docs hygiene がPASS
- bundle reality check がPASS
