# S21 PLAN — Ops Hygiene (Outer Wall)

## Why
運用の衛生を“外壁”として固定する。
backlog項目が増えても、迷子にならず、壊れず、同じ儀式で整理できる状態を作る。

## Scope (Outer Wall)
- STATUS により「いま動いてるもの／次に触るもの／止めたもの」を一目で分かる化
- Triage 儀式（分類→移植→墓場）を定義し、増え続ける backlog を破綻させない
- 単一SOT原則：同じタスクが複数ファイルで“未完のまま”漂流しないようにする
- 観測（進捗%スナップショット）をSOTとして残す

## Non-Goals
- 過去Sxxの全面改稿（必要最小限の移植のみ）
- 新しい自動ツール実装（S21-01は基本ドキュメント運用で勝つ）

## Terms / Taxonomy
- ACTIVE: いま走ってる（PR/ブランチがある）
- NEXT: 次に着手する（優先キュー）
- PARKED: 価値はあるが今やらない（理由が必須）
- GRAVEYARD: やらないと決めた（理由が必須）
- MIGRATED: 古いbacklog項目を“参照”に変え、現行SOTへ移植済み

## Absolute Rules (No-Exit Contract)
- exit / return / set -e / trap EXIT / sys.exit / raise SystemExit / assert を運用設計に持ち込まない
- STOP は「人間がそこで止まる」
- 判定は終了コードではなく “出力テキスト” で行う（OK/ERROR/SKIP）

## Triage Ritual (Recurring)
1. Snapshot: backlog総量とホットスポット（ファイル別件数）を採取
2. Choose Top-N: 上位ファイルから順に “移植候補” を選ぶ
3. For each backlog line:
   - if ACTIVE/NEXT に上げる → SOT(現行Task)へ移植
   - else if PARKED → PARK理由を書いてSTATUSへ
   - else → GRAVEYARD（やらない理由を書く）
4. 古い場所はチェックボックスを残さない（参照行に置換して漂流を止める）
5. STATUS を更新して「次の一手」を固定

## Success Criteria
- STATUSがあり、S21の運用ルールがそれだけで再現できる
- backlogが増えても「分類→移植→墓場」で破綻しない
