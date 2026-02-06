import hashlib
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List

# Define required file paths template for config_sha
# These are relative to the project root (or wherever the script is run from)
CONFIG_PATTERNS = [
    "satellite/sources/{id}.toml",
    "satellite/rules/{id}.toml",
    # "satellite/prompts/{id}/v1.txt", # Allow v*.txt wildcards or fixed v1? User said v1.txt or v*.txt.
    # Instruction says: "satellite/prompts/<source_id>/v1.txt" (S4.1 placeholder ok)
    "satellite/prompts/{id}/v1.txt", 
]

def generate_run_id(
    date_str: str,
    source_id: str,
    config_sha: str,
    code_version: str
) -> str:
    """
    Generate a deterministic SHA256 run_id.
    Input strings are concatenated with a delimiter.
    """
    payload = f"{date_str}|{source_id}|{config_sha}|{code_version}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_config_sha(source_id: str, project_root: Path) -> str:
    r"""
    Compute config_sha based on Policy A.
    Reads source def, rules, and prompt. 
    Files must exist. 
    Calculation: Concatenate sorted(path + '\n' + bytes + '\n').
    """
    sha = hashlib.sha256()
    
    # Resolve target paths
    target_files: List[Path] = []
    
    # 1. Expand patterns
    for pattern in CONFIG_PATTERNS:
        rel_path_str = pattern.format(id=source_id)
        full_path = project_root / rel_path_str
        if not full_path.exists():
            raise FileNotFoundError(f"Missing required config file for config_sha: {rel_path_str}")
        target_files.append(full_path)
    
    # 2. Sort by path (Policy A) - using relative path string for sorting to be stable across machines
    # But for calculation we use the content.
    # The requirement says: "Concatenate path + \n + file_bytes + \n"
    # We will use the relative path string as the "path" part of the hash payload.
    target_files.sort(key=lambda p: str(p.relative_to(project_root)))

    for fpath in target_files:
        rel_path = str(fpath.relative_to(project_root))
        content = fpath.read_bytes()
        
        # Payload structure: relative_path + newline + content + newline
        # Using separate updates to avoid massive memory usage for large files (though configs are small)
        sha.update(rel_path.encode("utf-8"))
        sha.update(b"\n")
        sha.update(content)
        sha.update(b"\n")

    return sha.hexdigest()


def save_manifest(path: Path, data: Dict[str, Any]) -> None:
    """
    Save manifest data to a file atomically with stable JSON formatting.
    Enforces Policy B: Strict Schema and Sorting.
    """
    # Policy B: Validate Schema
    required_fields = {"run_id", "date", "source_id", "config_sha", "code_version", "artifacts"}
    if not required_fields.issubset(data.keys()):
        missing = required_fields - data.keys()
        raise ValueError(f"Manifest missing required fields: {missing}")

    # Policy B: Sort artifacts by path
    if "artifacts" in data and isinstance(data["artifacts"], list):
        # We assume artifacts are dicts with "path" key
        # Sort in place or create new list
        data["artifacts"] = sorted(data["artifacts"], key=lambda x: x.get("path", ""))

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as tmp:
        # Policy B: keys sorted (sort_keys=True)
        json.dump(data, tmp, sort_keys=True, indent=2, ensure_ascii=False)
        tmp.write("\n")
        tmp_path = Path(tmp.name)

    try:
        tmp_path.replace(path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise

