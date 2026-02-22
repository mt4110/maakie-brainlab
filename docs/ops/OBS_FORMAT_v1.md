# OBS Format v1 (Draft)
目的: すべての入口スクリプトが「同じ形」で観測ログを吐くことで、解析・自動化・監査を安定化する。

## 絶対ルール
- stdout は **行ログ**のみ（機械が拾いやすい）
- 行の先頭は必ず `OK:` / `ERROR:` / `SKIP:` のいずれか
- 行の後半は `KEY=VALUE` をスペース区切りで付与（順不同）
- 失敗は exit/例外/終了コードで表現しない。**ERROR行 + STOP=1** を真実とする。
- STOP=1 以降は後続処理を行わず、**SKIP行**を残す（理由1行）
- obs_dir は **UTC命名のみ**（比較・集計・再現が安定する）

## 行ログの形
例:
- OK: phase=boot obs_format=v1 obs_dir=.local/obs/il_entry_20260222T010203Z
- OK: phase=validate ms=12 il_path=data/il/run.json
- ERROR: phase=execute code=E_EXEC reason="model_timeout" STOP=1
- SKIP: phase=post STOP=1 reason="prior ERROR"

### フィールド推奨
- phase=...        : 処理の段
- step=...         : phase内の細分
- ms=...           : 所要時間(任意)
- code=...         : エラー分類(任意)
- reason="..."     : 人間向け理由（短く）
- STOP=0/1         : 実行継続可否（重要）
- obs_format=v1    : 規格バージョン（重要）
- obs_dir=...      : 詳細ファイル出力先（重要）

## obs_dir 命名
- `.local/obs/<name>_<YYYYMMDDTHHMMSSZ>` （UTC）
- 例: `.local/obs/il_entry_20260222T010203Z`

## stdout とファイルの分離
- stdout: 行ログ（OK/ERROR/SKIP + KEY=VALUE）
- ファイル: 詳細（json, txt など）
  - 例: `${obs_dir}/result.json`, `${obs_dir}/detail.log`
