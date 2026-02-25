# RULESET_GUARD (Runbook)

## Purpose
Ruleset の required status checks に「存在しない context（幽霊）」が混入して merge が詰む事故を、観測とSOTで再発しにくくする。

このツールは "OK/WARN/ERROR/SKIP" を出力し、終了コードに依存しない。

## Files
- tools/ops/ruleset_guard.py
- ops/ruleset_required_status_checks.json

## Quick Start (Local)
### 1) ruleset 一覧
python3 tools/ops/ruleset_guard.py list-rulesets

### 2) 監査（ref は HEAD 既定）
python3 tools/ops/ruleset_guard.py audit

### 3) ruleset を指定して SOT を作成（IDは list-rulesets で取得）
python3 tools/ops/ruleset_guard.py write-sot --ruleset-id 123 --sot ops/ruleset_required_status_checks.json

### 4) SOT → ruleset 反映（安全フラグが揃った場合のみ）
APPLY=1 python3 tools/ops/ruleset_guard.py sync --ruleset-id 123 --sot ops/ruleset_required_status_checks.json

## Notes
- "observed contexts" は check-runs と commit statuses を合成して見る
- ref によっては PR 時だけ出る checks がある。必要なら監査 ref を明示する
