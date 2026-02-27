# S22-02 TASK — P2 IL executor minimal

> 原則：落ちない / exit禁止 / 1ステップ1観測 / 真実はログに固定

## 0. Preflight (読むだけ・軽い)

- [x] `rg -n "IL_CONTRACT|canonicalize|il_guard|il_validator" docs/il scripts src tests`
- [x] `ls -la src scripts docs/il tests`

## 1. Contract 固め（設計の核）

- [x] `docs/il/IL_EXEC_CONTRACT_v1.md` を新規作成（report/result v1を固定）
- [x] reportの `overall_status` 決定ルールを明文化（ERROR優先、次OK、全部SKIPならSKIP）
- [x] resultは `overall_status==OK` のときのみ生成、を明文化

## 2. Fixtures（決定論の燃料）

- [x] `tests/fixtures/il_exec/` を作成
- [x] `tests/fixtures/il_exec/il_min.json`（SEARCH_TERMS→RETRIEVE→ANSWER→CITE の最小構成）
- [x] `tests/fixtures/il_exec/retrieve_db.json`（index + docs）

## 3. Executor 実装（例外で落ちない）

- [x] `src/il_executor.py` を作成
- [x] `scripts/il_exec_run.py` を作成（CLI）
- [x] 各stepで OK/ERROR/SKIP + reason を必ず埋める
- [x] reportを常にout_dirに書く（例外が出ても書く）
- [x] overall_statusがOKのときだけ result を書く

## 4. Selftest（exitしない検証の柱）

- [x] `scripts/il_exec_selftest.py` を作成
- [x] fixture入力でexecutorを実行
- [x] report/resultの存在/内容チェック → printで出す

## 5. 既存ルートへ統合

- [x] `make verify-il` に selftest を組み込む
- [x] 既存の `scripts/il_check.py` の責務を壊さない

## 6. STATUS更新

- [x] `docs/ops/STATUS.md` に S22-02 行追加（S22-01の直後）
- [x] S22-02 を `1% (Kickoff: IL executor minimal)` にする

## 7. Gates（軽→重）

- [x] Light: `python3 scripts/il_exec_selftest.py`
- [x] Medium: `make verify-il`

## 8. PR

- [x] `git push -u origin s22-02-il-executor-min-v1`
- [x] PR本文に SOT/Evidence/Gates を入れる
