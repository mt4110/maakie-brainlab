import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            obj = json.loads(text)
        except Exception:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def build_digest(source_id: str, date_str: str, project_root: Path) -> Dict[str, Any]:
    norm_path = project_root / f"data/satellite/{source_id}/norm/{date_str}.jsonl"
    decisions_path = project_root / f"data/satellite/{source_id}/decisions/{date_str}.jsonl"
    out_dir = project_root / f"data/satellite/{source_id}/digest"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / f"{date_str}.json"
    out_md = out_dir / f"{date_str}.md"

    norm_rows = _read_jsonl(norm_path)
    decision_rows = _read_jsonl(decisions_path)

    norm_by_uid: Dict[str, Dict[str, Any]] = {}
    for row in norm_rows:
        il = dict(row.get("il", {})) if isinstance(row, dict) else {}
        uid = str(il.get("uid") or "").strip()
        if uid:
            norm_by_uid[uid] = row

    items: List[Dict[str, Any]] = []
    for row in decision_rows:
        uid = str(row.get("uid") or "").strip()
        if not uid:
            continue
        il = dict(norm_by_uid.get(uid, {}).get("il", {}))
        decision = str(row.get("decision") or "UNKNOWN").upper().strip()
        if decision not in {"KEEP", "DROP", "UNKNOWN"}:
            decision = "UNKNOWN"
        item = {
            "uid": uid,
            "decision": decision,
            "reason_code": str(row.get("reason_code") or "UNKNOWN"),
            "title": str(il.get("title") or row.get("title") or ""),
            "canonical_url": str(il.get("canonical_url") or row.get("canonical_url") or ""),
            "raw_ref": str(il.get("raw_ref") or row.get("raw_ref") or ""),
        }
        items.append(item)

    order = {"KEEP": 0, "UNKNOWN": 1, "DROP": 2}
    items.sort(key=lambda r: (order.get(str(r.get("decision")), 9), str(r.get("uid"))))

    counts = {"KEEP": 0, "DROP": 0, "UNKNOWN": 0}
    unknown_reasons: Dict[str, int] = {}
    for row in items:
        dec = str(row.get("decision") or "UNKNOWN")
        if dec not in counts:
            dec = "UNKNOWN"
        counts[dec] += 1
        if dec == "UNKNOWN":
            reason = str(row.get("reason_code") or "UNKNOWN")
            unknown_reasons[reason] = int(unknown_reasons.get(reason, 0)) + 1

    payload = {
        "source_id": source_id,
        "date": date_str,
        "inputs": {
            "norm_jsonl": str(norm_path.relative_to(project_root)) if norm_path.exists() else "",
            "decisions_jsonl": str(decisions_path.relative_to(project_root)) if decisions_path.exists() else "",
        },
        "counts": counts,
        "unknown_reason_counts": dict(sorted(unknown_reasons.items())),
        "items": items,
    }

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=out_json.parent, delete=False) as tf:
        tf.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        tmp = Path(tf.name)
    tmp.replace(out_json)

    lines: List[str] = []
    lines.append(f"# Satellite Digest {source_id} {date_str}")
    lines.append("")
    lines.append(f"- KEEP: `{counts['KEEP']}`")
    lines.append(f"- UNKNOWN: `{counts['UNKNOWN']}`")
    lines.append(f"- DROP: `{counts['DROP']}`")
    lines.append("")

    if unknown_reasons:
        lines.append("## UNKNOWN by reason")
        lines.append("")
        for reason, value in sorted(unknown_reasons.items()):
            lines.append(f"- {reason}: {value}")
        lines.append("")

    lines.append("## Items")
    lines.append("")
    for row in items:
        uid = str(row.get("uid") or "")
        dec = str(row.get("decision") or "UNKNOWN")
        reason = str(row.get("reason_code") or "UNKNOWN")
        title = str(row.get("title") or "")
        url = str(row.get("canonical_url") or "")
        if url:
            lines.append(f"- [{dec}] uid=`{uid}` reason=`{reason}` title={title} url={url}")
        else:
            lines.append(f"- [{dec}] uid=`{uid}` reason=`{reason}` title={title}")

    out_md.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    summary = {
        "source_id": source_id,
        "date": date_str,
        "digest_json": str(out_json.relative_to(project_root)),
        "digest_md": str(out_md.relative_to(project_root)),
        "counts": counts,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Build daily satellite digest")
    parser.add_argument("source_id", help="Source ID")
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    summary = build_digest(args.source_id, args.date, root)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
