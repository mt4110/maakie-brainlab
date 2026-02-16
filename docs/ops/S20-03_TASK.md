# S20-03 Task — Eval Wall v1 impl (Ambi-chan CPU-safe)

## Progress
- [x] 0% Start
- [x] 10% Plan/Task frozen
- [x] 30% Dataset skeleton committed (repo)
- [x] 60% Run artifacts writer implemented (local)
- [x] 80% Taxonomy wiring + summary aggregation
- [x] 90% Gates pass + PR ready
- [ ] 100% PR merged

## C0: Worldline Lock (Lightweight)
- [/] `bash -lc 'cd "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || { echo "ERROR:not in repo"; return 1; }; git status -sb; git remote -v'`
- [/] `bash -lc 'cd "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || { echo "ERROR:not in repo"; return 1; }; git grep -nE "file:/{2}|/U[s]ers/" -- docs data eval || echo "OK: no forbidden patterns"'`
- [/] `bash -lc 'cd "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || { echo "ERROR:not in repo"; return 1; }; test -L data && echo "ERROR:data is symlink" || echo "OK:data is real dir"'`

## C1: Dataset (Lightweight)
- [/] `bash -lc 'cd "$(git rev-parse --show-toplevel)" || { echo "ERROR"; return 1; }; ls -la "data/eval/datasets/rag-eval-wall-v1__seed-mini__v0001/"'`
- [/] `bash -lc 'cd "$(git rev-parse --show-toplevel)" || { echo "ERROR"; return 1; }; git check-ignore -v "data/eval/datasets/rag-eval-wall-v1__seed-mini__v0001/" || echo "OK:not_ignored"'`
- [/] `bash -lc 'cd "$(git rev-parse --show-toplevel)" || { echo "ERROR"; return 1; }; git ls-files "data/eval/datasets/rag-eval-wall-v1__seed-mini__v0001/cases.jsonl" "data/eval/datasets/rag-eval-wall-v1__seed-mini__v0001/dataset.meta.json"'`

## C2: Artifacts Writer (Medium Load: 1 run only)
- [/] `bash -lc 'cd "$(git rev-parse --show-toplevel)" || { echo "ERROR"; return 1; }; mkdir -p .local ".local/rag_eval/runs"; nice -n 10 python3 eval/run_eval.py --mode record --provider mock --dataset "rag-eval-wall-v1__seed-mini__v0001" || echo "ERROR:run_eval failed"'`
- [/] `bash -lc 'cd "$(git rev-parse --show-toplevel)" || { echo "ERROR"; return 1; }; ls -1 ".local/rag_eval/runs" | tail -n 5'`
- [/] `bash -lc 'cd "$(git rev-parse --show-toplevel)" || { echo "ERROR"; return 1; }; RUN="$(ls -1t ".local/rag_eval/runs" | head -n 1)"; echo "RUN=$RUN"; ls -la ".local/rag_eval/runs/$RUN"; for f in run.meta.json results.jsonl summary.json; do test -f ".local/rag_eval/runs/$RUN/$f" && echo "OK:$f" || echo "ERROR:missing:$f"; done'`

## C3: Taxonomy (Lightweight)
- [/] `bash -lc 'cd "$(git rev-parse --show-toplevel)" || { echo "ERROR"; return 1; }; rg -n "UNKNOWN" eval/run_eval.py && echo "ERROR:UNKNOWN found" || echo "OK:no UNKNOWN"'`
- [/] `bash -lc 'cd "$(git rev-parse --show-toplevel)" || { echo "ERROR"; return 1; }; RUN="$(ls -1t ".local/rag_eval/runs" | head -n 1)"; python3 - <<PY
  import json,sys
  frozen=set(["DATASET_INVALID","FORMAT_INVALID","RETRIEVAL_EMPTY","RETRIEVAL_OFFTOPIC","ANSWER_UNSUPPORTED","CITATION_MISSING","REFUSAL_MISSING","REFUSAL_UNNECESSARY","INJECTION_SUCCEEDED","TIMEOUT","CRASH"])
  path=".local/rag_eval/runs/"+RUN+"/results.jsonl"
  try:
    for i,line in enumerate(open(path,"r",encoding="utf-8"),1):
      o=json.loads(line)
      st=o.get("status")
      if st not in ("PASS","FAIL","SKIP"):
        print("ERROR: invalid status line",i,st); break
      if st!="PASS":
        fc=o.get("failure_code")
        if fc not in frozen:
          print("ERROR: non-frozen failure_code line",i,fc); break
    else:
      print("OK: frozen failure_code only")
  except Exception as e:
    print("ERROR:", e)
  PY'`

## C4: Docs Coherence (Lightweight)
- [/] `bash -lc 'cd "$(git rev-parse --show-toplevel)" || { echo "ERROR"; return 1; }; rg -n "S20-03_PLAN.md" docs/ops/ROADMAP.md && echo "OK:ROADMAP" || echo "ERROR:ROADMAP missing"'`
- [/] `bash -lc 'cd "$(git rev-parse --show-toplevel)" || { echo "ERROR"; return 1; }; rg -n "User Review Required" docs/ops/S20-03_PLAN.md && echo "ERROR:PLAN not canonical" || echo "OK:PLAN canonical"'`

## C5: Gates (Heavy: 1 by 1)
- [/] (Heavy 1) `bash -lc 'cd "$(git rev-parse --show-toplevel)" || { echo "ERROR"; return 1; }; nice -n 10 env GOMAXPROCS=2 go test -p 1 ./... || echo "ERROR:go test failed"'`
- [/] (Light) `bash -lc 'cd "$(git rev-parse --show-toplevel)" || { echo "ERROR"; return 1; }; git status -sb'`
- [/] (Heavy 2) `bash -lc 'cd "$(git rev-parse --show-toplevel)" || { echo "ERROR"; return 1; }; mkdir -p .local; nice -n 10 env GOMAXPROCS=2 go run cmd/reviewpack/main.go submit --mode verify-only 2>&1 | tee .local/s20-03_reviewpack_verify_only.log'`

## C6: Commit/PR (Lightweight)
- [/] `bash -lc 'cd "$(git rev-parse --show-toplevel)" || { echo "ERROR"; return 1; }; git status -sb; git diff --stat'`
- [/] `bash -lc 'cd "$(git rev-parse --show-toplevel)" || { echo "ERROR"; return 1; }; git add eval/run_eval.py .gitignore docs/ops/S20-03_PLAN.md docs/ops/S20-03_TASK.md docs/ops/ROADMAP.md "data/eval/datasets/rag-eval-wall-v1__seed-mini__v0001/cases.jsonl" "data/eval/datasets/rag-eval-wall-v1__seed-mini__v0001/dataset.meta.json"; git commit -m "feat(rag-eval): eval wall v1 dataset + artifacts + taxonomy (S20-03)" || echo "WARN:commit failed"'`
- [ ] `bash -lc 'cd "$(git rev-parse --show-toplevel)" || { echo "ERROR"; return 1; }; git push -u origin HEAD || echo "WARN:push failed"'`
- [ ] `bash -lc 'cd "$(git rev-parse --show-toplevel)" || { echo "ERROR"; return 1; }; (test -f ops/pr_create.sh && ./ops/pr_create.sh || gh pr create --fill) || echo "WARN:pr create failed"'`
