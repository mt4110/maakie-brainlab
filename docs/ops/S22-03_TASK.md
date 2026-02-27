# S22-03 TASK — P3 IL-centered Eval Wall (IL metrics + dataset)

## Safety rules (non-negotiable)

- **exit系の全面禁止（シェル/Python）**
  - Shell: `exit` / `return 1` / `set -e` / `set -euo pipefail` / `trap ... EXIT` 禁止
  - Python: `sys.exit(...)` / `raise SystemExit` / `assert` 禁止（失敗で終了扱いになり得るため）
- **停止条件は「終了コード」ではなく「STOPフラグ」で制御**
  - ルール：`ERROR:` を出したら `STOP=1`
  - `STOP=1` のとき以降のステップは **必ず** `SKIP: step=<name> reason=<prior error>` を1行出して **continue**
  - 逆に、成功時は `OK:` を1行出して次へ進む
- **"error はその場で終了（嘘をつかない）" の定義**
  - ここでの「終了」は **プロセス終了ではない**
  - 意味：そのステップを **中断**し、以降のステップへ **進まない判断（STOP=1）** を確定する
- **Pythonスクリプトの最上段で必ず try/catch**
  - 未捕捉例外で止まるのはNG（sys.exit禁止でも例外は止まる）
  - すべてのrunner/metrics/causalは：
    - `try:` 本体
    - `except Exception as e:` で `print("ERROR: ...")`（例外は上に投げない）
    - 最後に `print("OK: ...")` か `print("ERROR: ...")` を必ず1行出す
  - 返り値（終了コード）は常に0でよい（判定は出力テキストで行う）
- **重い処理は分割（CPU/ターミナル保護）**
  - seed-mini固定（10〜15ケース）を厳守
  - runner strong / weak / metrics / causal / verify を **1ステップ1本**に分ける
  - "固まりそう"なら中断してよい：ただし `SKIP:` に **中断理由と直前の観測結果**を1行残す
- **Makefileの罠（重要）**
  - `make` は通常、途中コマンドが失敗すると **そのターゲット内で後続行が実行されない**
  - 対策方針：
    - 原則：Makefileは薄くして **「常に0で終わるPythonランナー」** を呼ぶ
    - どうしても必要な場面は `|| true` を付与しつつ、`ERROR:` / `OK:` のログをPython側で出す

### Safety rules addendum (Exitless Deterministic Ops)

**[MUST] 終了コードで制御しない**

- シェル：`exit` / `return非0` / `set -e` / `set -euo pipefail` / `trap ... EXIT` を使わない
- Python：`sys.exit` / `raise SystemExit` / `assert` を使わない（失敗時に強制終了し得るため）
- "失敗" は常に標準出力で表現する：`OK:` / `ERROR:` / `SKIP:`

**[MUST] STOPプロトコル（止まらない、でも次に進まない）**

- 各ステップは「次へ進んでよいか」をフラグで制御する（例：`STOP=1`）
- 失敗したら：
  - `ERROR: <reason>` を1行出す
  - `STOP=1` にして以降のステップを実行しない（ただしプロセス自体は落とさない）
- スキップしたら：
  - `SKIP: <reason>` を1行出す（未来の監査ログ）

**[MUST] Python は例外を封じ込める**

- すべてのメイン処理を `try/except Exception as e:` で包む
- 例外発生時は `ERROR: ... err=<e>` を1行出して終了（例外を外へ漏らさない）
- "検査スクリプト" はエラーでも 0 で終わる設計（出力テキストで判定）

**[MUST] 1 target = 1 responsibility（重い処理は分割）**

- strong生成 / strong集計 / weak生成 / weak集計 / 差分生成 は必ず別ステップ
- 重くなりそうなら「途中で中断して `SKIP:` / `ERROR:` で理由を残す」

**[MUST] Makefile は罠を作らない**

- 失敗で make が止まらないように、判定は出力行（`OK:` / `ERROR:` / `SKIP:`）で行う
- パイプやリダイレクトでログが消えないように、最小限のログを必ず残す
- "verify系" は重くしない（強い実行器を呼ばないテストを優先）

**[MUST] 監査ログの書式（1行で読める真実）**

