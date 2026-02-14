# S17-02 PLAN — IL validator / canonicalizer (Contract v1)

## 0. 現状 / 前提（SOT）
- SOT: `docs/il/IL_CONTRACT_v1.md` と `docs/il/il.schema.json` が唯一の基準。
- 例（fixtures）:
  - `docs/il/examples/good_min.json` … PASS 期待
  - `docs/il/examples/bad_min.json` … FAIL 期待
  - `docs/il/examples/bad_forbidden_timestamp.json` … FAIL 期待
- 目的: 下流（pipeline / eval）が “悩まない” ために、OK/NG を機械的に判定できる IL 検証と正規化を実装する。

## 1. 目的（Goal）
IL Contract v1 に対して以下を提供する:

1) **validator**  
- IL item の妥当性チェック（必須/型/禁止フィールド/フォーマット/追加プロパティ等）
- **失敗時の errors 形式を Contract に固定**（空配列禁止などを含む）

2) **canonicalizer**  
- IL item を “安定な表現” に正規化（canonical JSON / JSONL）
- 同一入力 → 同一出力（再現性100%）

3) **統合**  
- 既存 normalize / pipeline に最小差分で組み込み、下流が validator/canonicalizer を必ず通る導線にする。

## 2. 非目的（Non-Goals）
- IL v2 など新バージョン策定はしない（Contract v1 を実装するだけ）
- 大規模な依存追加やリファクタはしない（最小差分・最短導線）
- 例外で握りつぶす挙動は作らない（必ず errors で説明する）

## 3. 設計原則（壊れないための縛り）
- **決定論**: 同一入力 → 同一出力（canonical JSON）
- **責務分離**: validator と canonicalizer は概念的に別（同一モジュール内でも関数/層は分ける）
- **SOT固定**: Contract + schema が真。コードは追従。
- **エラーは仕様**: 下流のUX。迷わせない。
- **依存は最小**: 既存依存を優先。追加するなら理由を docs に残す。

## 4. インタフェース（内部APIの“形”だけ先に固定）
※ 実際の関数名/配置は repo の既存スタイルに合わせる（勝手に新ルールを作らない）

### 4.1 validate (概念)
入力: IL item（dict相当）  
出力:
- OK: （成功を示す値。errors は Contract に従う）
- NG: Contract準拠の errors（必ず非空）

### 4.2 canonicalize (概念)
前提: validate を通った item のみ対象（validate失敗は canonicalize しない）  
出力: canonical JSON 表現（以下の規則で固定）

## 5. canonical JSON 規則（決定論の芯）
- JSONシリアライズは以下を固定:
  - キー順: 辞書キーを常にソート
  - 区切り: 余計な空白なし（例: `,` と `:` の後にスペースなし）
  - 改行: JSONL は 1行1item、末尾 `\n` 固定
- 配列順: **入力順を保持**（Contract が別途指定していない限り勝手に並べ替えない）
- 数値/文字列: 仕様があるなら Contract に従う（無ければ “そのまま”）
- 禁止フィールド:
  - 基本方針: validator で FAIL。canonicalizer は “削って帳尻合わせ” しない。
  - 例: `bad_forbidden_timestamp.json` は FAIL すること。

## 6. errors 仕様（Contract v1 に完全追従）
- errors は “下流がそのまま表示・集計できる” 構造にする
- 最重要: **FAIL のとき errors は必ず非空**（空配列を返さない）
- エラーの順序も決定論にする:
  - 例: `(path, code, message)` の昇順でソート（※実フィールド名は Contract に合わせる）
- 実装前に Contract を読んで “errors 形” を抜き出して docs に固定する（このPlanの Step 1 でやる）

## 7. 実装配置（最終は探索して確定）
候補:
- Python 実装があるなら `src/...` の既存 “normalize/pipeline” 近傍に入れる
- 新規ディレクトリを増やすより、既存の文脈へ最小追加（長期破綻しにくい）

## 8. テスト方針（fixtures が根拠）
- `good_min.json` → PASS
- `bad_min.json` → FAIL（errors 非空）
- `bad_forbidden_timestamp.json` → FAIL（errors 非空）
- canonical JSON が安定:
  - 同じ入力を2回canonicalizeして同一文字列になる
  - “キー順” と “空白” が規則通り

## 9. 受け入れ条件（Acceptance）
- `make test` PASS
- `go run cmd/reviewpack/main.go submit --mode verify-only` PASS
- fixtures の期待が満たされる
- エラー順序が決定論（テストで固定できる）
- 依存追加をした場合、その理由と範囲が docs に残っている

## 10. 実装ステップ（分岐つき / STOPつき疑似コード）
### Step A: 入口特定（最重要）
IF IL の生成/normalize 入口が見つからない:
  STOP（推測で追加しない。rg結果を evidence として残す）
ELSE:
  continue

### Step B: Contract抽出
- Contract と schema から errors 形式・禁止フィールド・必須制約を抽出し、コードのTODOを “仕様固定” に変換する

### Step C: validator
- schema 検証 + Contract固有ルール（禁止フィールド等）
- errors の形と順序を固定

### Step D: canonicalizer
- validate を通った item のみ canonicalize
- 決定論のための JSON 出力規則をコードで固定

### Step E: pipeline統合
- normalize/pipeline の “出口1箇所” に差し込む（導線を増やさない）

### Step F: Gate
- make test
- reviewpack submit verify-only
- git status clean
