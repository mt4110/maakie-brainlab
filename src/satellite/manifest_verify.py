import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

from satellite.manifest import compute_config_sha, generate_run_id


REQUIRED_FIELDS = {"run_id", "date", "source_id", "config_sha", "code_version", "artifacts"}


def verify_manifest(source_id: str, date_str: str, project_root: Path) -> Dict[str, Any]:
    manifest_path = project_root / f"data/satellite/{source_id}/manifests/{date_str}.manifest.json"
    verify_path = project_root / f"data/satellite/{source_id}/manifests/{date_str}.verify.json"

    errors: List[str] = []
    payload: Dict[str, Any] = {}

    if not manifest_path.exists():
        errors.append(f"manifest missing: {manifest_path}")
    else:
        try:
            obj = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(obj, dict):
                payload = obj
            else:
                errors.append("manifest is not a JSON object")
        except Exception as exc:
            errors.append(f"manifest parse failed: {exc}")

    missing = sorted(REQUIRED_FIELDS - set(payload.keys())) if payload else sorted(REQUIRED_FIELDS)
    for key in missing:
        errors.append(f"manifest missing field: {key}")

    if payload:
        expected_source = str(payload.get("source_id") or "")
        expected_date = str(payload.get("date") or "")
        if expected_source != source_id:
            errors.append(f"source_id mismatch: {expected_source} != {source_id}")
        if expected_date != date_str:
            errors.append(f"date mismatch: {expected_date} != {date_str}")

        config_sha = str(payload.get("config_sha") or "")
        code_version = str(payload.get("code_version") or "")
        expected_run_id = generate_run_id(date_str, source_id, config_sha, code_version)
        if str(payload.get("run_id") or "") != expected_run_id:
            errors.append("run_id mismatch")

        try:
            recalculated = compute_config_sha(source_id, project_root)
            if config_sha and recalculated != config_sha:
                errors.append("config_sha mismatch")
        except Exception as exc:
            errors.append(f"config_sha check failed: {exc}")

        artifacts: List[Any] = []
        artifacts_value: Any = payload.get("artifacts")
        if not isinstance(artifacts_value, list):
            errors.append("artifacts is not a list")
        else:
            artifacts = artifacts_value

        artifact_items: List[Dict[str, Any]] = []
        for idx, row in enumerate(artifacts):
            if not isinstance(row, dict):
                errors.append(f"artifact entry is not an object: index={idx}")
                continue
            artifact_items.append(row)

        paths = [str(row.get("path") or "") for row in artifact_items]
        if paths != sorted(paths):
            errors.append("artifacts are not sorted by path")

        root_resolved = project_root.resolve()
        for item in artifact_items:
            rel = str(item.get("path") or "")
            if not rel:
                errors.append("artifact missing path")
                continue
            rel_path = Path(rel)
            if rel_path.is_absolute():
                errors.append(f"artifact path must be relative: {rel}")
                continue
            file_path = (project_root / rel_path).resolve()
            if root_resolved not in file_path.parents:
                errors.append(f"artifact path escapes project root: {rel}")
                continue
            if not file_path.exists():
                errors.append(f"artifact missing file: {rel}")
                continue
            blob = file_path.read_bytes()
            actual_sha = hashlib.sha256(blob).hexdigest()
            if str(item.get("sha256") or "") != actual_sha:
                errors.append(f"artifact sha mismatch: {rel}")
            try:
                expected_bytes = int(item.get("bytes", -1) or -1)
            except Exception:
                errors.append(f"artifact bytes invalid: {rel}")
                continue
            if expected_bytes != len(blob):
                errors.append(f"artifact size mismatch: {rel}")

    result = {
        "source_id": source_id,
        "date": date_str,
        "manifest": str(manifest_path.relative_to(project_root)),
        "ok": len(errors) == 0,
        "error_count": len(errors),
        "errors": errors,
    }
    verify_path.parent.mkdir(parents=True, exist_ok=True)
    verify_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify satellite manifest integrity")
    parser.add_argument("source_id", help="Source ID")
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    out = verify_manifest(args.source_id, args.date, root)
    print(json.dumps(out, ensure_ascii=False, sort_keys=True))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
