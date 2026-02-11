# Evidence Pack Contract v1

## Overview
This document defines **Evidence Pack Contract v1**.
The goal is to ensure long-term verifiability and safety of evidence packs, regardless of their content ("kind").

## 1. Fixed Structure
An Evidence Pack MUST be a single `.tar.gz` file.
The root directory MUST contain exactly these items:

| Path | Requirement | Description |
| :--- | :--- | :--- |
| `EVIDENCE_VERSION` | **Required** | Content MUST be exactly `v1\n`. |
| `METADATA.json` | **Required** | JSON object. Required keys MUST be present. Unknown keys allowed. |
| `MANIFEST.tsv` | **Required** | List of all files in `data/`. Format: `path<TAB>sha256<TAB>size`. |
| `CHECKSUMS.sha256` | **Required** | SHA256 sums of `EVIDENCE_VERSION`, `METADATA.json`, and `MANIFEST.tsv`. |
| `data/` | **Required** | Directory containing the actual evidence payload. |

### Constraints
- **Root Fixed**: No other files allowed in root.
- **Extensions**: All variable content MUST go into `data/`.
- **No Self-Reference**: `CHECKSUMS.sha256` MUST NOT contain its own checksum.

## 2. Verification Contract
The `verify` tool MUST enforce these rules. Any violation MUST result in failure.

### Safety Checks
- **No Absolute Paths**: All paths in the tar MUST be relative.
- **No Path Traversal**: Paths containing `..` are strictly PROHIBITED.
- **No Symlinks/Hardlinks**: The tar MUST NOT contain symbolic or hard links.

### Integrity Checks
- **Version Match**: `EVIDENCE_VERSION` content matches `v1\n`.
- **Root Checksums**: `CHECKSUMS.sha256` matches the actual content of the 3 root files.
- **Manifest Completeness (Mutual Exact Match)**:
    - Every file in `data/` MUST be listed in `MANIFEST.tsv`.
    - Every entry in `MANIFEST.tsv` MUST exist in `data/`.
    - File size and SHA256 content MUST match the manifest.

## 3. Metadata Schema (`METADATA.json`)
Required keys (must exist):
```json
{
  "contract": "evidence-pack-v1",
  "contract_version": 1,
  "created_at_utc": "YYYY-MM-DDTHH:MM:SSZ",
  "kind": "string",
  "git": {
    "sha": "string",
    "dirty": boolean
  },
  "payload_root": "data/",
  "tool": {
    "name": "evidencepack",
    "lang": "go"
  }
}
```
*Note: Additional keys (e.g., `tags`, `extensions`) are allowed and ignored by validation.*

## 4. Determinism (RunAlways)
To ensure reproducibility:
- **Tar Sort Order**: Files MUST be added in **lexicographic order**.
- **Tar Headers**:
    - `ModTime`: Fixed (e.g., 0 or `created_at_utc`).
    - `Uid/Gid`: Fixed to 0.
    - `Uname/Gname`: Empty or fixed.
- **Atomic Write**: Packs MUST be created in a staging area and moved atomically to the store.
