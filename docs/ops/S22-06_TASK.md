# S22-06 TASK (P7) OBS Format v1
進捗率（推定）: 13%

## ルール（絶対）
- exit系全面禁止（shell/Python）
- 失敗は `ERROR:` 行 + `STOP=1`
- STOP=1 以降は `SKIP:`（理由1行）
- heavy処理は分割（常用は smoke/light のみ）

---

## 0) ブランチ
- [ ] `git switch main`（落ちない）
- [ ] `git pull --ff-only`（落ちない）
- [ ] `git switch -c s22-06-obs-format-v1`（無理なら既存へswitch）

## 1) 雛形ファイル作成（今回のスクリプトで作成済みならSKIP）
- [ ] `docs/ops/OBS_FORMAT_v1.md` を確認（規格が最小であること）
- [ ] `docs/ops/S22-06_PLAN.md` を確認（止まらない型になっていること）
- [ ] `docs/ops/S22-06_TASK.md` を確認（順序固定になっていること）

## 2) obs_writer 実装（軽い）
- [ ] `scripts/obs_writer.py` を作る
  - [ ] `OK/ERROR/SKIP` 行ログ出力
  - [ ] `KEY=VALUE` 出力（スペース区切り）
  - [ ] `obs_dir` UTC命名（`.local/obs/<name>_<YYYYMMDDTHHMMSSZ>`）
  - [ ] ファイル書き込み失敗は ERROR 行で表現（例外で止めない）

## 3) il_entry 接続（最小）
- [ ] `scripts/il_entry.py` に OBS v1 を接続
  - [ ] 起動時に `OK: obs_format=v1 obs_dir=...`
  - [ ] phase開始/終了を行ログで出す（最小: boot/validate/execute/end）
  - [ ] 失敗は `ERROR:` + `STOP=1`
  - [ ] STOP=1 後は `SKIP:`（理由1行）
  - [ ] 詳細は `${obs_dir}/result.json` 等へ

## 4) テスト（軽量）
- [ ] `tests/test_obs_format.py` を追加（文字列中心）
  - [ ] 行頭が OK/ERROR/SKIP のみ
  - [ ] KEY=VALUE の最低限パース
  - [ ] UTC命名の形式チェック
  - [ ] STOP=1 → SKIP の規約チェック

## 5) 検証（heavy禁止 / まずsmoke）
- [ ] `python3 -m compileall scripts 2>/dev/null || true`（落ちない）
- [ ] 既存テスト実行（pytest/unittest を repoに合わせて）
- [ ] ログが規格どおりか目視（数行）

## 6) SOT更新（最小）
- [ ] `docs/ops/STATUS.md` に S22-06 を 1% (WIP) で反映（行単位で最小差分）
- [ ] `docs/ops/ROADMAP.md` に P7 を追記（必要なら）

## 7) コミット（軽→重）
- [ ] Commit 1: docs（OBS_FORMAT + PLAN/TASK）
- [ ] Commit 2: obs_writer.py
- [ ] Commit 3: il_entry接続
- [ ] Commit 4: tests

## 8) PR
- [ ] PR作成（milestone=S22-06）
- [ ] CI green 確認
- [ ] merge は guard 経由（あなたの関所）