- 形式：`<LEVEL>: <what> key=value ...`
  - `OK:    OK: il_metrics wrote path=... count=...`
  - `ERROR: ERROR: il_metrics failed reason=...`
  - `SKIP:  SKIP: verify-il-thread-v2 reason=STOP=1`

---

## 0) Preflight: branch & main divergence吸収（落ちない）

- [x] `git fetch origin --prune 2>/dev/null || true`
- [x] `git status -sb 2>/dev/null || true`
- [x] divergence観測（証拠ログ用）
  - [x] `git log --oneline --left-right --cherry main...origin/main 2>/dev/null || true`
- [x] 作業ブランチで origin/main を取り込む（コンフリクトは"観測→解決"）
  - [x] `git switch s22-03-eval-wall-il-v1 2>/dev/null || true`
  - [x] `git merge --no-ff origin/main 2>/dev/null || true`
  - [x] `git status -sb 2>/dev/null || true`
  - [x] もしconflictなら：対象ファイルを列挙してログに残す（解決は次のチェックで）
    - [x] `git diff --name-only --diff-filter=U 2>/dev/null || true`
    - [x] `SKIP: resolve conflicts first (list above)` を1行残し STOP=1（以降ステップへ進まない）

## 1) S22-03 PLAN/TASK を確定（このファイル群）

編集対象（実パス固定）：

- docs/ops/S22-03_PLAN.md
- docs/ops/S22-03_TASK.md

- [x] `git add docs/ops/S22-03_PLAN.md docs/ops/S22-03_TASK.md 2>/dev/null || true`
- [x] `git commit -m "docs(ops): specify S22-03 IL-centered eval wall DoD/metrics/dataset" 2>/dev/null || true`

## 2) 既存schema/fixture入口を"読む"（推測禁止）

目的：**勝手にschemaを作らず**、既存のIL資産（schema/examples/fixtures）を最大再利用する。

- [x] IL schema の存在確認（入口）
  - [x] `ls -la docs/il/il.schema.json 2>/dev/null || true`
- [x] IL examples/fixtures を観測（再利用候補を列挙）
  - [x] `ls -la docs/il/examples 2>/dev/null || true`
  - [x] `ls -la tests/fixtures/il 2>/dev/null || true`
- [x] 既存eval dataset（参考観測。互換に寄せる場合の材料）
  - [x] `ls -la data/eval/datasets/rag-eval-wall-v1__seed-mini__v0001 2>/dev/null || true`
  - [x] `python3 - <<'PY'\nfrom pathlib import Path\nimport json\np=Path('data/eval/datasets/rag-eval-wall-v1__seed-mini__v0001/cases.jsonl')\nprint('OK: exists=', p.exists())\nif p.exists():\n  line=p.read_text(encoding='utf-8').splitlines()[0]\n  obj=json.loads(line)\n  print('OK: first_keys=', sorted(obj.keys()))\nPY`
  - [x] `python3 - <<'PY'\nfrom pathlib import Path\nimport json\np=Path('data/eval/datasets/rag-eval-wall-v1__seed-mini__v0001/dataset.meta.json')\nprint('OK: exists=', p.exists())\nif p.exists():\n  obj=json.loads(p.read_text(encoding='utf-8'))\n  print('OK: meta_keys=', sorted(obj.keys()))\nPY`

## 3) 新dataset作成（IL-centered seed-mini）

編集対象（実パス固定）：

- data/eval/datasets/il-eval-wall-v1__seed-mini__v0001/dataset.meta.json
- data/eval/datasets/il-eval-wall-v1__seed-mini__v0001/cases.jsonl

（必要なら）

- tests/fixtures/il/...（再利用優先。追加は最小）

方針（重要）：

- seed-miniは **10〜15件**（分類が勝ち）
- caseは **狙いが明確**：禁則/注入/スキーマ逸脱/未決定要素/negative_control/executor
- negative_control を必ず含める（誘導・注入が来ても壊れない＝false_positive率の基盤）
- timestamp/network/random/external 等の未決定要素痕跡を **狙って**入れる

作業：

- [x] ディレクトリ作成（落ちない）
  - [x] `mkdir -p data/eval/datasets/il-eval-wall-v1__seed-mini__v0001 2>/dev/null || true`
- [x] dataset.meta.json を作る（既存meta形式に合わせる）
  - [x] 既存metaの必須キーを踏襲し、dataset_idだけ差し替える
