# S22-02 PLAN — P2 IL executor minimal

## Status

- Phase: S22-02 (P2)
- Prev: S22-01 (P1 IL canonicalize) — **Merged PR #76** ✅
- Next: S22-03 (P3) is **blocked** until S22-02 is merged.

## Goal (Non-Negotiable)

IL を「ただのJSON」から **決定論的に処理を駆動する"小さなプログラム"**に格上げする。
ただし P2 は *賢くならない*。**嘘をつかない**ことだけに全振りする。

## Hard Rules (Project-wide)

- **外部通信禁止**（ネットワークI/O禁止）。P2のRETRIEVEはローカルfixtureのみ。
- **exit系禁止**：終了コードで制御しない。成功/失敗は必ずログ（JSON+print）で真実化する。
- **例外で落ちない**：トップレベルでcatchして `overall_status=ERROR` に落として report を必ず吐く。
- **決定論**：時刻、乱数、並列の順序、OS依存を結果に混ぜない（必要なら sort / stable key）。

## Scope (P2 Minimal Opcodes)

最小opcode v1（4つ、これで十分）：

1. SEARCH_TERMS
2. RETRIEVE
3. ANSWER（P2では常にSKIPでOK：LLMは非決定）
4. CITE

## Inputs

- IL JSON (P1でcanonicalize済みを前提)
- fixture store（RETRIEVEが参照するローカルデータ）
- out_dir（artifacts出力先）

## Outputs (Artifacts) — "成功/失敗の嘘"を潰す

### Always (常に出す＝真実ログ)

- `il.exec.report.json`
  - stepごとの OK/ERROR/SKIP
  - 理由（reason）は必須
  - どんな入力を見て何を出したかの要約（全文コピペ禁止・要約のみ）

### Only when overall_status == OK (成功の証拠)

- `il.exec.result.json`
  - answer / cites 等（P2ではanswerは空でも良いが、構造は固定）

### Strict Rule

- `overall_status=ERROR` が1つでもあれば **result.json は出さない**
- `overall_status` の決定：
  - ERRORが1つでもあれば ERROR
  - ERRORなしで OKが1つでもあれば OK
  - 全部SKIPなら SKIP

## Contracts (v1)

### report schema (concept)

- `schema`: "IL_EXEC_REPORT_v1"
- `overall_status`: "OK" | "ERROR" | "SKIP"
- `steps`: list of
  - `index` (int)
  - `opcode` (str)
  - `status` ("OK"|"ERROR"|"SKIP")
  - `reason` (str, non-empty)
  - `in_summary` (dict/str)
  - `out_summary` (dict/str)

### result schema (concept)

- `schema`: "IL_EXEC_RESULT_v1"
- `cites`: list (deterministic order)
- `answer`: str (P2では空文字。MUST: 常に存在する)

## Opcode Semantics (Deterministic)

### 1) SEARCH_TERMS

- input: `il.search_terms` があるなら検証して通す。無いなら SKIP（導出は次PR）
- output: `terms`: list[str] (sorted, dedup)

### 2) RETRIEVE

- fixture only: `retrieve_db.json` を唯一のデータ源にする（P2）
- algorithm: termsごとに index から doc_id を取得 → sort → dedup
- 見つからなければ SKIP
- output: `retrieved`: list of docs (deterministic order)

### 3) ANSWER (P2)

- 常に SKIP
- reason: "P2: LLM/non-deterministic; answering is deferred"

### 4) CITE

- input: retrieved docs
- cite_key = sha256("doc_id\nsource")[:16]
- output: `cites`: list[{cite_key, doc_id, source, title}]

## Deliverables

- `src/il_executor.py`（中核：step interpreter + report/result writer）
- `scripts/il_exec_run.py`（CLI：入力/fixture/out_dir指定、例外catchして必ずreport）
- `scripts/il_exec_selftest.py`（OK/ERROR/SKIPをprint、常に0で返す）
- fixtures:
  - `tests/fixtures/il_exec/il_min.json`
  - `tests/fixtures/il_exec/retrieve_db.json`
- docs:
  - `docs/il/IL_EXEC_CONTRACT_v1.md`（report/resultの契約を固定化）
