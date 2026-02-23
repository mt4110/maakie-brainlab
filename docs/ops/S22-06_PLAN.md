# S22-06 PLAN (P7) OBS Format v1
進捗率（推定）: 13%

## Goal
入口スクリプト（最低: scripts/il_entry.py）が **同一規格(OBS v1)** で観測ログを吐く。
stdout=行ログ / 詳細=obs_dirファイル / UTC命名 / STOP制御 / exit系禁止。

## Non-Goal（今回やらない）
- 全スクリプトへの一斉適用（最小: il_entry に通す。余裕があれば rag_pipeline も）
- heavy系の常時実行（smokeのみ常用、heavyは任意）

## Deliverables
- docs/ops/OBS_FORMAT_v1.md
- scripts/obs_writer.py
- scripts/il_entry.py に OBS v1 を接続（最小）
- tests/test_obs_format.py（軽量）
- docs/ops/S22-06_TASK.md

## 設計原則（壊れない）
- exit/return非0/sys.exit/SystemExit/assert 禁止
- 失敗は ERROR 行 + STOP=1
- STOP=1 の後は SKIP 行（理由1行）
- stdout は機械向け最小、詳細は obs_dir ファイル
- obs_dir は UTC 命名のみ
- heavy と smoke を分離（常用=軽い）

---

## Pseudocode（止まらない型）
### 0) 前提確認
if not in git repo:
  print("ERROR: not in repo")
  STOP=1

if STOP==1:
  print("SKIP: phase=boot STOP=1 reason=\"not in repo\"")
  goto END

### 1) 対象パス確定（実パスを先に固める）
candidates = [
  "scripts/il_entry.py",
  "scripts/rag_pipeline.py",
  "scripts/il_exec_run.py",
]
for p in candidates:
  if exists(p):
    print("OK: phase=discover path=" + p)
    continue
  else:
    print("SKIP: phase=discover path=" + p + " reason=\"missing\"")
    continue

required = ["scripts/il_entry.py"]
for p in required:
  if not exists(p):
    print("ERROR: phase=discover reason=\"missing required\" path=" + p + " STOP=1")

### 2) OBS v1 規格の実装（共通ユーティリティ）
try:
  create scripts/obs_writer.py
  - obs_dir = ".local/obs/<name>_<UTC>"
  - print_line(level, **kv)  # OK/ERROR/SKIP + KEY=VALUE
  - write_file(path, content)  # 例外は握り、ERROR行にする
catch Exception as e:
  print("ERROR: phase=obs_writer reason=\"unexpected\" STOP=1")

### 3) il_entry へ接続（最小改修）
if STOP==1:
  print("SKIP: phase=il_entry STOP=1 reason=\"prior ERROR\"")
else:
  try:
    il_entry 起動時に:
      - obs_dir を作る（UTC）
      - print("OK: obs_format=v1 obs_dir=... phase=boot")
      - 主要phaseの開始/終了を行ログで出す（validate/execute/postなど）
      - 失敗時は ERROR 行 + STOP=1
      - STOP=1 なら後続は SKIP 行
      - 詳細は obs_dir に result.json 等で書く
  catch Exception as e:
    print("ERROR: phase=il_entry reason=\"unexpected\" STOP=1")

### 4) テスト（軽量・文字列中心）
if exists("tests"):
  create tests/test_obs_format.py
  - 行ログのパース（先頭OK/ERROR/SKIP、KEY=VALUE）
  - UTC命名の形式チェック（YYYYMMDDTHHMMSSZ）
  - STOP=1 後の SKIP 規約チェック（文字列で）

else:
  print("SKIP: phase=test reason=\"tests dir missing\"")

### 5) 既存テストと整合
try:
  run minimal test command(s) without heavy
  - 例: python -m pytest -q (あれば)
  - なければ python -m unittest (fallback)
catch:
  print("ERROR: phase=verify STOP=1")

END:
print("OK: phase=end STOP=<0|1>")
