import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib


VALID_DECISIONS = {"KEEP", "DROP", "UNKNOWN"}


def _contains_japanese(text: str) -> bool:
    for ch in text:
        code = ord(ch)
        if 0x3040 <= code <= 0x30FF:
            return True
        if 0x4E00 <= code <= 0x9FFF:
            return True
    return False


def _load_rules(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as f:
        raw = tomllib.load(f)
    if isinstance(raw, dict):
        return raw
    return {}


def _keyword_match(haystack: str, keywords: List[str]) -> Tuple[bool, str]:
    if not keywords:
        return False, ""
    text = haystack.lower()
    for kw in keywords:
        token = str(kw or "").strip()
        if not token:
            continue
        if token.lower() in text:
            return True, token
    return False, ""


def _fallback_uid(source_id: str, date_str: str, line_no: int, raw_line: str) -> str:
    payload = f"{source_id}|{date_str}|{line_no}|{raw_line}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def decide_row(row: Dict[str, Any], *, source_id: str, date_str: str, rules: Dict[str, Any], line_no: int) -> Dict[str, Any]:
    il = dict(row.get("il", {})) if isinstance(row, dict) else {}
    uid = str(il.get("uid") or "").strip()
    canonical_url = str(il.get("canonical_url") or "").strip()
    title = str(il.get("title") or "").strip()
    text = str(il.get("text") or "").strip()

    allow = list(dict(rules.get("allowlist", {})).get("keywords", []) or [])
    deny = list(dict(rules.get("denylist", {})).get("keywords", []) or [])
    constraints = dict(rules.get("constraints", {}))
    min_chars = int(constraints.get("min_chars", 0) or 0)
    require_japanese = bool(constraints.get("require_japanese", False))

    if not uid:
        serialized = json.dumps(row, ensure_ascii=False, sort_keys=True)
        uid = _fallback_uid(source_id, date_str, line_no, serialized)

    out = {
        "uid": uid,
        "source_id": source_id,
        "date": date_str,
        "decision": "UNKNOWN",
        "reason_code": "FORMAT_INVALID",
        "canonical_url": canonical_url,
        "title": title,
        "raw_ref": str(il.get("raw_ref") or ""),
        "stage": "gate-1",
    }

    if not canonical_url:
        return out

    if not text:
        out["reason_code"] = "EXTRACTION_FAILED"
        return out

    merged_text = f"{title}\n{text}" if title else text

    if require_japanese and not _contains_japanese(merged_text):
        out["reason_code"] = "LANGUAGE_MISMATCH"
        return out

    deny_hit, deny_kw = _keyword_match(merged_text, deny)
    if deny_hit:
        out["decision"] = "DROP"
        out["reason_code"] = "DENYLIST_MATCH"
        out["matched_keyword"] = deny_kw
        return out

    if min_chars > 0 and len(text) < min_chars:
        out["decision"] = "DROP"
        out["reason_code"] = "TOO_SHORT"
        return out

    allow_hit, allow_kw = _keyword_match(merged_text, allow)
    if allow and not allow_hit:
        out["reason_code"] = "ALLOWLIST_MISS"
        return out

    out["decision"] = "KEEP"
    out["reason_code"] = "RULE_PASS"
    if allow_hit and allow_kw:
        out["matched_keyword"] = allow_kw
    return out


def run_gate(source_id: str, date_str: str, project_root: Path) -> Dict[str, Any]:
    norm_path = project_root / f"data/satellite/{source_id}/norm/{date_str}.jsonl"
    rules_path = project_root / f"satellite/rules/{source_id}.toml"
    out_dir = project_root / f"data/satellite/{source_id}/decisions"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{date_str}.jsonl"
    summary_path = out_dir / f"{date_str}.summary.json"

    if not norm_path.exists():
        raise FileNotFoundError(f"normalize output not found: {norm_path}")

    rules = _load_rules(rules_path)
    rows: List[Dict[str, Any]] = []

    for idx, raw in enumerate(norm_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError("row must be object")
        except Exception:
            fallback = {
                "uid": _fallback_uid(source_id, date_str, idx, line),
                "source_id": source_id,
                "date": date_str,
                "decision": "UNKNOWN",
                "reason_code": "FORMAT_INVALID",
                "canonical_url": "",
                "title": "",
                "raw_ref": "",
                "stage": "gate-1",
            }
            rows.append(fallback)
            continue
        rows.append(decide_row(obj, source_id=source_id, date_str=date_str, rules=rules, line_no=idx))

    rows.sort(key=lambda r: str(r.get("uid", "")))

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=out_path.parent, delete=False) as tf:
        for row in rows:
            if str(row.get("decision", "")) not in VALID_DECISIONS:
                row["decision"] = "UNKNOWN"
                row["reason_code"] = "FORMAT_INVALID"
            tf.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        tmp_path = Path(tf.name)
    tmp_path.replace(out_path)

    counts = {"KEEP": 0, "DROP": 0, "UNKNOWN": 0}
    reason_counts: Dict[str, int] = {}
    for row in rows:
        dec = str(row.get("decision") or "UNKNOWN")
        if dec not in counts:
            dec = "UNKNOWN"
        counts[dec] += 1
        reason = str(row.get("reason_code") or "UNKNOWN")
        reason_counts[reason] = int(reason_counts.get(reason, 0)) + 1

    summary = {
        "source_id": source_id,
        "date": date_str,
        "input": str(norm_path.relative_to(project_root)),
        "output": str(out_path.relative_to(project_root)),
        "rules": str(rules_path.relative_to(project_root)) if rules_path.exists() else "",
        "total": len(rows),
        "counts": counts,
        "reason_counts": dict(sorted(reason_counts.items())),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Satellite gate-1 rule decision")
    parser.add_argument("source_id", help="Source ID")
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    summary = run_gate(args.source_id, args.date, root)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
