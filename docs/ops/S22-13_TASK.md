# S22-13_TASK: Required Checks SOT Sync（ドキュメント漂流の根絶）v2（Closeout）

## 進捗

* S22-13: 100% ✅（PR #93 / fail-closed 動作確認済み）

## 概要（SOT）

* 目的：GitHub required checks（現実）と docs/ops/CI_REQUIRED_CHECKS.md（SOT）がズレた瞬間に、merge guard が STOP=1 で止める（人間の注意力運用を廃止）
* 現実制約：private repo + 現条件で rulesets API が取得不能なため、classic branch protection の contexts endpoint を唯一の現実ソースとして採用
* ポリシー：現実が取得不能 / 未設定 / 空 の場合は **ERROR（fail-closed）** とし、マージ儀式を必ず停止（嘘を付かない）

## Task（順序固定 / 完了）

* [x] 00. OBS作成（.local/obs/s22-13_*）
* [x] 01. 現状観測：CI_REQUIRED_CHECKS.md / pr_merge_guard.sh / required checks取得可否 を OBS 保存
* [x] 02. docs/ops/CI_REQUIRED_CHECKS.md に required_checks_sot:v1 ブロックを追加（機械可読SOT）
* [x] 03. NEW: ops/required_checks_sot.py を追加（stopless / fail-closed）

  * mode=check: 現実の required checks を取得 → SOT集合比較 → OK/ERROR
  * mode=write-sot: 現実が取れた場合のみ SOTブロック更新（取れない場合はERRORで何もしない）
  * mode=dump-live: 現実一覧を出力（監査用）
  * 重要：取得不能 / 未設定 / 空 = ERROR（fail-closed）
* [x] 04. NEW: ops/required_checks_sot.sh を追加（thin wrapper / stopless）
* [x] 05. required_checks_sot の実行ログを OBS 化（OK/ERROR/SKIP を証拠として保存）
* [x] 06. MOD: ops/pr_merge_guard.sh に required checks gate を統合（fail-closed）

  * required_checks_sot の出力に **OK: required_checks_sot matched** が無い場合：STOP=1
* [x] 07. docs/ops/STATUS.md を S22-13: 100%（PR #93）へ更新
* [x] 08. 軽量検証（diff stat / required_checks_sot 出力 / guard の STOP=1 挙動）を OBS 化
* [x] 09. PR #93 作成（S22-13 v2 実装を集約）
* [x] 10. fail-closed 動作確認（現状 required checks が null/取得不能のため、期待通りマージがブロックされることを確認）
* [x] 11. closeout：本TASKを 100% に更新し、証拠を確定

## 証拠（例 / 監査ログ）

* fail-closed の期待出力（現状設定により再現）：

  * ERROR: live checks unavailable [fail-closed]
  * ERROR: required checks gate failed; STOP=1
* reviewpack verify-only（提出物の検証）：

  * SUBMIT: review_bundle_20260225_114404.tar.gz
  * SHA256: 5398e53c5e37948e4cd464f01776433ef01495f66d770454c9ed175acd798a9b
* walkthrough:

  * walkthrough.md（※リポジトリに入れる場合は file:// 等の非portable要素を含めない）

## 既知の運用手順（後日：GitHub設定が整った時に解除）

required checks を GitHub UI で有効化した後：

1. bash ops/required_checks_sot.sh dump-live
2. bash ops/required_checks_sot.sh write-sot
3. bash ops/required_checks_sot.sh check  → OK: required_checks_sot matched
4. merge guard 経由で merge

## 最終状態

* S22-13 の関所（required checks drift 検知 / fail-closed）が完成
* required checks が未設定/取得不能な状態では「嘘を付かず」必ず停止する
