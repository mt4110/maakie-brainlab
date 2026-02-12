# S8_PLAN — Determinism / Audit Tightening
(監査即時性 + ノイズ抑制の境界線を仕様化する)

## 0. 状態 / 前提
- PR #32 merged ✅（S7 bundle UX polish）
- S7: verify-only / pack-contained Gate-1 は OK ✅
- 破壊しない（verify-only PASS 維持）
- “ログ改変”は最小限（必要なら「抑制」優先、「置換」は最後）

## 1. 目的（S8）
- 監査の即時性を上げる：
  - `go test -count=1` の適用範囲/ポリシーを確定
  - `go test -mod=readonly` の適用範囲/失敗時UXを確定（CIだけ落ちる病を殺す）
- bundleログの可搬性を上げる：
  - 環境依存ノイズを抑制する（ただし監査性を落とす改変はしない）
  - rawは保持し、閲覧/差分用に portable view を作る（監査ガード付き）

## 2. 定義（S8で固定する言葉）
- 監査即時性（Audit Immediacy）:
  - 「同じ入力に対して、今この場でテスト/検証が実行され、結果が最新である」こと
  - 具体: Go test cache による過去結果の再利用を避ける（`-count=1`）
- 監査性（Auditability）:
  - 「後から、何を実行し、何が起きたか」を復元可能な形で残すこと
  - 具体: 実行コマンド/exit code/失敗理由/重要ログは raw で保持
- ノイズ（Noise）:
  - 監査判断に寄与しないが、環境差で変動しやすく、diff/比較を汚す情報
  - 例: temp dir 絶対パス、ランダムID、経過秒、ワーカー用一時ファイル名など
- 抑制（Suppress）:
  - 表示やportable viewから除外する（rawには残る）
- 置換（Replace）:
  - `<TMPDIR>` のようなトークンに置き換える（rawとは別ファイルでのみ許可）

## 3. 境界線（ここがS8의 “勝ち筋”）
### 3.1 絶対に残す（監査クリティカル / 抑制禁止）
- 実行コマンド全文（go test の引数含む）
- 実行環境の要点（go version / GOOS / GOARCH / module mode 等、最小セット）
- 失敗時のエラー全文（依存解決失敗・コンパイル失敗・テスト失敗）
- verify-only の Gate 判定根拠（PASS/FAIL とその理由）
- raw log（生ログ） + raw log のハッシュ（改ざん検知）

### 3.2 抑制してよい（ノイズ / portable viewのみ）
- temp dir の絶対パス（/var/folders/...）
- timing（XXms, X.XXXs などの経過時間）
- 一時ファイル名やランダムっぽいID（UUID風、乱数風）
- デバッグ詳細のうち「作業ディレクトリ/一時領域」露出だけが目的の行

### 3.3 置換は最後（やるなら portable viewでのみ）
- 「抑制だと情報が欠けて比較不能」な場合に限定
- 例: “pathが要素として必要だが絶対パスがノイズ” → `<TMPDIR>/...` に置換
- 置換ルールは versioned & 明示（ルール自体が監査対象）

## 4. `go test` オプション方針（ローカル/CI/オフライン）
### 4.1 基本方針
- CI（strict）:
  - `go test -count=1 -mod=readonly` を標準化
- Local（permissive）:
  - デフォルトは破壊しない（既存のまま）
  - ただし opt-in で strict と同等にできる導線を用意
- Offline:
  - “勝手に依存を書き換えない” を守る（-mod=readonlyは妥当）
  - ただしモジュールキャッシュ不足は起きうるため、失敗時メッセージを強化し誘導する

### 4.2 失敗時UX（CIだけ落ちる病の封じ）
- -mod=readonly 失敗を「原因別」に誘導：
  - go.sum/go.mod が更新必要 → “先に go mod tidy / go test を通常モードで実行し差分をコミットせよ”
  - モジュール未キャッシュでオフライン → “オンラインで go mod download を実行してから再試行せよ”
- 重要: 失敗原因の raw を残し、メッセージは補助（捏造しない）

## 5. ログ可搬性の設計（raw保持 + portable view）
- bundle には以下を同梱（例）:
  - `logs/raw/<step>.log` : 生ログ
  - `logs/portable/<step>.log` : 抑制/必要なら置換した閲覧用
  - `logs/portable/rules-v1.json` : 抑制/置換ルール定義（versioned）
  - `logs/raw/<step>.log.sha256` : rawハッシュ（監査ガード）
- 原則:
  - verify 判定は raw を根拠とする（portable は表示/比較用）
  - portable が壊れても監査は死なない（rawが真実）

## 6. 実装スコープ（S8で触って良い範囲）
- code:
  - `internal/reviewpack/*`（go test 実行とログ出力がある場所）
  - 既存の実行/ログパイプラインに“最小差分”で追加する
- docs:
  - `docs/ops/S8_PLAN.md`
  - `docs/ops/S8_TASK.md`
  - 既存のRUNBOOK/Walkthroughがあるなら、そこへS8方針を1節追記

## 7. 成果物（Doneの定義）
- CI strict で `go test -count=1 -mod=readonly` が効いている
- verify-only PASS を維持
- raw log と portable view が bundle に同梱される（rawハッシュ付き）
- ノイズ抑制が “抑制→置換（最終手段）” の順で実装され、ルールが versioned
- 失敗時UXが原因別に誘導し、かつ raw を残す（捏造しない）

## 8. 非目標（S8でやらない）
- ログの“完全な匿名化”や“機微情報マスキング”の一般解（別フェーズ）
- 既存フォーマットの大破壊（互換なし変更）
- ネットワークを前提にした動的取得（オフライン耐性を落とす）
