# S17-01 TASK（IL Contract v1 Spec）

## Safety Snapshot
- MIGRATED: S21-MIG-S17-01-0001 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S17-01-0002 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S17-01-0003 (see docs/ops/S21_TASK.md)

## Spec files（固定パス）
- MIGRATED: S21-MIG-S17-01-0004 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S17-01-0005 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S17-01-0006 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S17-01-0007 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S17-01-0008 (see docs/ops/S21_TASK.md)

## IL_CONTRACT_v1.md の必須章（抜けたらERROR）
- MIGRATED: S21-MIG-S17-01-0009 (see docs/ops/S21_TASK.md)
- MIGRATED: S21-MIG-S17-01-0010 (see docs/ops/S21_TASK.md)
- [x] Canonicalization rules（決定論）
- [x] Forbidden（禁止）
- [x] Error/SKIP policy（停止規約）
- [x] Examples（GOOD/BADの説明と意図）

## Schema の必須（最低限）
- [x] `il` object 必須
- [x] `meta.version` 必須（例：`"il_contract_v1"`)
- [x] `evidence` object 必須（最低 `hashes` の箱を確保）
- [x] `errors` は array（存在したら FAIL 扱い、を spec に記述）

## Examples の必須
- [x] GOOD は keys ソート済み、禁止要素なし
- [x] BAD は明確な違反（例：`-0` / unsorted key / forbidden timestamp）


## Gates（clean tree）
- [x] `make test`
- [x] `go run cmd/reviewpack/main.go submit --mode verify-only`
