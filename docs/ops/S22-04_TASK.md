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
- Ref: .local/obs/s22-03_close_20260221T225032Z/20_copilot_extract.md
- Rule: include only items that affect S22-04 IL-planned RAG steps (collect/normalize/index/search/cite)
