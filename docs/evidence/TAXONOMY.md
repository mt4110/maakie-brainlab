# Evidence Taxonomy

## Kind
The `kind` field in generic metadata describes the type of evidence.

### Format
Regex: `^[a-z][a-z0-9_]{0,31}$`

### Examples
- `prverify`: Result of a PR verification run.
- `review_bundle`: Bundle of code/docs for review.
- `security_scan`: Output from a security scanner.
- `eval`: Evaluation results.

*Note: The list of kinds is NOT fixed in the contract. New kinds can be added without changing the tool.*

## Tags
To distinguish variations within a `kind`, use the `tags` field in `METADATA.json`.

```json
"tags": ["ci", "release-blocker"]
```

## Extensions
For kind-specific metadata that doesn't fit into the flat key-value pairs, use the `extensions` object in `METADATA.json`.

```json
"extensions": {
  "prverify": {
    "pr_number": 123,
    "result": "pass"
  }
}
```
