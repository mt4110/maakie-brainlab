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
- [x] Verified clean state
- [x] Verified no forbidden patterns

### C1: Dataset (Lightweight)
- [x] Verified dataset dir string
- [x] Verified required files existence
- [x] Verified not ignored

### C2: Artifacts Writer (Medium Load - Throttled)
- [x] `run_eval.py` produces artifacts
- [x] `run_id` uses 7-char git sha (Patched)
- [x] `sys.exit` removed (Patched)

### C3: Taxonomy & Spec (Lightweight)
- [x] `UNKNOWN` removed from code/output (Patched)
- [x] `results.jsonl` contains only frozen codes

### C4: Docs Coherence (Lightweight)
- [x] Roadmap updated
- [x] Plan/Task canonical

### C5: Gates (Heavy - Throttled & Split)
- [x] `go test` PASS
- [x] `reviewpack` PASS

### C6: PR Readiness
- [x] PR Body generated
