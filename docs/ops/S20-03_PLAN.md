# S20-03 Plan — Eval Wall v1 implementation (Ambi-chan Style)

## Strategy (Pseudo-code)

### Common: Error Handling (No Exit)
```python
def error(msg):
    print(f"ERROR: {msg}")
    return False # Stop current step, do not exit process

def skip(msg):
    print(f"SKIP: {msg}")
    return True # Continue
```

### C0: Worldline Lock (Lightweight)
```python
try:
    evidence = run("git status -sb && git remote -v")
    if "dirty" in evidence:
        error("dirty state: commit required")
    
    hits = run(FORBIDDEN_SCAN + " || true")
    if hits:
        error("forbidden patterns found")
except Exception as e:
    error(f"C0 failed: {e}")
```

### C1: Dataset (Lightweight)
```python
try:
    if not exists(DATASET_DIR):
        error(f"missing dataset dir: {DATASET_DIR}")
    
    for f in DATASET_REQUIRED:
        if not exists(f"{DATASET_DIR}/{f}"):
            error(f"missing dataset file: {f}")
    
    # Check ignore status
    if run(f"git check-ignore -v {DATASET_DIR}"):
        error("dataset is ignored")
except Exception as e:
    error(f"C1 failed: {e}")
```

### C2: Artifacts Writer (Medium Load - Throttled)
```python
try:
    # Run once, throttled
    run(f"nice -n 10 python3 eval/run_eval.py --mode record --provider mock --dataset {DATASET_ID}")
    
    latest = get_latest_run(RUNS_DIR)
    for f in RUN_REQUIRED:
        if not exists(f"{latest}/{f}"):
            error(f"missing artifact: {f}")
except Exception as e:
    error(f"C2 failed: {e}")
```

### C3: Taxonomy & Spec (Lightweight)
```python
try:
    # Spec violation check
    code = read("eval/run_eval.py")
    if "UNKNOWN" in code and not "FailureCode.UNKNOWN = None" in code:
        # UNKNOWN failure code is forbidden in output, allow code constant if mapped to None or unused
        # But strict rule says "UNKNOWN prohibited"
        if "FailureCode.UNKNOWN" in code:
             error("UNKNOWN detected. Must map to frozen codes only.")

    # Output check
    results = read_jsonl(f"{latest}/results.jsonl")
    frozen = {...} # EVAL_SPEC_v1 list
    for line in results:
        if line.status != "PASS" and line.failure_code not in frozen:
             error(f"non-frozen failure code: {line.failure_code}")

    # Git SHA length check
    if len(run_id_git_part) != 7:
        error("run_id git sha must be 7 chars")

except Exception as e:
    error(f"C3 failed: {e}")
```

### C4: Docs Coherence (Lightweight)
```python
try:
    roadmap = read("docs/ops/ROADMAP.md")
    if "S20-03_PLAN.md" not in roadmap:
        error("ROADMAP missing S20-03")
    
    task = read("docs/ops/S20-03_TASK.md")
    if "100%" in task and not is_pr_merged():
        error("TASK claims 100% but PR not merged")
except Exception as e:
    error(f"C4 failed: {e}")
```

### C5: Gates (Heavy - Throttled & Split)
```python
try:
    # Heavy 1
    if not run("nice -n 10 env GOMAXPROCS=2 go test -p 1 ./..."):
        error("go test failed")
    
    # Heavy 2
    if not run("nice -n 10 go run cmd/reviewpack/main.go submit --mode verify-only"):
        error("reviewpack verify failed")
except Exception as e:
    error(f"C5 failed: {e}")
```

### C6: PR Readiness
```python
try:
    body = generate_pr_body_template()
    write(".local/handoff/s20-03_pr.md", body)
    print("PR body generated. Ready for 'gh pr create'.")
except Exception as e:
    error(f"C6 failed: {e}")
```
