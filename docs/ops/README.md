# Operations Documentation

## Testing Standard
All tests must be discoverable and runnable via the standard `unittest` command:
```bash
python3 -m unittest discover tests
```
Or via `make`:
```bash
make test
```

## Python Compatibility
- **Requirement**: Python 3.9+
- **Dependency**: `tomli` is required for Python < 3.11 (added via `requirements.txt`).