- [x] cases.jsonl を作る（"分類が勝ち"）
  - [x] 10〜15件に抑える
  - [x] NGケースは intent を1行で明文化
  - [x] forbidden/timestamp/network/random/external など未決定要素痕跡を狙うケースを入れる
  - [x] schema逸脱ケースを入れる（必須欠落/型不正など）
  - [x] injection（誘導/注入）ケースを入れる（IL内に注入痕跡を混ぜる等）
- [x] cases.jsonl の"決定論チェック"（順序/ID固定）
  - [x] `python3 - <<'PY'\nfrom pathlib import Path\np=Path('data/eval/datasets/il-eval-wall-v1__seed-mini__v0001/cases.jsonl')\nprint('OK: exists=', p.exists())\nif p.exists():\n  lines=p.read_text(encoding='utf-8').splitlines()\n  print('OK: lines=', len(lines))\n  # 先頭3行だけ観測（監査ログ用）\n  for i,ln in enumerate(lines[:3]):\n    print('OK: head', i, ln[:120])\nPY`

## 4) Runner追加（IL中心 eval 実行）

編集対象（実パス固定）：

- eval/run_il_eval.py

依存参照（既存を再利用）：

- scripts/il_check.py（呼び出し方のSOT）
- scripts/il_exec.py（実行器）
- src/il_validator.py（検証器がここなら、runnerはそれを呼ぶだけ）
- docs/il/il.schema.json（schema駆動が可能なら使う）

要件：

- [x] 同一dataset_id + 同一seed で再現
- [x] strong/weak 2モード（weakは評価用の"意図的劣化"）
- [x] 出力は stable filename（timestamp禁止）
- [x] Python例外は必ず握って `ERROR:` を吐く（sys.exit禁止）
- [x] caseごとに `OK/ERROR/SKIP` と `observed_fail_class` を記録
- [x] **fail_class 判定の優先順位（precedence）を固定**
  - 1つのILに複数の違反が共存し得る（例：`created_at` + `injection_trace`）
  - 判定順は **最も具体的なクラスが勝つ**（以下の優先順で最初にマッチしたものを採用）：
    1. `forbidden_injection` — キー名が `injection_trace` / `injection_trace_v2` 等（prefix: `injection_trace`）
    2. `forbidden_network` — キー名が `network_trace` / `network_trace_v2` 等（prefix: `network_trace`）
    3. `forbidden_random` — キー名が `random_trace` / `random_trace_v2` 等（prefix: `random_trace`）
    4. `forbidden_field` — 上記以外の禁則フィールド（`created_at` / `timestamp` 等）
    5. `schema_violation` — JSON schema 違反（必須欠落/型不正等）
    6. `executor_error` — JSON parse失敗等、検証以前のエラー
    7. `none` — 違反なし（OK）
  - キー一致は **prefix match**（`injection_trace` で `injection_trace_v2` も拾う）
  - この優先順位は **仕様として固定**（実装が独自に順序を変えてはならない）
- [x] （推測禁止の回避策）schema駆動で mutation を適用する場合：
  - 文字列注入先は「schema上の最初のstringフィールド（辞書順）」など **固定規則**
  - required削除も「schema required の辞書順先頭」など **固定規則**
  - 禁則フィールド追加も **固定規則**（一覧はIL規約側で固定）

## 5) Metrics追加（自動集計）

編集対象（実パス固定）：

- eval/il_metrics.py

要件：

- [x] 指標をJSONで出力（stable filename）
- [x] 必須metrics（schema違反率/禁止率/未決定率/status分布/result生成率）
- [x] 追加metrics（failclass一致率、FP/FN）
- [x] スコア単一値（比較用、式は固定）
- [x] 例外を握り、最後に `OK:` or `ERROR:` を1行（終了コードに依存しない）
- [x] **permitted fail_class enum（許容値を固定）**
  - `none` / `schema_violation` / `executor_error` / `forbidden_field` / `forbidden_injection` / `forbidden_network` / `forbidden_random`
  - ↑ 以外の値が `observed_fail_class` に現れたら `ERROR:` を出す（サイレントな分類漏れ防止）

## 6) Causal check（差分の証拠）

編集対象（実パス固定）：

- eval/il_metrics.py（compare機能を入れる）または eval/il_causal.py（新規でもOK）
- eval/results/il_causal__{dataset_id}__seed0000.json（出力）

