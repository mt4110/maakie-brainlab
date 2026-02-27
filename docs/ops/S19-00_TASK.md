# DETERMINISTIC_TASK_TEMPLATE (v1)

## Safety Snapshot
- [x] cd repo root
- [x] git fetch -p origin
- [x] git status -sb (dirty/ahead -> STOP)

## 0) Scope
- [x] scope 1文
- [x] scope根拠パス1行
- [x] missing -> ERROR STOP

## 1) Branch
- [x] create/switch (skip理由1行)

## 2) Files (path fixed)
- [x] PLAN/TASK 実パス固定
- [x] template copy
- [x] PLAN/TASK に Scope/Deliverables/Gates/STOP を確定

## 3) Local Gates
- [x] make test
- [x] reviewpack submit --mode verify-only

## 4) Canonical Pin (single)
- [x] commit / bundle / sha256
- [x] PR本文 Canonical を1回だけ更新
