# PRODUCT.md

**Status:** canonical product definition for maintainers and Codex CLI  
**Audience:** product owner, maintainers, implementers, reviewers  
**Visibility:** public-safe. Do **not** put secrets, personal absolute paths, unreleased business deals, user PII, or private experiment notes in this file. Put those in `PRODUCT.private.md` or another private document.

---

## 0. この文書の役割

この文書は、**maakie-brainlab を何のための製品に戻すか**を定義する。

実装判断で迷ったときの優先順位は次の通りとする。

1. `PRODUCT.md` — プロダクトの真実
2. `AGENTS.md` — 開発運用・儀式・ブランチルール
3. `README.md` — セットアップと現状説明
4. `SPEC.md` / reviewpack / evidencepack 関連文書 — 成果物と検証仕様
5. 既存コード・既存UI

**重要:** 既存コードや既存ダッシュボードがこの文書と衝突する場合、原則として **プロダクトをこの文書に寄せる**。過去の広がりより、今後の使い勝手を優先する。

---

## 1. 製品を一文で言うと

**maakie-brainlab は、非AI研究者のための「根拠付きローカル知識ワークベンチ」である。**

ユーザーは:

1. 資料を入れる
2. 自然言語で質問する
3. 根拠を確認する

この3つだけで前に進める。  
ユーザーに **RAG / LangChain / chunk / rerank / eval taxonomy / contract internals** を理解させることは製品目的ではない。

---

## 2. 何を解決する製品か

### 2.1 解決したい課題

非AI研究者が知りたいのは次のことである。

- どの資料が入っているか
- 質問に対する答えは何か
- その答えの根拠はどこか
- 根拠が足りないなら、どこまで分かってどこから分からないのか

### 2.2 解決したくない課題

この製品は、次を主目的にしない。

- RAG の教材になること
- LangChain の検証 playground になること
- ML 評価ダッシュボードを常用させること
- 多機能な AI 実験ポータルになること
- 一般的な自律エージェント基盤になること
- “なんでも入り” の研究OSになること

### 2.3 プロダクトの勝ち筋

この製品の価値は **賢そうに見えること** ではなく、次の3点である。

- **根拠が見えること**
- **分からないときに分からないと言えること**
- **後から検証できること**

---

## 3. 想定ユーザー

### 3.1 Primary user

- 非AI研究者
- ローカル資料を扱う知識労働者
- プロンプトやRAG内部設定ではなく、**資料から答えを得たい人**

### 3.2 Secondary user

- 開発者
- 運用者
- 評価・検証担当

### 3.3 Non-target user（少なくとも v1 では前面に出さない）

- LangChain の細かい比較を主目的にする人
- RAG パラメータ調整そのものを主作業にしたい人
- 複数エージェント合意形成を日常的に回したい人
- Fine-tune / ML experiment / contract trace をメインUIで見たい人

これらは **完全に否定しない**。ただし **operator / lab / internal** の扱いに下げる。

---

## 4. 製品原則

1. **Task first, AI second**  
   AI 内部概念より、ユーザーの作業完了を優先する。

2. **Evidence first**  
   回答は根拠と一緒に出す。根拠が弱いなら、その弱さを出す。

3. **Unknown is acceptable**  
   分からないことを正しく伝えるのは失敗ではない。

4. **Operator complexity is hidden by default**  
   運用・評価・実験の複雑さは、通常ユーザーに見せない。

5. **Deterministic core over flashy orchestration**  
   まずは決定論・再現性・検証性を守る。

6. **Small stable core before any new lab**  
   主要体験が固まる前に、新しい研究室ページを増やさない。

---

## 5. 製品のコア体験

通常ユーザーに見せる主要導線は **3面** に限定する。

### 5.1 画面A: 資料

目的: 「何が入っているか」と「今使えるか」を把握できること。

必須要件:

- 資料一覧を見られる
- 各資料の状態を見られる
  - 取り込み済み
  - インデックス済み / 未更新
  - エラーあり
- 資料追加ができる
- 再インデックスができる
- 最終更新時刻を見られる
- どの資料が現在の知識ベースに含まれるかが分かる

通常ユーザーに見せないもの:

- chunk size
- overlap
- embedding model
- rerank score
- provider canary
- eval taxonomy
- LangChain 実験結果
- ML 実験履歴
- opcode / IL 内部構造

### 5.2 画面B: 質問

目的: 自然言語で質問し、**使える答え**を得ること。

必須要件:

- 質問入力欄
- 実行ボタン
- 回答の短い要約
- 使われた資料への導線
- 不明時の明確な表示
- 「なぜ不明なのか」の説明

