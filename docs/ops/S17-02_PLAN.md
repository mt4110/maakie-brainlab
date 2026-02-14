# S17-02 PLAN — IL validator / canonicalizer (Contract v1) [HARDCORE]

## 0. SOT（唯一の基準）
- Contract: `docs/il/IL_CONTRACT_v1.md`
- Schema: `docs/il/il.schema.json`（少なくともJSONとしてparse可能であること）
- Fixtures:
  - `docs/il/examples/good_min.json` … PASS
  - `docs/il/examples/bad_min.json` … FAIL
  - `docs/il/examples/bad_forbidden_timestamp.json` … FAIL（schema PASSでも contract FAIL）

## 1. Goal（目的）
LLM出力を検証可能な中間言語（IL）として扱うために、以下を実装し「下流が悩まない」世界を作る。

1) validator
- Contract v1 に対する検証（必須/型/禁止フィールド/禁止キー/数値/Null禁止）
- Failure時は `errors` を必ず出し length>=1（ContractのSuccess/Failure規約）

2) canonicalizer
- 同一入力→同一出力（canonical JSON / JSONL）
- JSONとして不正な値（NaN/Infinityなど）を排除

3) integration（導線は1本）
- `src/satellite/normalize.py` に統合し、pipelineが必ず validator/canonicalizer を通る

## 2. Non-Goals（やらない）
- IL v2策定はしない
- 下流evalロジックの拡張はしない（S17-xxで扱う）

## 3. MUST（規約：ここが炉心）
### 3.1 Import/Execution Contract（環境依存禁止）
- 公式のPythonモジュールルートは `./src`
- `make test` / `make sat-collect` / `make sat-normalize` は repo root から一発で動く
- `PYENV` は `PYTHONPATH=./src:.` を含む（`PYTHONPATH=.` 単独は禁止）

### 3.2 errors の code 集合固定（Contract準拠）
`errors[].code` は次のみ：
- `E_SCHEMA|E_FORBIDDEN|E_AMBIGUOUS|E_MISSING_ARTIFACT|E_NONDETERMINISTIC|E_UNSUPPORTED`
※独自コード禁止（E_TYPE等）

### 3.3 数値（厳密整数のみ）
- floatは全てFAIL（1.0/1e3含む）
- boolをint扱いしない
- intは53-bit範囲のみ

### 3.4 Top-level shape
- top-levelはobject
- 必須キー: `il`,`meta`,`evidence`
- `il` は object 必須（list/string禁止）
- meta.version は `il_contract_v1` 必須

### 3.5 canonical JSON 規格
- `json.dumps(... sort_keys=True, separators=(',',':'), ensure_ascii=False, allow_nan=False)`
- JSONLは改行1つ、CRLF禁止

##  Acceptence（受け入れ条件）
### Gates（必須）
- `make test` PASS
- `go run cmd/reviewpack/main.go submit --mode verify-only` PASS

### Behavior（根拠つき）
- `good_min.json` → PASS（errors省略）
- `bad_min.json` → FAIL（errors length>=1）
- `bad_forbidden_timestamp.json` → FAIL（errors length>=1）
- float（1.0/1e3/NaN/Inf相当）は FAIL
- `il` が object 以外（list/string）は FAIL
- canonical JSON/JSONL が決定論（キー順、区切り固定、NaN禁止）

## 5. Files（編集対象の実パス）
- `Makefile`（PYENV / sat-* 実行契約）
- `src/il_validator.py`（validator/canonicalizerの炉心）
- `src/satellite/normalize.py`（導線1本の統合点）
- `tests/test_il_validator.py`（Contractルールの固定）
- `tests/test_satellite_normalize.py`（統合後の正しさ固定）
- `docs/ops/S17-02_PLAN.md` / `docs/ops/S17-02_TASK.md`（SOT更新）
