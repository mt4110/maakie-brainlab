# S16-01（AI Contract “強制”）— repo実パス確定版 PLAN

## ゴール（ぶれない定義）

AI Contract を「ドキュメント」から「強制される仕様」に格上げする。

### 最低ライン（これが満たされれば勝ち）：

- Contract(v1) の必須出力（= pack内の必須ファイル/構造）がコードで固定されている
- reviewpack submit --mode verify-only がそれを検証し、PASS/FAIL を確実に出す
- 以降AI側をガッツリ触っても、成果物の“形”が崩れない（＝契約違反が検知される）

## 互換性（長期破綻しないための前提）

ここが地味に重要。過去の証拠を未来で検証できるのが監査的に強い。

方針：PACK_VERSIONで世代分岐する
- PACK_VERSION = 1：従来仕様（契約ファイルなしでも検証できる＝過去資産を殺さない）
- PACK_VERSION >= 2：AI Contract v1 を強制（今回から）

つまり S16-01 の本質は「契約強制」＋「破壊的変更の吸収（versioning）」。

## Contract v1（強制仕様）— 正式定義

PACK_VERSION >= 2 のとき、pack root（review_pack/）に以下が必須：

### 必須パス
- PACK_VERSION
- CONTRACT_v1（契約の宣言ファイル。存在することが契約の起動スイッチ）
- logs/portable/（dir）
- logs/portable/rules-v1.json（サニタイズ規約。存在＋JSONとしてparse可能）

### 必須条件（構造）
- logs/portable/ 配下に 少なくとも1つ以上 *.log が存在する
- logs/portable/*.log が存在する場合、対応する *.log.sha256 が 必ず存在する
  - 例：foo.log → foo.log.sha256

### CONTRACT_v1 の内容（推奨の最小スキーマ）
ファイル名は CONTRACT_v1（拡張子なし）で良い。中身はJSON（機械検証しやすい）。
encoding/jsonのstructで生成してキー順を安定化する（map禁止）。

最小フィールド案：
- contract_version: 1
- pack_version: （PACK_VERSIONの文字列）
- required_paths: 上の必須パス配列
- portable_log_requires_sha256: true

ポイント：契約は「コードがSOT」。JSONは“観測可能な宣言”であり、verify-onlyがそれを突き合わせる。

## verify-only の判定仕様（PASS/FAILがぶれないために）

reviewpack submit --mode verify-only は最終的にこうなる：

擬似コード（Planは分岐と停止条件が命）：

PHASE 0: Preflight
  root := git rev-parse --show-toplevel
  STOP if not git repo
  STOP if on main
  OK even if dirty? -> (project policyに従う。基本は STOP 推奨)

PHASE 1: Locate pack root
  r := findDirContainingFile(tmpDir, "PACK_VERSION", depth=2)
  STOP if not found

PHASE 2: Read PACK_VERSION
  v := readTrim("PACK_VERSION")
  STOP if empty

PHASE 3: Version gate
  IF v == "1" (or parseMajor==1):
      legacyVerify(r)   # 既存のverify挙動を維持
      PASS/FAIL
  ELSE:
      verifyContractV1(r)
      PASS/FAIL

PHASE 4: verifyContractV1(r)
  REQUIRE file "CONTRACT_v1" exists
  REQUIRE dir "logs/portable" exists
  REQUIRE file "logs/portable/rules-v1.json" exists AND JSON parse OK
  REQUIRE glob "logs/portable/*.log" has >= 1
  FOR EACH log in logs/portable/*.log:
      REQUIRE "${log}.sha256" exists
  PASS

### 停止条件（嘘をつかない仕組み）：
- 1つでも欠けたら その場で error（=FAIL）
- skipする場合は 理由を必ず1行（※今回は“強制”なので基本skipしない）

## 実装方針（コード設計）
- 契約定義は 定数 + 小さい関数に閉じ込める（散らすと破綻する）
- JSON生成は struct を使う（map使うと順序が揺れる可能性が上がる）
- エラーは「何が足りないか」が1行で分かる文字列にする
  例：contract_v1: missing required path: logs/portable/rules-v1.json

## テスト（最低限）
- PACK_VERSION=1 のpackは従来通り通る（互換性テスト）
- PACK_VERSION=2 で CONTRACT_v1 が無い → FAIL
- rules-v1.json が壊れたJSON → FAIL
- *.log はあるが *.log.sha256 が無い → FAIL

## 完了条件（Acceptance）
- make test PASS
- go run cmd/reviewpack/main.go submit --mode verify-only PASS
- 1つ以上の契約違反ケースで 意図通り FAIL を確認できる（最低1ケースはローカルで再現）