回答UIの理想形:

- **答え**
- **根拠**
- **使われた資料**
- **分からないこと / 注意点**

内部では4ブロック契約（結論 / 根拠 / 参照 / 不確実性）を使ってよい。  
ただし通常UIでは、ユーザーが理解しやすい表現へ整形してよい。

### 5.3 画面C: 根拠

目的: 「どの一節を根拠に答えたか」を確認できること。

必須要件:

- 引用スニペットを表示する
- 出典ファイル名を表示する
- `path#chunk-N` のような内部参照も表示可能にする
- 可能なら元文書の該当位置に飛べる
- どの根拠がどの回答部分を支えているか追える

この画面は、単独ページでも、回答画面の右ペインでもよい。  
重要なのは「見えること」であり、ページ構成そのものではない。

---

## 6. 通常ユーザーに見せないもの

次は **運用者専用** または **内部ラボ** に降格する。

- Overview（多指標まとめ）
- Evidence History
- Prompt Trace
- Fine-tune
- AI Lab
- Consensus
- ML Studio
- RAG Lab
- LangChain Lab
- Quality / Operator export 詳細
- 生の Contract 違反ログ一覧
- Prompt loop / raw response / compile report の直接閲覧

これらは削除してもよいし、`/ops` や feature flag の下へ移してもよい。  
**通常ユーザーの最短導線からは外すこと。**

---

## 7. OpenCraw など外部収集レイヤとの関係

OpenCraw のような外部ツールは **敵ではない**。  
ただし本製品の責務は次の通りに分ける。

### 7.1 Upstream collector がやってよいこと

- Web から資料を集める
- 取得手順を自動化する
- 定期収集する
- ログイン済み操作やブラウザ作業を補助する

### 7.2 maakie-brainlab が責任を持つこと

- 取り込んだ資料を索引化する
- 質問に答える
- 根拠を示す
- 分からない場合は止まる
- 検証可能な証跡を残す
- reviewpack / evidencepack 的な再確認可能性を保つ

### 7.3 重要判断

**maakie-brainlab は “収集ツール” ではなく “根拠付き回答エンジン” である。**  
収集は接続してよいが、コア体験の中心には置かない。

---

## 8. v1 のスコープ

### 8.1 必ず入れる

- ローカル資料の登録
- ローカル資料の再インデックス
- 自然言語質問
- 根拠付き回答
- 不明応答
- 出典一覧
- 基本的なエラーメッセージ
- 最低限のログ保存
- 既存の検証基盤を壊さないこと

### 8.2 入れてよいが後回し

- 回答履歴
- お気に入り質問
- 共有用の evidence export
- 文書タグ
- 資料単位の ON/OFF
- 収集ツールとの連携

### 8.3 v1 では入れない

- 一般ユーザー向けの RAG 調整画面
- LangChain 実験画面
- ML 実験画面
- Multi-agent consensus を主機能にすること
- Fine-tune UI
- パラメータチューニング UI
- 複数ベクトルDBや複雑な retrieval backend の比較UI

---

## 9. 技術方針

### 9.1 コア方針

- まずは **既存の決定論的で軽い実装** を活かす
- シンプルに動くなら SQLite FTS5 ベースでよい
- OpenAI互換 endpoint に接続できるローカルLLMでよい
- `.md` / `.txt` を最優先でよい
- reviewpack / evidencepack / Gate 系は壊さない

### 9.2 明確な禁止事項

Codex CLI は、次を **MVP の main path に導入しないこと**。

- main path への LangChain 依存
- main path への複雑な agent orchestration
- main path への multi-provider consensus
- main path へのベクトルDB必須化
- main path への ML experiment UI
- main path への prompt trace UI

### 9.3 許容事項

次は **operator / lab / optional** として残してよい。

- LangChain PoC
- ML experiment
- prompt loop
- operator dashboard export
- consensus run
- canary / soak / readiness 系スクリプト

---

## 10. UX ルール

### 10.1 ユーザー向けコピー

通常UIでは、なるべく次の語彙を使う。

- 資料
- 質問
- 答え
- 根拠
- 使われた資料
- 分からないこと
- 更新
- エラー

通常UIでは、なるべく次の語彙を避ける。

- RAG
- retrieval
- chunk
- rerank
- eval wall
- failure taxonomy
- prompt trace
- contract violation
- consensus
- operator export

### 10.2 不明時のUX

不明時は次を必ず示す。

- 分からないという結論
- 何が足りないか
- 次に何をすればよいか
  - 資料を追加する
  - インデックスを更新する
  - 質問を具体化する

