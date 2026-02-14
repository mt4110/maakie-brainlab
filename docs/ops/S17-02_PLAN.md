# S17-02 PLAN — IL validator / canonicalizer (Contract v1) [HARDCORE+]

## 0. SOT（唯一の基準）
- Contract: `docs/il/IL_CONTRACT_v1.md`
- Schema: `docs/il/il.schema.json`（JSONとしてparse可能であること）
- Fixtures:
  - `docs/il/examples/good_min.json` … PASS
  - `docs/il/examples/bad_min.json` … FAIL
  - `docs/il/examples/bad_forbidden_timestamp.json` … FAIL（schema PASS/contract FAIL）

## 1. Goal（目的）
IL Contract v1 に対して検証器（validator）と正規化器（canonicalizer）を実装し、
normalize/pipeline が機械的に OK/NG を判定できるようにする。

- validator：必須/型/禁止フィールド/禁止キー/数値/予約語/Null禁止を固定
- canonicalizer：同一入力→同一出力（canonical JSON / JSONL）
- integration：`src/satellite/normalize.py` に統合し、導線は1本

## 2. Non-Goals（やらない）
- IL v2策定
- 下流評価ロジックの拡張（別Sに分離）

## 3. Design（設計）
### 3.1 Execution Contract（環境依存禁止）
- Pythonモジュールルートは `./src`
- repo root から `make test` / sat-* が一発で動く
- `PYTHONPATH=./src:.` を満たす

### 3.2 Contract固定（曖昧さの芽を潰す）
- `errors` は予約語：入力に現れた時点で FAIL（どこに出ても）
- 数値は厳密整数のみ
  - float 全拒否（1.0, 1e3 も禁止）
  - bool を int 扱いしない
  - 53-bit safe integer のみ
- `il` は object 必須

### 3.3 Error code（集合固定）
`errors[].code` は Contract集合のみ（独自追加禁止）：
- `E_SCHEMA`
- `E_FORBIDDEN`
- `E_AMBIGUOUS`
- `E_MISSING_ARTIFACT`
- `E_NONDETERMINISTIC`
- `E_UNSUPPORTED`

### 3.4 Canonical JSON（規格固定）
- `json.dumps(..., sort_keys=True, separators=(',',':'), ensure_ascii=False, allow_nan=False)`
- JSONLは 1行=1レコード、改行はLF固定

## 4. Acceptance（受け入れ条件）
### Gates（必須）
- `make test` PASS
- `go run cmd/reviewpack/main.go submit --mode verify-only` PASS

### Behavior（根拠）
- good fixture：PASS（errorsは出さない）
- bad fixtures：FAIL（errors length>=1）
- `errors` キーが入力に存在：FAIL（E_SCHEMA）
- float / bool / 53-bit超過：FAIL
- `il` が object 以外：FAIL
- canonical JSON/JSONL が決定論で固定

## 5. Files（編集対象の実パス）
- `Makefile`
- `src/il_validator.py`
- `src/satellite/normalize.py`
- `tests/test_il_validator.py`
- `tests/test_satellite_normalize.py`
- `docs/ops/S17-02_PLAN.md`
- `docs/ops/S17-02_TASK.md`

## 6. Delivery（運用）
- 1PRでS17-02を閉じる（コミットは刻んでOK）
- bundle SHA256 は 1つに固定（食い違い禁止）