要件：

- [x] strong と weak の metrics を同seedで作る（seed=0固定推奨）
- [x] "strongの方が良い方向" を差分JSONに保存
- [x] 判定は `OK:` / `ERROR:` を1行で出す（exitで止めない）
- [x] 差分JSONには最低限以下を入れる（監査用）
  - dataset_id / seed
  - score_strong / score_weak / delta
  - schema_violation_rate_strong/weak
  - forbidden_field_rate_strong/weak
  - nondeterminism_rate_strong/weak
  - result_generated_rate_strong/weak
  - summary_line（最終のOK/ERRORをそのまま格納してもよい）

## 7) Makefileに組み込み（既存を壊さない）

編集対象（実パス固定）：

- Makefile

追加ターゲット（例）：

- [x] `make il-thread-smoke`（thread runner 実行）
- [x] `make verify-il-thread-v2`（suite/doctor/replay 集計）
- [x] `make verify-il`（統合検証）
- [x] `make verify-il` に軽く組み込む（重くしない）

注意（重要）：

- [x] makeターゲット内は「失敗で止まる」罠があるため、原則は
  - **Pythonランナーが常に0で終わる**（判定は `OK:`/`ERROR:` の出力で行う）
- [x] 既存ターゲットの意味を変えない（壊さない）

## 8) テスト（軽量・決定論）

編集対象（実パス固定）：

- tests/test_il_metrics_smoke.py
- tests/test_il_dataset_shape.py

方針：

- [x] 実行器を呼ばない（重くしない）
- [x] 集計ロジックの決定論（入力→出力が安定）だけ担保
- [x] dataset shape は必須キーだけ検査（過剰に厳しくしない）

## 9) Evidence / Gates（最終確認）

- [x] `python3 -m pytest -q 2>/dev/null || true`
- [x] `make verify-il 2>/dev/null || true`
- [x] `go test ./... 2>/dev/null || true`
- [x] `go run cmd/reviewpack/main.go submit --mode verify-only 2>/dev/null || true`
- [x] review bundle に以下が入っていることを確認（grepでOK）
  - eval/results/il_eval__il-eval-wall-v1__seed-mini__v0001__seed0000__strong.jsonl
  - eval/results/il_metrics__il-eval-wall-v1__seed-mini__v0001__seed0000__strong.json
  - eval/results/il_eval__il-eval-wall-v1__seed-mini__v0001__seed0000__weak.jsonl
  - eval/results/il_metrics__il-eval-wall-v1__seed-mini__v0001__seed0000__weak.json
  - eval/results/il_causal__il-eval-wall-v1__seed-mini__v0001__seed0000.json

## 10) STATUS更新（最小編集）

編集対象（実パス固定）：

- docs/ops/STATUS.md

- [x] docs/ops/STATUS.md に S22-03 行が存在するか確認
  - [x] `rg -n "^\| S22-03 " docs/ops/STATUS.md 2>/dev/null || true`
- [x] もし S22-03 行が無い場合：S22-01 の直後に **最小追記**で挿入（順序維持）
  - [x] `python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/ops/STATUS.md')\ntry:\n  txt=p.read_text(encoding='utf-8')\nexcept Exception as e:\n  print('ERROR: read failed:', e)\n  txt=''\nif not txt:\n  print('ERROR: empty STATUS.md')\nelif '| S22-03 ' in txt:\n  print('SKIP: S22-03 row already exists')\nelse:\n  lines=txt.splitlines(True)\n  out=[]\n  inserted=False\n  for ln in lines:\n    out.append(ln)\n    if (not inserted) and ln.startswith('| S22-01 '):\n      out.append('| S22-03 | ACTIVE | docs/ops/S22-03_PLAN.md | 1% (Kickoff) |\n')\n      inserted=True\n  if not inserted:\n    print('ERROR: cannot find S22-01 row to insert after')\n  else:\n    try:\n      p.write_text(''.join(out), encoding='utf-8')\n      print('OK: inserted S22-03 row')\n    except Exception as e:\n      print('ERROR: write failed:', e)\nPY`
- [x] S22-03 を更新（%と短いCurrentのみ）
  - 目安：dataset+metrics仕様確定で 10〜20%
  - 例：`10% (dataset+metrics specified)` / `20% (dataset committed)` など
