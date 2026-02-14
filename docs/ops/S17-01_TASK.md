# S17-01 TASK（IL Contract v1 Spec）

## Safety Snapshot
- [ ] `cd "$(git rev-parse --show-toplevel)"; git status -sb`
- [ ] `git rev-parse --abbrev-ref HEAD`
- [ ] `git log -1 --oneline --decorate`

## Spec files（固定パス）
- [ ] Create `docs/il/IL_CONTRACT_v1.md`
- [ ] Create `docs/il/il.schema.json`
- [ ] Create `docs/il/examples/good_min.json`
- [ ] Create `docs/il/examples/bad_min.json`

## IL_CONTRACT_v1.md の必須章（抜けたらERROR）
- [ ] Purpose / Terms
- [ ] Input / Output schema（人間向け）
- [ ] Canonicalization rules（決定論）
- [ ] Forbidden（禁止）
- [ ] Error/SKIP policy（停止規約）
- [ ] Examples（GOOD/BADの説明と意図）

## Schema の必須（最低限）
- [ ] `il` object 必須
- [ ] `meta.version` 必須（例：`"il_contract_v1"`)
- [ ] `evidence` object 必須（最低 `hashes` の箱を確保）
- [ ] `errors` は array（存在したら FAIL 扱い、を spec に記述）

## Examples の必須
- [ ] GOOD は keys ソート済み、禁止要素なし
- [ ] BAD は明确な違反（例：`-0` / unsorted key / forbidden timestamp）

## Gates（clean tree）
- [ ] `make test`
- [ ] `go run cmd/reviewpack/main.go submit --mode verify-only`
