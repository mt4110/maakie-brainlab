import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from satellite.store import store_day


class SatelliteStoreTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        self.source = "test_src"
        self.date = "2026-02-27"

        (self.root / f"data/satellite/{self.source}/norm").mkdir(parents=True, exist_ok=True)
        (self.root / f"data/satellite/{self.source}/decisions").mkdir(parents=True, exist_ok=True)

        self.norm_path = self.root / f"data/satellite/{self.source}/norm/{self.date}.jsonl"
        self.decisions_path = self.root / f"data/satellite/{self.source}/decisions/{self.date}.jsonl"

        norm_rows = [
            {
                "il": {
                    "uid": "uid-1",
                    "canonical_url": "https://example.com/1",
                    "title": "T1",
                    "text": "A" * 20,
                    "raw_ref": "raw/1.json",
                    "raw_sha256": "sha1",
                }
            },
            {
                "il": {
                    "uid": "uid-2",
                    "canonical_url": "https://example.com/2",
                    "title": "T2",
                    "text": "B" * 20,
                    "raw_ref": "raw/2.json",
                    "raw_sha256": "sha2",
                }
            },
        ]
        with self.norm_path.open("w", encoding="utf-8") as f:
            for row in norm_rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def tearDown(self):
        self.td.cleanup()

    def _write_decisions(self, decision_for_uid2: str) -> None:
        rows = [
            {"uid": "uid-1", "decision": "KEEP", "reason_code": "RULE_PASS"},
            {"uid": "uid-2", "decision": decision_for_uid2, "reason_code": "ALLOWLIST_MISS"},
        ]
        with self.decisions_path.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def test_store_upsert_is_idempotent(self):
        self._write_decisions("UNKNOWN")
        summary1 = store_day(self.source, self.date, self.root)
        self.assertEqual(summary1["upserted"], 2)

        self._write_decisions("KEEP")
        summary2 = store_day(self.source, self.date, self.root)
        self.assertEqual(summary2["upserted"], 2)
        self.assertEqual(summary2["counts"]["KEEP"], 2)

        db_path = self.root / "data/satellite/satellite.sqlite3"
        conn = sqlite3.connect(str(db_path))
        try:
            total = conn.execute("SELECT COUNT(*) FROM sat_items").fetchone()[0]
            self.assertEqual(total, 2)
            row = conn.execute("SELECT decision FROM sat_items WHERE uid='uid-2'").fetchone()
            self.assertEqual(row[0], "KEEP")
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