### 10.3 エラー時のUX

ユーザーに内部事情を丸投げしない。  
例:

- 悪い例: `OPENAI_API_BASE mismatch`
- 良い例: `ローカルモデルに接続できません。モデルサーバーが起動しているか確認してください。`

内部の詳細ログは operator 側に残してよい。

---

## 11. 受け入れ基準

### 11.1 主要体験

次を満たしたら、v1 は「復活可能」とみなす。

1. 新規ユーザーが、RAGの知識なしで資料を登録できる
2. 質問すると、答えと根拠が同時に見える
3. 根拠が無い質問には、明確に不明と答える
4. 出典ファイルに辿れる
5. 通常UIから LangChain / ML / RAG tuning を触らなくて済む
6. `gate1` や reviewpack 系を維持しつつ、通常利用にそれを要求しない

### 11.2 オンボーディング

- 初回体験で `make gate1` を必須にしない
- 初回体験で外部ストレージ symlink を必須にしない
- 初回体験で Go toolchain を必須にしない
- 初回体験は「資料追加 → 質問 → 根拠確認」の最短導線だけで成立させる

### 11.3 信頼性

- answer without source を成功扱いしない
- negative control 的な質問に対しては、不明回答を優先する
- 根拠付き回答の表示が壊れていたら release block とする

---

## 12. 計測指標

ビジネス指標ではなく、まずは製品妥当性を見る。

- **Time to first cited answer**
- **Unsupported question で unknown を返せた率**
- **回答に可視な根拠が付いた率**
- **通常UIで RAG / LangChain / ML の知識を要求した回数**
- **通常UIから operator 概念が漏れた回数**

目標は、内部スコアの精密さより **認知負荷の低さ** を改善すること。

---

## 13. 実装優先順位（Codex CLI 用）

### Phase 1: Surface simplification

- main nav を 3面へ削減する
- 現在の多機能 dashboard は `/ops` 相当に降格する
- lab / operator / trace 系を main path から外す
- README の通常導線を 3面プロダクトに合わせて更新する

### Phase 2: Core flow hardening

- 資料一覧
- インデックス状態表示
- 質問画面
- 回答 + 根拠表示
- 不明時の説明
- 基本エラーUI

### Phase 3: Trust and export

- 回答単位の evidence export
- answer history
- source inspection
- reviewpack / evidencepack との接続整理

### Phase 4: Optional upstream integration

- OpenCraw 等との連携
- 自動収集
- 更新通知

**注意:** Phase 1 が終わる前に、新しい lab 機能を追加しない。

---

## 14. 既存資産の扱い

次は **活かす側** の資産である。

- `src/ask.py` の evidence-first 回答方針
- `src/build_index.py` のシンプルな索引生成
- `eval/run_eval.py` の fail taxonomy と negative control 思想
- `ops/gate1.sh` の厳格検証
- `cmd/reviewpack/*` の verify-only パック思想
- `cmd/evidencepack/*` の証跡化の思想

次は **前面から下げる側** の資産である。

- `ops/dashboard` の多機能 lab / operator UI
- 実験系ページ群
- 内部運用を可視化するだけのページ群

---

## 15. README / UI / 文書更新ルール

実装がこの文書に寄ったら、次も必ず更新する。

- `README.md` の通常導線
- `ops/dashboard/README.md` の位置づけ
- 必要なら `docs/` 内の案内文
- UI の文言

README に個人ローカル環境前提の絶対パスを残し続けない。  
公開文書は、repo-relative または環境変数ベースにする。

---

## 16. 失敗の定義

次の状態なら、製品はまだ復活していない。

- ユーザーが質問前に RAG 設定を理解する必要がある
- ダッシュボードの多機能さが主価値になっている
- answer より metrics 画面の方が目立つ
- 根拠を確認できない
- 分からないときに止まれない
- operator 専用概念が main path に露出している

---

## 17. 成功の定義

次の状態なら、maakie-brainlab は「ちゃんとしたソフトウェア」と言える。

- 非AI研究者が迷わず資料を入れられる
- 迷わず質問できる
- 答えの根拠が見える
- 根拠が無いときは無いと言う
- 開発者は裏で検証・証跡・再確認を続けられる

つまり、**表は単純、裏は厳密** である。

---

## 18. Codex CLI への最終指示

実装時に迷ったら、次の原則で決めること。

1. 通常ユーザーの認知負荷を下げる
2. 根拠可視性を上げる
3. operator 複雑性を隠す
4. 既存の検証資産を壊さない
5. 新機能追加より、表面積削減を優先する

**足し算ではなく、引き算で復活させる。**