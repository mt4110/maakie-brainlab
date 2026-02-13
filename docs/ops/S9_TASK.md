# S9_TASK (DSL-Alignment / V2 実行レール)

## ルール
- `if / else if / else`
- `for / continue / break`
- `skip`（必ず理由を書いて“監査性を落とさない”）
- `error`（即 exit 2）
- `STOP`（以降の作業禁止）

---

## 0) Preflight（絶対）
- [x] if `git status --porcelain=v1` が空でない → error "dirty tree" → STOP
- [x] `make ci-test`
- [x] if fail → error "baseline ci-test failed" → STOP
- [x] `go run cmd/reviewpack/main.go submit --mode verify-only`
- [x] if fail → error "verify-only baseline failed" → STOP

---

## 1) Docs Hygiene Gate（PR前ゲート）
- [x] `bash ops/check_no_file_url.sh`
- [x] if fail → error "file URL found" → STOP

- [x] `rg -n '^[`]{4}carousel' docs -S && { echo "NG: carousel"; exit 2; } || true`
- [x] if exit=2 → error "carousel found" → STOP

---

## 2) Help Gate（環境差分で落ちない形）
- [x] `go run cmd/reviewpack/main.go diff --help 2>&1 | rg -n '(-|--)kind|(-|--)format'`
- [x] if no match → error "help gate failed: flags not visible" → STOP

---

## 3) Contract Audit（コード構造チェック）
### 3.1 禁止事項
- [x] if `rg -n 'os\.Exit\(|log\.Fatal' internal/reviewpack/diff.go -S` hits → error "diff logic uses os.Exit/log.Fatal" → STOP

### 3.2 error伝播が落ちてないか
- [x] if `comparePortable/compareRaw` が `bool` だけ返して err を捨てている → error "error swallowed (false-negative risk)" → STOP
- [x] else continue

### 3.3 raw nucleus 契約
- [x] if raw mode が `.sha256` を比較せず、実ファイルhashで代用している → error "raw nucleus contract violated" → STOP
- [x] if sidecar欠落が exit 1/0 になる → error "must be exit 2" → STOP

### 3.4 json 契約
- [x] if `--format json` が WARN 文言混入や非JSON出力になる → error "json contract violated" → STOP

---

## 4) Tests（false-negative潰し）
- [x] `make ci-test`
- [x] if fail → error "tests failed" → STOP

- [x] for each test case (portable/raw/json/error paths):
  - [x] if portable missing → exit 2
  - [x] if raw sidecar missing → exit 2
  - [x] if diff found → exit 1
  - [x] if no diff → exit 0
  - [x] if same inputs twice → output identical（determinism）

- [x] if any unstable fixture (timestamp/temp path) → continue（fixturesを正規化）
- [x] else continue

---

## 5) Proof of Work（bundle-to-bundle実証）
### 5.1 A/B bundle作成（再現可能）
- [x] if gitがdirty → error → STOP
- [x] create bundle A（コマンドはrepoの正規ルートに従う）
- [x] introduce controlled change（portableにだけ差分が出る変更が望ましい）
  - [x] if raw に影響しそう → continue（変更を差し替える）
  - [x] else continue
- [x] commit change（pack preflight のため）
- [x] create bundle B

### 5.2 diff 実行（exit code検証）
- [x] run portable:
  - `go run cmd/reviewpack/main.go diff --kind portable --format text <A> <B>`
  - [x] if expected diff → exit 1
  - [x] else if no diff → exit 0
  - [x] else if error → exit 2

- [x] run raw nucleus:
  - `go run cmd/reviewpack/main.go diff --kind raw --format text <A> <B>`
  - [x] if sidecar欠落/壊れ → exit 2
  - [x] if sha256差分 → exit 1
  - [x] if no sha256差分 → exit 0

- [x] run json:
  - `go run ... diff --kind portable --format json <A> <B> | jq -e . >/dev/null`
  - [x] if jq fail → error "non-json output" → STOP

---

## 6) Bundle Reality Check（“現実に入ってるか”）
- [x] extract bundle B
- [x] if `src_snapshot/internal/reviewpack/diff.go` に `--kind/--format` / `(bool, error)` / nucleus enforcement が無い → error "bundle snapshot old/invalid" → STOP
- [x] else continue

---

## 7) Walkthrough（嘘禁止）
- [x] update walkthrough with:
  - exact commands (```bash)
  - bundle sha256
  - diff outputs (text + json validation)
  - no file[:]//, no carousel blocks
- [x] if walkthrough claims feature not present → error "walkthrough mismatch" → STOP

---

## 8) Final Gates（PR前）
- [x] `bash ops/check_no_file_url.sh` PASS
- [x] `make ci-test` PASS
- [x] `go run cmd/reviewpack/main.go submit --mode verify-only` PASS
- [x] break → PR ready

---

## 9) PR ワンライナー（いつもの最短レール）
- [x] `git status -sb`
- [x] `git diff --stat`
- [x] `git add -A`
- [x] `git commit -m "fix(reviewpack): diff hardening v2 (exit2, raw nucleus, json, gates)"`
- [x] `git push`
- [x] `gh pr checks --watch`
