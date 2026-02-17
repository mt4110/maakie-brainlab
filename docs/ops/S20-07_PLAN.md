# S20-07 Python Compatibility Fix (tomli)

## Plan (Pseudocode)
```python
if python3 -V >= 3.11:
    print("OK: tomlib is stdlib")
else:
    try:
        import tomli
        print("OK: tomli found")
    except ImportError:
        print("ERROR: tomli missing (py<3.11 fallback needed)")
        print("HINT: add tomli to requirements/pyproject")
        STOP
```

## Audit Log
- **Context**: Python < 3.11 requires `tomli` as a backport for `tomllib`.
- **Action**: Explicitly adding `tomli` dependency to ensure compatibility.
