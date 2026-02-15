# S17-02 TASK — IL validator / canonicalizer (Contract v1) [HARDCORE+]

## SOT（唯一の基準）
- Contract: docs/il/IL_CONTRACT_v1.md
- Schema: docs/il/il.schema.json（JSONとしてparse可能であること）
- Fixtures:
  - docs/il/examples/good_min.json … PASS
  - docs/il/examples/bad_min.json … FAIL（errors length>=1）
  - docs/il/examples/bad_forbidden_timestamp.json … FAIL（schema PASSでも contract FAIL）

## MUST（炉心ルール：妥協禁止）
- 実行契約：Pythonモジュールルートは `./src`。repo root から一発で動く（テストだけ通る禁止）
- import契約の優先順位：**最終責任は Makefile（`PYTHONPATH=./src:.`）**。`src/satellite/normalize.py` の `sys.path.insert` は保険（実行方法/CWD差の事故防止）であり、競合したら Makefile 契約に合わせる。
- `errors` は予約語：入力に現れた時点で FAIL（トップ/ネスト問わず）
- 数値：厳密整数のみ（float全拒否、boolをint扱い禁止、53-bit範囲のみ）
- top-level `il` は object 必須
- `errors[].code` は Contract集合のみ（独自コード禁止）
- canonical JSON 規格：sort_keys / separators / ensure_ascii / allow_nan=False を固定
- docs は現実：TASKは実行ログ。嘘禁止

---

## Step 0: Safety Snapshot（落ちない版）
- [x] `cd "$(git rev-parse --show-toplevel)"`
- [x] `git status -sb`
- [x] `git clean -ndx`（dry-run）
- [x] `git rev-parse --abbrev-ref HEAD`

STOP:
- 作業ツリーが汚い（意図しない差分がある）→ 先に整理。混ぜない。

---

## Step 1: 編集対象ファイルの実パス確定（迷子防止）
- [x] `ROOT="$(git rev-parse --show-toplevel)"`
- [x] 実在確認（無ければ探索へ分岐）:

  - [x] `ls -la "$ROOT/Makefile"`
  - [x] `ls -la "$ROOT/src/il_validator.py"`
  - [x] `ls -la "$ROOT/src/satellite/normalize.py"`
  - [x] `ls -la "$ROOT/tests/test_il_validator.py"`
  - [x] `ls -la "$ROOT/tests/test_satellite_normalize.py"`
  - [x] `ls -la "$ROOT/docs/ops/S17-02_PLAN.md" "$ROOT/docs/ops/S17-02_TASK.md"`

FOR（探索：見つけたらbreak、見つからなければcontinue）
- [x] 見つからない/名前が違う場合：
  - [x] `rg -n "PYENV=|PYTHONPATH=|class ILValidator|ILCanonicalizer|from il_validator|sat-normalize|sat-collect" "$ROOT" || true`

STOP:
- 実パスが確定しない → その先の編集禁止（“推測で編集”を封じる）

---

## Step 2: 実行契約を固定（PYTHONPATH=./src を必須化）
- [x] Makefile の `PYENV` を確認し、`PYTHONPATH=./src:.` を満たすこと

  - [x] `rg -n "PYENV=.*PYTHONPATH" "$ROOT/Makefile" || true`

IF（契約が弱い）:
- [x] `PYENV=PYTHONPATH=.` 等が残っている → `PYENV=PYTHONPATH=./src:.` に修正してコミット対象

任意（より堅牢）:
- [x] sat系がスクリプト実行なら、可能なら `python -m satellite.normalize` 形式に寄せる (今回はMakefile contractで吸収)

STOP:
- import が実運用で壊れる兆候（Makefile契約が満たせない）→ 先にここを直す。炉心の前に足場。

---

## Step 3: HARDCORE+ 封印（予約語 errors を入力禁止にする）
目的：下流が「成功なのに errors がある」等で悩む世界を永久に殺す。

- [x] `src/il_validator.py` に予約語チェックを追加：
  - [x] dict走査で key が `"errors"` を検出したら `E_SCHEMA` を追加して FAIL
  - [x] ノイズ増殖防止：`errors` 配下は深掘りせず `continue`

期待：
- 入力のどこに現れても FAIL（/errors, /il/errors, /meta/errors など全て）

STOP:
- 予約語の扱いが曖昧（場所によって許可など）→ 禁止一択に統一（“例外”は未来の地雷）

---

## Step 4: 型と数値の完全固定（float / bool 地雷を殺す）
- [x] `src/il_validator.py` の int検証ロジックを確認・固定：
  - [x] `type(val) is int` を使用（bool混入を防ぐ）
  - [x] `isinstance(val, float)` は即FAIL（1.0 / 1e3 を殺す）
  - [x] 53-bit safe integer（±(2^53-1)）範囲外は FAIL

- [x] top-level `il` が object（dict）必須：
  - [x] `il` が list/string 等なら `E_SCHEMA`（path は `/il` 推奨）

STOP:
- “通してほしい”誘惑が出る → Contract目的（表現戦争の芽を潰す）を優先。例外は v2。

---

