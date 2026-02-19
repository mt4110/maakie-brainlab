# S21-06_TASK (v1)

## 0) Repo確認（落ちない）

- [ ] ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; if [ -z "$ROOT" ]; then echo "ERROR: not in git repo"; else echo "OK: repo=$ROOT"; fi
- [ ] cd "$ROOT" 2>/dev/null; pwd; git status -sb

## 1) main最新化（落ちない）

- [ ] git switch main 2>/dev/null; git pull --ff-only 2>/dev/null; echo "OK: updated main (check output manually)"

## 2) ブランチ作成（落ちない）

- [ ] BR="s21-06-il-scripts-hardening-v1"
- [ ] git switch -c "$BR" 2>/dev/null || git switch "$BR" 2>/dev/null; git status -sb

## 3) Plan/Task作成 + STATUS更新（最小編集）

- [ ] docs/ops/S21-06_PLAN.md を作成（metaテンプレがあればコピー、なければ新規）
- [ ] docs/ops/S21-06_TASK.md を作成
- [ ] docs/ops/STATUS.md の S21-06 行を追加（まだ無ければ）し、進捗=1% と Last Updated を更新（他行は触らない）
  - [ ] 確認: rg -n "^\| S21-06 " docs/ops/STATUS.md

## 4) A1: good fixture から timestamp 削除

- [ ] 編集: tests/fixtures/il/good/minimal.json から meta.timestamp を削除
- [ ] 確認: rg -n "timestamp" tests/fixtures/il/good/minimal.json; echo "OK: timestamp removed (expect no hits)"

## 5) A3: SystemExitゼロ化（argparse撤去 or 安全パーサ）

- [ ] scripts/il_guard.py: argparse.parse_args を使わない実装へ（手書き parse(argv) 推奨）
- [ ] scripts/il_exec.py: 同様
- [ ] scripts/il_check.py: 同様（必要なら最小で）

## 6) A2+B1: il_guard 常時レポート + NaN禁止 + 契約整合

- [ ] scripts/il_guard.py:
  - [ ] src/il_validator.py の ILValidator / ILCanonicalizer を importして使う
  - [ ] 入力を validate（errorsを収集）
  - [ ] forbidden検出は errors に残す（黙って通さない）
  - [ ] canonical出力は sanitized(=forbidden除去)に対して ILCanonicalizer.canonicalize を使って bytes を書く
  - [ ] 例外時でも il.guard.json は必ず書く（out_dir不明なら "." にフォールバック）
  - [ ] printは OK/ERROR/SKIP で始める

## 7) B2+B3: il_exec ログprefix + status集約 + 常時レポート

- [ ] scripts/il_exec.py:
  - [ ] guard.can_execute=false の場合、実行せず SKIP、il.exec.json を書く
  - [ ] opcode毎ログは OK:/ERROR:/SKIP: で開始
  - [ ] overall status を opcode結果から集約（ERROR優先）
  - [ ] 例外時も必ず il.exec.json を書く

## 8) A4+B4: il_check shell=True撤去 + 例外でも落ちない

- [ ] scripts/il_check.py:
  - [ ] subprocess.run は argv配列、shell=False
  - [ ] 戻りコードで分岐しない（生成された il.guard.json / il.exec.json を読んで結論を出す）
  - [ ] try/except(Exception) で予期せぬ例外も ERROR: を出し、処理継続（可能なら check report も書く）

## 9) 軽量ローカル検証（重い処理は分割）

- [ ] (軽) python: $(PYENV) $(PY) -c "print('OK: python alive')" など
- [ ] (軽) verify-il: $(PYENV) $(PY) scripts/il_check.py （ログを確認）
- [ ] (中) go test ./... を実行しログ保存（nice推奨、ただし落ちない）
- [ ] (重) go run cmd/reviewpack/main.go submit --mode verify-only（最後に1回）

## 10) コミット（粒度は2〜4コミットに分割）

- [ ] commit1: docs/ops(S21-06 plan/task/status)
- [ ] commit2: fixture timestamp removal
- [ ] commit3: il_guard hardening
- [ ] commit4: il_exec + il_check hardening

## 11) PR作成（SOT/証拠スタイル）

- [ ] gh pr create（本文はSOT/Evidence/Gates。証拠bundle名とsha256は埋める）
- [ ] PRのMilestoneを S21-06 に設定（必須）
