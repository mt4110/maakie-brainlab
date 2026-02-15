# PLAN: S17-02 IL validator / canonicalizer (Contract v1) [HARDCORE+]
Status: DONE
Owner: ambi
Progress: 100%

## Goal（目的）
- IL Contract v1 に対する強固な検証器 (validator) と正規化器 (canonicalizer) を実装する。
- 数値の厳密性、予約語 `errors` の排除、および決定論的な JSON シリアライズを保証する。

## Non-Goal（やらないこと）
- IL v2 の策定。
- 下流評価ロジックの拡張（別フェーズに分離）。

## Inputs（入力）
- Repo: `git rev-parse --show-toplevel`
- Target branch: `s17-02-il-validator-v1` (Merged)
- Target files:
    - `src/il_validator.py`
    - `src/satellite/normalize.py`
    - `tests/test_il_validator.py`

## Outputs（出力）
- Code changes: `il_validator.py` (HARDCORE+ implementation).
- Evidence: `reviewpack submit --mode verify-only`
- PR: #50 (Merged)

## Invariants（絶対に壊さないもの）
- Determinism: 同一入力に対して常に同一の canonical JSON を生成すること。
- Auditability: `errors` コードを Contract v1 集合に限定すること。
- Safety: `errors` 配下への再帰的バリデーションを禁止し、ノイズ増殖を防ぐこと。

## Stop Conditions（停止条件）
- error: `errors` キーが入力の任意の位置に存在する。
- error: 数値が float, bool, または 53-bit 範囲外である。
- error: `il` フィールドが object 以外。

## Plan Pseudocode（疑似コード）
### P0: Safety Snapshot
- `repo_root` 取得。
- `git status` 確認。

### P1: Resolve Paths
- `VALIDATOR_PY = "src/il_validator.py"`
- `NORMALIZE_PY = "src/satellite/normalize.py"`
- 実在確認後、パスを記録。

### P2: Implement (HARDCORE+)
- `ILValidator`:
    - for key in data: if key == "errors" -> add_error(E_SCHEMA).
    - _validate_recursive: 予約語 `"errors"` 検出でノイズ防止のため `continue`。
    - type(val) is int (no bool/float) + 53-bit range check.
- `ILCanonicalizer`:
    - `json.dumps(..., sort_keys=True, separators=(',',':'), allow_nan=False)`.
- `normalize.py`:
    - `sys.path.insert(0, str(ROOT / "src"))` による import 契約固定。

### P3: Gates
- `make test` PASS。
- `verify-only` PASS。

### P4: Commit/PR
- PR #50 本文への SHA256  rituals 記録。

## Dead-Angle Check（死角チェック）
- 「既に存在」する `errors` キーが下流に混乱を招かないか？ → 入力段階で即 FAIL させる設計で排除。
- import 先が CWD によって揺れないか？ → `sys.path` を `src` に固定して解決。
