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

---

## 0) Preflight: branch & main divergence吸収（落ちない）

- [ ] `git fetch origin --prune 2>/dev/null || true`
- [ ] `git status -sb 2>/dev/null || true`
- [ ] divergence観測（証拠ログ用）
  - [ ] `git log --oneline --left-right --cherry main...origin/main 2>/dev/null || true`
- [ ] 作業ブランチで origin/main を取り込む（コンフリクトは"観測→解決"）
  - [ ] `git switch s22-03-eval-wall-il-v1 2>/dev/null || true`
  - [ ] `git merge --no-ff origin/main 2>/dev/null || true`
  - [ ] `git status -sb 2>/dev/null || true`
  - [ ] もしconflictなら：対象ファイルを列挙してログに残す（解決は次のチェックで）
    - [ ] `git diff --name-only --diff-filter=U 2>/dev/null || true`
    - [ ] `SKIP: resolve conflicts first (list above)` を1行残し STOP=1（以降ステップへ進まない）

## 1) S22-03 PLAN/TASK を確定（このファイル群）

編集対象（実パス固定）：

- docs/ops/S22-03_PLAN.md
- docs/ops/S22-03_TASK.md

- [ ] `git add docs/ops/S22-03_PLAN.md docs/ops/S22-03_TASK.md 2>/dev/null || true`
- [ ] `git commit -m "docs(ops): specify S22-03 IL-centered eval wall DoD/metrics/dataset" 2>/dev/null || true`

## 2) 既存schema/fixture入口を"読む"（推測禁止）

目的：**勝手にschemaを作らず**、既存のIL資産（schema/examples/fixtures）を最大再利用する。

- [ ] IL schema の存在確認（入口）
  - [ ] `ls -la docs/il/il.schema.json 2>/dev/null || true`
- [ ] IL examples/fixtures を観測（再利用候補を列挙）
  - [ ] `ls -la docs/il/examples 2>/dev/null || true`
  - [ ] `ls -la tests/fixtures/il 2>/dev/null || true`
- [ ] 既存eval dataset（参考観測。互換に寄せる場合の材料）
  - [ ] `ls -la data/eval/datasets/rag-eval-wall-v1__seed-mini__v0001 2>/dev/null || true`
  - [ ] `python3 - <<'PY'\nfrom pathlib import Path\nimport json\np=Path('data/eval/datasets/rag-eval-wall-v1__seed-mini__v0001/cases.jsonl')\nprint('OK: exists=', p.exists())\nif p.exists():\n  line=p.read_text(encoding='utf-8').splitlines()[0]\n  obj=json.loads(line)\n  print('OK: first_keys=', sorted(obj.keys()))\nPY`
  - [ ] `python3 - <<'PY'\nfrom pathlib import Path\nimport json\np=Path('data/eval/datasets/rag-eval-wall-v1__seed-mini__v0001/dataset.meta.json')\nprint('OK: exists=', p.exists())\nif p.exists():\n  obj=json.loads(p.read_text(encoding='utf-8'))\n  print('OK: meta_keys=', sorted(obj.keys()))\nPY`

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

- [ ] ディレクトリ作成（落ちない）
  - [ ] `mkdir -p data/eval/datasets/il-eval-wall-v1__seed-mini__v0001 2>/dev/null || true`
- [ ] dataset.meta.json を作る（既存meta形式に合わせる）
  - [ ] 既存metaの必須キーを踏襲し、dataset_idだけ差し替える
- [ ] cases.jsonl を作る（"分類が勝ち"）
  - [ ] 10〜15件に抑える
  - [ ] NGケースは intent を1行で明文化
  - [ ] forbidden/timestamp/network/random/external など未決定要素痕跡を狙うケースを入れる
  - [ ] schema逸脱ケースを入れる（必須欠落/型不正など）
  - [ ] injection（誘導/注入）ケースを入れる（IL内に注入痕跡を混ぜる等）
- [ ] cases.jsonl の"決定論チェック"（順序/ID固定）
  - [ ] `python3 - <<'PY'\nfrom pathlib import Path\np=Path('data/eval/datasets/il-eval-wall-v1__seed-mini__v0001/cases.jsonl')\nprint('OK: exists=', p.exists())\nif p.exists():\n  lines=p.read_text(encoding='utf-8').splitlines()\n  print('OK: lines=', len(lines))\n  # 先頭3行だけ観測（監査ログ用）\n  for i,ln in enumerate(lines[:3]):\n    print('OK: head', i, ln[:120])\nPY`

## 4) Runner追加（IL中心 eval 実行）

編集対象（実パス固定）：

- eval/run_il_eval.py

依存参照（既存を再利用）：

- scripts/il_check.py（呼び出し方のSOT）
- scripts/il_exec.py（実行器）
- src/il_validator.py（検証器がここなら、runnerはそれを呼ぶだけ）
- docs/il/il.schema.json（schema駆動が可能なら使う）

要件：

