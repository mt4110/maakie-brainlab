# S17-02 TASK — IL validator / canonicalizer (Contract v1) [HARDCORE]

## Step 0: Safety Snapshot（落ちない版）
- [x] `cd "$(git rev-parse --show-toplevel)"`
- [x] `git status -sb`
- [x] `git clean -ndx`（dry-run）
- [x] ブランチ確認: `git rev-parse --abbrev-ref HEAD`
- [x] STOP条件: 作業ツリーが汚れていて「意図しない差分」が混ざっている → 先に整理

## Step 1: 編集対象ファイルの“実在”確定（迷子防止）
- [ ] `ROOT="$(git rev-parse --show-toplevel)"`
- [ ] `ls -la "$ROOT/Makefile" "$ROOT/src/il_validator.py" "$ROOT/src/satellite/normalize.py" "$ROOT/tests/test_il_validator.py" "$ROOT/tests/test_satellite_normalize.py"`
- [ ] STOP条件: 期待ファイルが無い → `rg -n "class ILValidator|sat-normalize|sat-collect" "$ROOT"` で探索して確定するまで進まない

## Step 2: Import/Execution Contract を確定（PYTHONPATH=./src を必須化）
### 2.1 Makefile修正（MUST）
- [ ] `Makefile` の `PYENV=PYTHONPATH=.` を **`PYENV=PYTHONPATH=./src:.`** に更新
- [ ] sat系ターゲットが script実行なら、`PYENV`更新だけで import が通ることを保証
  - 追加で堅牢化するなら（任意だが推奨）：
    - `$(PY) -m satellite.collect`
    - `$(PY) -m satellite.normalize`
- [ ] STOP条件: `make test` 前に import で落ちる → `PYENV` / 実行形態を戻して原因を切り分け

### 2.2 “実運用で動く”をテストで固定（MUST）
- [ ] `tests/test_satellite_normalize.py` に **subprocess smoke** を追加：
  - `PYTHONPATH="$ROOT/src"` を渡して `python -m satellite.normalize --help` が exit 0
- [ ] STOP条件: CIでのみ落ちる/ローカルでのみ通る → env差をログに残して原因確定

## Step 3: errors code を Contract集合に正規化（E_TYPE禁止）
- [ ] `src/il_validator.py` の `E_TYPE` を廃止し、Contract集合へマッピング
  - 型/数値/範囲 → `E_SCHEMA`
  - null/禁止フィールド → `E_FORBIDDEN`
  - version不一致 → `E_UNSUPPORTED`
- [ ] `tests/test_il_validator.py` を追従（codeの期待値も固定）
- [ ] STOP条件: 期待コードが揺れる → Contractの集合を優先して統一（下流のif分岐を殺さない）

## Step 4: 数値ルールを“厳密整数のみ”に固定（float/ bool 地雷除去）
- [ ] float は全て FAIL（1.0/1e3含む）
- [ ] bool を int 扱いしない（`type(val) is int` を使用）
- [ ] 53-bit範囲外は FAIL
- [ ] テスト追加（必須）
  - [ ] `1.0` FAIL
  - [ ] `1e3` FAIL
  - [ ] `True` FAIL（int扱い禁止）
  - [ ] `2**53` FAIL、`2**53 - 1` PASS
- [ ] STOP条件: “通って欲しい”誘惑が出る → Contractの目的（表現戦争の芽を潰す）を優先

## Step 5: `il` 型チェックを追加（object必須）
- [ ] `validate()` に `data["il"]` が dict でない場合のエラーを追加（pathは `/il` 推奨）
- [ ] テスト追加：`il: []` / `il: "x"` → FAIL
- [ ] STOP条件: 下流が list を使いたい → それは v2でやる（S17-02では禁止）

## Step 6: canonical JSON 規格を固定（NaN禁止）
- [ ] `ILCanonicalizer.canonicalize()` に `allow_nan=False` を追加
- [ ] テスト：canonicalizeが NaN/Inf を通さない（float自体禁止でも、二重に安全にする）
- [ ] STOP条件: 例外が出る → 例外は FAILとして errors に落とす設計へ（握りつぶし禁止）

## Step 7: docs（SOT）更新（TASKは現実）
- [ ] `docs/ops/S17-02_PLAN.md` を HARDCORE版に更新
- [ ] `docs/ops/S17-02_TASK.md` のチェックを **現実に合わせて**更新（嘘禁止）
- [ ] `file[:]//` や絶対パスを docs に入れない（Contractに違反）
- [ ] STOP条件: docsが事故りそう → 相対パスのみで書き直す

## Step 8: Gate（いつもの儀式）
- [ ] `make test`
- [ ] `go run cmd/reviewpack/main.go submit --mode verify-only`
- [ ] `git status -sb`（clean確認）

## Step 9: Commit/PR（1PRでS17-02を閉じる）
（コミットは刻んでOK、だがPRは1本で完走）
- [ ] Commit案（例）
  - [ ] `fix(s17-02): enforce PYTHONPATH=./src for satellite targets`
  - [ ] `fix(s17-02): align error codes with IL Contract v1`
  - [ ] `fix(s17-02): forbid float and bool-int; enforce 53-bit ints`
  - [ ] `docs(s17-02): update plan/task to hardcore SOT`
- [ ] `git push -u origin s17-02-il-validator-v1`
- [ ] `gh pr create --fill`（または既存PR更新）