## Step 5: errors.code を Contract集合に正規化（独自コード禁止）
- [x] `errors[].code` を Contract集合に統一（例）：
  - [x] schema/型/範囲/形 → `E_SCHEMA`
  - [x] 禁止フィールド/禁止キー → `E_FORBIDDEN`
  - [x] version不一致 → `E_UNSUPPORTED`
  - [x] その他は Contractの集合から選ぶ（独自追加禁止）

STOP:
- codeが揺れる → 下流が死ぬ。統一するまで進むな。

---

## Step 6: canonical JSON 規格を固定（allow_nan=False）
- [x] `ILCanonicalizer.canonicalize()` を次で固定：
  - [x] `sort_keys=True`
  - [x] `separators=(',',':')`
  - [x] `ensure_ascii=False`
  - [x] `allow_nan=False`

STOP:
- 例外が出る → 握りつぶさず、FAILとして errors に落とす（嘘禁止）

---

## Step 7: normalize 統合（導線は1本、import真実も1本）
- [x] `src/satellite/normalize.py` が validator/canonicalizer を必ず通す（導線1本）

- [x] importの真実を一本化：
  - [x] `sys.path.insert(0, str(ROOT / "src"))` を採用（ROOT 直下ではなく src）
  - [x] `from il_validator import ...` が確実に動く

STOP:
- CWD依存の挙動が残る → “たまたま動く”は禁止。契約で固定。

---

## Step 8: テスト（仕様を“未来の自分の鎧”にする）
### 8.1 `tests/test_il_validator.py`（炉心ルールを固定）
- [x] 予約語 `errors`：
  - [x] top-level `errors` を含む入力が FAIL
  - [x] エラーに `E_SCHEMA` と path `/errors` を含む

- [x] 数値：
  - [x] `1.0` FAIL
  - [x] `1e3` FAIL（float）
  - [x] `True` FAIL（boolをint扱い禁止）
  - [x] `2**53 - 1` PASS
  - [x] `2**53` FAIL

- [x] il 型：
  - [x] `il: []` FAIL
  - [x] `il: "x"` FAIL

- [x] code集合：
  - [x] `errors[].code` が Contract集合に属することを assert（独自コード禁止）

### 8.2 `tests/test_satellite_normalize.py`（実運用import契約の固定）
- [x] subprocess smoke を追加・維持：
  - [x] env `PYTHONPATH="$ROOT/src"` で `python -m satellite.normalize --help` が exit 0

STOP:
- ローカルだけ通る/CIだけ落ちる → env差をログに残し、契約（PYTHONPATH）で吸収するまで進むな。

---

## Step 9: docs（SOT）更新（TASKは現実、嘘禁止）
- [x] `docs/ops/S17-02_PLAN.md` に HARDCORE+（予約語errors禁止）を反映
- [x] このTASK自体を “現実の進捗” に同期：
  - [x] 完了した項目は [x]

禁止：
- [x] docsに “ローカルファイル参照のURL” を生文字列で書かない（reviewpackスキャンで落ちる）
  - 表現は「file URL pattern」「ローカルパス参照」等に言い換える

---

## Step 10: 禁止パターンの自己スキャン（最後に刺さらない）
- [x] docs/src/tests をスキャン（生文字列の混入を防ぐ）
  - [x] `rg -n "file:/{2}" docs src tests -S || true`

STOP:
- 1件でも出た → docsから除去 or 表現を変更（生文字列を残さない）

---

## Step 11: Gate（真実の確定）
- [x] `make test`
- [x] `go run cmd/reviewpack/main.go submit --mode verify-only`
- [x] PR本文に貼る前に SHA256 を再計算して一致確認：`shasum -a 256 "$(ls -1t review_bundle_*.tar.gz | head -n 1)"`（出力が reviewpack の SHA256 行と一致すること）
- [x] `git status -sb`（clean確認）

STOP:
- どれか落ちた → その場で原因確定→修正（次へ進まない）

---

## Step 12: Commit / PR（1PRでS17-02を閉じる）
（コミットは刻んでOK。だがPRは1本で完走。）

推奨コミット粒度（例）:
- [x] `fix(s17-02): enforce reserved errors key + unify normalize sys.path to src`
- [x] `fix(s17-02): harden int rules (no float/bool, 53-bit range)`
- [x] `fix(s17-02): normalize error codes to Contract v1 set`
- [x] `test(s17-02): add subprocess smoke for satellite normalize import contract`
- [x] `docs(s17-02): sync plan/task to HARDCORE+ reality`

コマンド:
- [ ] `git add -A`
- [ ] `git commit -m "<message>"`
- [ ] `git push -u origin HEAD`
- [ ] `gh pr list --head "$(git rev-parse --abbrev-ref HEAD)" --state all`
- [ ] PRが無ければ `gh pr create --fill`

DONE条件:
- [ ] CI green
- [ ] reviewpack verify-only PASS
- [ ] bundle SHA256 を PR本文/ログ/メモで 1つに固定（食い違い禁止）
- [ ] PR本文に貼る bundle SHA256 は、貼る直前にローカルで再計算して確定値として貼る（例：`shasum -a 256 "$(ls -1t review_bundle_*.tar.gz | head -n 1)"`。`sha256sum` がある環境なら置き換え可）
