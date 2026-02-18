# S21-05 PLAN — IL Entry Unification → Canonicalize → Minimal Executor (P0→P1→P2)

## Progress
- Current: 99%
- Target: 99% when PR open + CI green + guard logs stable

## Goal (Why)
P0: IL生成/受け取りの“入口”を1本化し、常時検証することで「壊れたILが実行に進む」を構造的に封じる。  
P1: 同じ意味のILが常に同一バイト列になる正規化(canonicalize)を確立し、差分/署名/比較を安定させる。  
P2: ILが“ただのJSON”で終わらず、決定論的に処理を駆動する最小executorを作る（副作用は最小、ログは真実）。

## Absolute Rules (Non-Negotiable)
- exit系の全面禁止（シェル/ Python含む）
  - Shell: exit / return 非0 / set -e / trap EXIT など禁止
  - Python: sys.exit / SystemExit / assert 禁止
- 失敗は `print("ERROR: ...")` で記録し、次工程に進まない判断は **フラグ**で制御する
- 重い処理は分割（1ステップ1本）。固まりそうなら SKIP し、理由を1行残す
- “入口”を通らないIL実行経路を残さない（既存コードは入口に寄せる）

## Scope (Deliverables)
### P0 (Top Priority): Single Entry + Always Validate
- ILの単一エントリポイントを確定（既存があればそこを“唯一の入口”に昇格、無ければ新設）
- 出力/入力ILは必ず `il.schema.json` に通す
- 失敗時も0終了。ただし `can_execute=false` を固定し、次工程（executor）に進ませない

### P1: Canonicalize (Stable Bytes)
- canonicalize規約を固定
  - key順: sort
  - whitespace: なし（separators固定）
  - 禁止フィールド: timestamp系/環境依存/生成時刻系は strip（specに明記）
  - 配列順: 入力順維持（勝手にソートしない。意味が変わるため）
- pipeline順序を固定
  - parse -> canonicalize(strip含む) -> validate(schema) -> write(bytes)

### P2: Minimal Executor
- 最小オペコード集合を定義（例）
  - NOOP
  - SET_VARS
  - SEARCH_TERMS   (副作用なし: terms抽出だけ)
  - RETRIEVE       (最小はSKIPで良い: “未接続”を明示)
  - ANSWER_DRAFT   (結果をoutに書くだけ)
- executorは決定論的
  - 入力(IL+guard)が同じなら出力も同じ
  - ログは `OK/ERROR/SKIP` を1行単位で残す
- guard.can_execute=false の場合は “実行しない” を保証（SKIPで記録）

## Discovery (Paths must be real)
実パスは repo を検索して確定する（推測で固定しない）。
- il.schema.json の実在パス
- 既存のIL関連コード（ask.py / pipeline / eval / etc）
- scripts/ or src/ のどちらが標準か

## Design: Unified Pipeline
State:
- errors: list[str]
- can_execute: bool (default true, but any ERROR makes it false)
- artifacts:
  - il.canonical.json (bytes stable)
  - il.guard.json (machine-readable summary)
  - il.guard.log (human log)

Pseudo (IF/ELSE/FOR/TRY/CATCH style):
- IF schema not found:
    - ERROR: schema missing
    - can_execute=false
- TRY read raw_il
  - CATCH:
    - ERROR: cannot read/parse
    - can_execute=false
- IF can_execute:
    - canonical = canonicalize(raw_il)
    - validate(canonical, schema)
      - IF any validation issue:
          - ERROR: ...
          - can_execute=false
- write artifacts always (even if can_execute=false)

## Tests / Fixtures (Always-on)
- good fixtures: validate OK, canonical stable (exact bytes)
- bad fixtures: validate NG, guard can_execute=false
- Tests must be light and deterministic (no network)

## CI Integration (No-exit philosophy)
- CIは “scriptの終了コード” ではなくログ/出力ファイルを成果物として残す
- 実行の真偽は `il.guard.json` の `can_execute` と `errors[]` が真実

## DoD
- P0:
  - good/bad fixtures が固定され、CIで常時回る
  - “壊れたILがexecutorへ” が構造的に起きない（guardで遮断）
- P1:
  - 同じ入力から同一 `il.canonical.json` が得られる（少なくともテストで固定）
- P2:
  - 最小opcodeが動き、OK/ERROR/SKIPログが残る
  - guard false 時は executor が必ず SKIP する

## Evidence (What to attach in PR)
- 実行ログ:
  - python3 scripts/il_guard.py ... の出力
  - python3 scripts/il_exec.py ... の出力
- 生成物:
  - out_dir/il.canonical.json
  - out_dir/il.guard.json
  - out_dir/il.exec.json / il.exec.log（追加するなら）