- [ ] 同一dataset_id + 同一seed で再現
- [ ] strong/weak 2モード（weakは評価用の"意図的劣化"）
- [ ] 出力は stable filename（timestamp禁止）
- [ ] Python例外は必ず握って `ERROR:` を吐く（sys.exit禁止）
- [ ] caseごとに `OK/ERROR/SKIP` と `observed_fail_class` を記録
- [ ] （推測禁止の回避策）schema駆動で mutation を適用する場合：
  - 文字列注入先は「schema上の最初のstringフィールド（辞書順）」など **固定規則**
  - required削除も「schema required の辞書順先頭」など **固定規則**
  - 禁則フィールド追加も **固定規則**（一覧はIL規約側で固定）

## 5) Metrics追加（自動集計）

編集対象（実パス固定）：

- eval/il_metrics.py

要件：

- [ ] 指標をJSONで出力（stable filename）
- [ ] 必須metrics（schema違反率/禁止率/未決定率/status分布/result生成率）
- [ ] 追加metrics（failclass一致率、FP/FN）
- [ ] スコア単一値（比較用、式は固定）
- [ ] 例外を握り、最後に `OK:` or `ERROR:` を1行（終了コードに依存しない）

## 6) Causal check（差分の証拠）

編集対象（実パス固定）：

- eval/il_metrics.py（compare機能を入れる）または eval/il_causal.py（新規でもOK）
- eval/results/il_causal__{dataset_id}__seed0000.json（出力）

要件：

- [ ] strong と weak の metrics を同seedで作る（seed=0固定推奨）
- [ ] "strongの方が良い方向" を差分JSONに保存
- [ ] 判定は `OK:` / `ERROR:` を1行で出す（exitで止めない）
- [ ] 差分JSONには最低限以下を入れる（監査用）
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

- [ ] `make run-il-eval`（strong生成）
- [ ] `make il-metrics`（strong集計）
- [ ] `make verify-il-causal`（strong+weak+差分）
- [ ] `make verify-il` に軽く組み込む（重くしない）

注意（重要）：

- [ ] makeターゲット内は「失敗で止まる」罠があるため、原則は
  - **Pythonランナーが常に0で終わる**（判定は `OK:`/`ERROR:` の出力で行う）
- [ ] 既存ターゲットの意味を変えない（壊さない）

## 8) テスト（軽量・決定論）

編集対象（実パス固定）：

- tests/test_il_metrics_smoke.py
- tests/test_il_dataset_shape.py

方針：

- [ ] 実行器を呼ばない（重くしない）
- [ ] 集計ロジックの決定論（入力→出力が安定）だけ担保
- [ ] dataset shape は必須キーだけ検査（過剰に厳しくしない）

## 9) Evidence / Gates（最終確認）

- [ ] `python3 -m pytest -q 2>/dev/null || true`
- [ ] `make verify-il 2>/dev/null || true`
- [ ] `go test ./... 2>/dev/null || true`
- [ ] `go run cmd/reviewpack/main.go submit --mode verify-only 2>/dev/null || true`
- [ ] review bundle に以下が入っていることを確認（grepでOK）
  - eval/results/il_eval__il-eval-wall-v1__seed-mini__v0001__seed0000__strong.jsonl
  - eval/results/il_metrics__il-eval-wall-v1__seed-mini__v0001__seed0000__strong.json
  - eval/results/il_eval__il-eval-wall-v1__seed-mini__v0001__seed0000__weak.jsonl
  - eval/results/il_metrics__il-eval-wall-v1__seed-mini__v0001__seed0000__weak.json
  - eval/results/il_causal__il-eval-wall-v1__seed-mini__v0001__seed0000.json

## 10) STATUS更新（最小編集）

編集対象（実パス固定）：

- docs/ops/STATUS.md

- [ ] docs/ops/STATUS.md に S22-03 行が存在するか確認
  - [ ] `rg -n "^\| S22-03 " docs/ops/STATUS.md 2>/dev/null || true`
- [ ] もし S22-03 行が無い場合：S22-01 の直後に **最小追記**で挿入（順序維持）
  - [ ] `python3 - <<'PY'\nfrom pathlib import Path\np=Path('docs/ops/STATUS.md')\ntry:\n  txt=p.read_text(encoding='utf-8')\nexcept Exception as e:\n  print('ERROR: read failed:', e)\n  txt=''\nif not txt:\n  print('ERROR: empty STATUS.md')\nelif '| S22-03 ' in txt:\n  print('SKIP: S22-03 row already exists')\nelse:\n  lines=txt.splitlines(True)\n  out=[]\n  inserted=False\n  for ln in lines:\n    out.append(ln)\n    if (not inserted) and ln.startswith('| S22-01 '):\n      out.append('| S22-03 | ACTIVE | docs/ops/S22-03_PLAN.md | 1% (Kickoff) |\n')\n      inserted=True\n  if not inserted:\n    print('ERROR: cannot find S22-01 row to insert after')\n  else:\n    try:\n      p.write_text(''.join(out), encoding='utf-8')\n      print('OK: inserted S22-03 row')\n    except Exception as e:\n      print('ERROR: write failed:', e)\nPY`
- [ ] S22-03 を更新（%と短いCurrentのみ）
  - 目安：dataset+metrics仕様確定で 10〜20%
  - 例：`10% (dataset+metrics specified)` / `20% (dataset committed)` など
