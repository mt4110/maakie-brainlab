import argparse
import json
import sqlite3
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


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sat_items (
            uid TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            date TEXT NOT NULL,
            canonical_url TEXT,
            title TEXT,
            text TEXT,
            raw_ref TEXT,
            raw_sha256 TEXT,
            decision TEXT NOT NULL,
            reason_code TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sat_items_source_date
        ON sat_items(source_id, date)
        """
    )


def store_day(source_id: str, date_str: str, project_root: Path) -> Dict[str, Any]:
    norm_path = project_root / f"data/satellite/{source_id}/norm/{date_str}.jsonl"
    decisions_path = project_root / f"data/satellite/{source_id}/decisions/{date_str}.jsonl"
    out_dir = project_root / f"data/satellite/{source_id}/store"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / f"{date_str}.json"

    norm_rows = _read_jsonl(norm_path)
    decision_rows = _read_jsonl(decisions_path)

    norm_by_uid: Dict[str, Dict[str, Any]] = {}
    for row in norm_rows:
        il = dict(row.get("il", {})) if isinstance(row, dict) else {}
        uid = str(il.get("uid") or "").strip()
        if uid:
            norm_by_uid[uid] = row

    decision_by_uid: Dict[str, Dict[str, Any]] = {}
    for row in decision_rows:
        uid = str(row.get("uid") or "").strip()
        if uid:
            decision_by_uid[uid] = row

    all_uids = sorted(set(norm_by_uid.keys()) | set(decision_by_uid.keys()))

    db_path = project_root / "data/satellite/satellite.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        _ensure_schema(conn)

        counts = {"KEEP": 0, "DROP": 0, "UNKNOWN": 0}
        for uid in all_uids:
            norm = norm_by_uid.get(uid, {})
            il = dict(norm.get("il", {})) if isinstance(norm, dict) else {}
            dec = decision_by_uid.get(uid, {})

            decision = str(dec.get("decision") or "UNKNOWN").upper().strip()
            if decision not in counts:
                decision = "UNKNOWN"
            reason_code = str(dec.get("reason_code") or "MISSING_DECISION").strip() or "MISSING_DECISION"
            counts[decision] += 1

            conn.execute(
                """
                INSERT INTO sat_items(
                    uid, source_id, date, canonical_url, title, text, raw_ref, raw_sha256, decision, reason_code
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(uid) DO UPDATE SET
                    source_id=excluded.source_id,
                    date=excluded.date,
                    canonical_url=excluded.canonical_url,
                    title=excluded.title,
                    text=excluded.text,
                    raw_ref=excluded.raw_ref,
                    raw_sha256=excluded.raw_sha256,
                    decision=excluded.decision,
                    reason_code=excluded.reason_code
                """,
                (
                    uid,
                    source_id,
                    date_str,
                    str(il.get("canonical_url") or dec.get("canonical_url") or ""),
                    str(il.get("title") or dec.get("title") or ""),
                    str(il.get("text") or ""),
                    str(il.get("raw_ref") or dec.get("raw_ref") or ""),
                    str(il.get("raw_sha256") or ""),
                    decision,
                    reason_code,
                ),
            )

        conn.commit()
    finally:
        conn.close()

    summary = {
        "source_id": source_id,
        "date": date_str,
        "norm_input": str(norm_path.relative_to(project_root)) if norm_path.exists() else "",
        "decisions_input": str(decisions_path.relative_to(project_root)) if decisions_path.exists() else "",
        "db": str(db_path.relative_to(project_root)),
        "upserted": len(all_uids),
        "counts": counts,
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Store satellite decisions to SQLite")
    parser.add_argument("source_id", help="Source ID")
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    summary = store_day(args.source_id, args.date, root)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
