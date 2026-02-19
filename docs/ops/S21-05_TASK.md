# S21-05 TASK — P0→P1→P2 (Single PR)

## Progress
- Start: 0%
- Update to 1% after kickoff commit
- Update to 99% when PR open and checks/logs stable

---

## 0) Kickoff (safe / no-exit)
- [x] repo root を取る（無ければ ERROR を出して止める＝以降の手順は実行しない）
  - Command:
    - `ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"; if [ -z "$ROOT" ]; then echo "ERROR: not in git repo"; else echo "OK: repo=$ROOT"; fi`
- [x] main を最新化してブランチ作成（失敗しても落ちない）
  - Command:
    - `BR="s21-05-il-entry-canon-executor-v1"; cd "$ROOT" || true; git switch main 2>/dev/null || true; git pull --ff-only 2>/dev/null || true; git switch -c "$BR" 2>/dev/null || true; git status -sb 2>/dev/null || true`
- [x] Plan/Task ファイル作成（既にあれば SKIP）
  - Files:
    - `docs/ops/S21-05_PLAN.md`
    - `docs/ops/S21-05_TASK.md`

---

## 1) Discovery: 実パス確定（推測で書かない）
- [x] il.schema.json を探す（軽量）
  - Command:
    - `cd "$ROOT" || true; ls -la 2>/dev/null || true; rg -n --hidden --no-heading "il\.schema\.json" . 2>/dev/null || true`
  - Rule:
    - 見つからない場合はこのPRで新設する（ただし置き場所は既存規約に合わせる）
- [x] IL関連の既存入口候補を列挙（軽量）
  - Command:
    - `cd "$ROOT" || true; for p in src/ask.py src/il_pipeline.py src/il/*.py scripts/*.py eval/*.py; do if [ -e "$p" ]; then echo "OK: found $p"; else echo "SKIP: missing $p"; fi; done`
- [x] 既存の “ILを実行っぽく扱ってる箇所” を当たり（軽量）
  - Command:
    - `cd "$ROOT" || true; rg -n --no-heading "IL|il_|schema|canonical|executor|opcode" src scripts eval tests 2>/dev/null || true`

STOP条件（ここで止める判断、exitはしない）:
- [ ] schema と入口候補が全く見えない → `ERROR: cannot locate IL surfaces` を残し、以降は設計だけコミットして終える（実装に突っ込まない）

---

## 2) P0: 入口一本化 + 常時検証 (il_guard)
- [ ] `scripts/` or `src/` の標準置き場を確定（見つけた方に合わせる）
  - Command:
    - `cd "$ROOT" || true; for d in scripts src cmd; do if [ -d "$d" ]; then echo "OK: dir=$d"; else echo "SKIP: no dir=$d"; fi; done`
- [/] 新規: `scripts/il_guard.py` を追加（常に0終了、ログで真実）
  - Behavior:
    - raw IL を読む（読めないなら ERROR）
    - canonicalize(strip含む)
    - schema validate（NGなら ERROR）
    - `out_dir/il.guard.json` に `can_execute` と `errors[]` を必ず出す
- [ ] 既存のIL生成/受け取り箇所を入口に寄せる（“入口を通らない経路”を残さない）
  - Rule:
    - 直接 executor を呼ぶ/直接 validate を抜く経路が残ったら ERROR 扱い

---

## 3) Fixtures & Always-on checks (軽量)
- [/] fixtures 置き場を決める（tests/ が無ければ最小で作る）
  - Proposed:
    - `tests/fixtures/il/good/*.json`
    - `tests/fixtures/il/bad/*.json`
- [/] good/bad を最低1つずつ固定
  - good: schema OK で can_execute=true
  - bad: schema NG で can_execute=false
- [/] “常時回す”軽量チェックを追加
  - Option A: `python3 scripts/il_guard.py --fixtures ...` モード
  - Option B: `python3 scripts/il_check.py` を追加して fixture を総当り
  - Rule:
    - どちらでも常に0終了
    - ただし `ERROR:` 行が出る＝失敗の真実（CI/merge guardが拾える）

---

## 4) P1: canonicalize 規約の確立（同一バイト列）
- [ ] canonicalize ルールをコードとドキュメントに固定
  - sort_keys=true
  - separators=(",",":")
  - strip forbidden fields (timestamp / generated_at / env)
  - arrays are order-preserving
- [ ] 同一入力 → 同一 `il.canonical.json` の bytes を fixture で固定
  - Approach:
    - fixture input を canonicalize して期待出力をファイルで固定（差分が出たら検知）
- [ ] pipeline順序を固定: parse -> canonicalize -> validate -> write

---

## 5) P2: minimal executor（副作用最小・決定論）
- [/] 新規: `scripts/il_exec.py` を追加
  - Input:
    - `--il` canonical json
    - `--guard` guard json
  - Behavior:
    - IF guard.can_execute != true:
        - print("SKIP: guard blocks execution")
        - write minimal exec report
        - return 0
    - ELSE:
        - opcode を順に処理（最小集合）
        - 副作用は out_dir への書き込みのみ
        - print("OK/ERROR/SKIP: ...") を残す
- [ ] opcode を schema に反映（最小で）
  - NOOP / SET_VARS / SEARCH_TERMS / RETRIEVE / ANSWER_DRAFT（など）
  - RETRIEVE は最小実装なら SKIP で良い（未接続を明示）

---

## 6) CI / Always-run 連携（“exitで落とさない哲学”）
- [x] 既存CIに軽量ステップを追加（存在するワークフローに合わせる）
  - Run:
    - `python3 scripts/il_guard.py --fixtures tests/fixtures/il --out .local/out/il_guard`
    - `python3 scripts/il_exec.py  --il ... --guard ... --out ...`（可能なら）
  - Rule:
    - CIの合否は終了コードではなく成果物（log/json）で観測可能にする
- [x] 成果物パスを docs に明記（監査ログとして）

---

## 7) PR 仕上げ（1PRで完了）
- [/] docs更新（S21-05 PLAN/TASK を最新化、DoDチェック）
- [x] 進捗を更新（STATUSボードがあれば行を更新、無ければ SKIP）
- [x] ローカルで軽量確認（重いのは分散）
  - `python3 scripts/il_guard.py --fixtures ...`
  - `python3 scripts/il_exec.py ...`（guard true/false 両方）
- [ ] PR作成（milestone S21-05 を必ず付与）

---

## Fixpack v2: Dependency & CI & Observability
- [ ] **1) jsonschema 固定**
  - Check `pyproject.toml` for `jsonschema`.
  - If missing, add `"jsonschema>=4.0.0"` to `dependencies`.
  - Run `make bootstrap`.
  - Verify `.venv/bin/python` exists.
- [ ] **2) CI Integration**
  - Add `run: make verify-il` to `.github/workflows/test.yml` (after `make test`).
- [ ] **3) Observability**
  - Update `scripts/il_check.py` to print stdout/stderr on error.
- [ ] **4) Verification**
  - Run `make verify-il` and check logs for `ERROR:`.
- [ ] **5) Evidence**
  - Run `reviewpack submit --mode verify-only`.
  - Update PR body with new bundle/SHA.

---

## Closeout (after merge)
- [ ] 後始末コマンドを実行（落ちない版）
  - see: docs/ops/S21-05_PLAN.md "Aftercare"
