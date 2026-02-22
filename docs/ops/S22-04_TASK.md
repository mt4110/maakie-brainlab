# DETERMINISTIC_TASK_TEMPLATE (v1)

## Safety Snapshot
- [ ] cd repo root
- [ ] git fetch -p origin
- [ ] git status -sb (dirty/ahead -> STOP)

## 0) Scope
- [ ] scope 1文
- [ ] scope根拠パス1行
- [ ] missing -> ERROR STOP

## 1) Branch
- [ ] create/switch (skip理由1行)

## 2) Files (path fixed)
- [ ] PLAN/TASK 実パス固定
- [ ] template copy
- [ ] PLAN/TASK に Scope/Deliverables/Gates/STOP を確定

## 3) Local Gates
- [ ] make test
- [ ] reviewpack submit --mode verify-only

## 4) Canonical Pin (single)
- [ ] commit / bundle / sha256
- [ ] PR本文 Canonical を1回だけ更新

## Carry-over (from PR78 Copilot)

- Ref: .local/obs/s22-03_close_20260221T230056Z/20_copilot_extract.md
- Rule: include only items that affect S22-04 IL-planned RAG steps (collect/normalize/index/search/cite)

## Implementation Tasks (stopless / split-heavy)

### 0) Observability setup

- [ ] Create run obs_dir: .local/obs/s22-04_<utc>/
- [ ] Every step writes:
  - <NN>_header.txt (step intent)
  - <NN>_run.log    (stdout/stderr captured)
  - <NN>_result.txt  (OK/ERROR/SKIP summary lines)

### 1) Path discovery (NO guessing)

- [ ] for: find IL schema/contract files
  - cmd: rg -n --hidden --no-heading "IL\\b|schema\\b|opcode\\b|canonicalize\\b" .
  - if found: write OK lines into .local/obs/s22-04_paths.txt then break
  - else: continue until exhaustion
- [ ] for: find executor implementation/entry
  - cmd: rg -n --hidden --no-heading "executor\\b|il_exec\\b|run_il\\b|execute\\(" .
  - if found: append OK lines then break
  - else: continue
- [ ] if: no critical paths found
  - write ERROR: cannot locate IL/executor paths
  - set STOP=1 (and skip all implementation steps)

### 2) IL contract update (small and safe)

- [ ] if STOP==0: add opcodes COLLECT/NORMALIZE/INDEX/SEARCH_RAG/CITE_RAG
- [ ] ensure: required fields defined for each opcode (inputs/outputs)
- [ ] output: contract diff is minimal (no refactor)

### 3) Implement opcodes as separate units (avoid spikes)

- [ ] COLLECT (tiny corpus first)
  - inputs: repo-relative paths list (seed-mini)
  - outputs: 10_collect_manifest.jsonl + blobs
  - if corpus too large: SKIP with reason, keep seed-mini only

- [ ] NORMALIZE
  - utf-8 decode policy + newline canonicalization
  - outputs: norm texts + manifest

- [ ] INDEX (v0 lightweight)
  - build deterministic inverted index JSON (no embeddings yet)
  - enforce stable ordering in JSON output

- [ ] SEARCH
  - deterministic scoring + stable tie-break

- [ ] CITE
  - deterministic excerpt extraction (fixed max chars)
  - outputs: citations jsonl + md

### 4) Verification (split; never "all at once")

- [ ] Smoke: run pipeline on seed-mini
  - check required artifacts exist
  - do not exit on failure; write ERROR lines
- [ ] Determinism: run twice, compare sha256 of key artifacts
  - mismatch => ERROR + STOP
- [ ] Heavy verify-only is the last checkbox (optional at phase end)

### 5) SOT / STATUS updates

- [ ] Keep S22-04 at 1% until (1) path discovery + (2) contract update completed
- [ ] After (2): bump to 10% with evidence path(s)
