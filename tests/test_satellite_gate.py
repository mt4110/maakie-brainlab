import json
import tempfile
import unittest
from pathlib import Path

from satellite.gate import run_gate


class SatelliteGateTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        self.source = "test_src"
        self.date = "2026-02-27"

        (self.root / f"satellite/rules").mkdir(parents=True, exist_ok=True)
        (self.root / f"data/satellite/{self.source}/norm").mkdir(parents=True, exist_ok=True)

        (self.root / f"satellite/rules/{self.source}.toml").write_text(
            """
[allowlist]
keywords=["AI"]
[denylist]
keywords=["Sponsored"]
[constraints]
min_chars=10
require_japanese=false
""".strip()
            + "\n",
            encoding="utf-8",
        )

        norm_path = self.root / f"data/satellite/{self.source}/norm/{self.date}.jsonl"
        rows = [
            {
                "il": {
                    "uid": "u-keep",
                    "canonical_url": "https://example.com/keep",
                    "title": "AI news",
                    "text": "This AI article has enough content.",
                    "raw_ref": "raw/a.json",
                }
            },
            {
                "il": {
                    "uid": "u-drop",
                    "canonical_url": "https://example.com/drop",
                    "title": "Sponsored content",
                    "text": "Sponsored post with enough length.",
                    "raw_ref": "raw/b.json",
                }
            },
            {
                "il": {
                    "uid": "u-unknown-allow",
                    "canonical_url": "https://example.com/unknown",
                    "title": "General update",
                    "text": "Nothing about required keywords here.",
                    "raw_ref": "raw/c.json",
                }
            },
            {
                "il": {
                    "uid": "u-unknown-empty",
                    "canonical_url": "https://example.com/empty",
                    "title": "AI title",
                    "text": "",
                    "raw_ref": "raw/d.json",
                }
            },
        ]
        with norm_path.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def tearDown(self):
        self.td.cleanup()

    def test_gate_decisions_and_idempotency(self):
        summary1 = run_gate(self.source, self.date, self.root)
        out_path = self.root / f"data/satellite/{self.source}/decisions/{self.date}.jsonl"
        first_bytes = out_path.read_bytes()

        self.assertEqual(summary1["counts"]["KEEP"], 1)
        self.assertEqual(summary1["counts"]["DROP"], 1)
        self.assertEqual(summary1["counts"]["UNKNOWN"], 2)

        rows = [json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        by_uid = {row["uid"]: row for row in rows}
        self.assertEqual(by_uid["u-keep"]["decision"], "KEEP")
        self.assertEqual(by_uid["u-drop"]["reason_code"], "DENYLIST_MATCH")
        self.assertEqual(by_uid["u-unknown-allow"]["reason_code"], "ALLOWLIST_MISS")
        self.assertEqual(by_uid["u-unknown-empty"]["reason_code"], "EXTRACTION_FAILED")

        run_gate(self.source, self.date, self.root)
        second_bytes = out_path.read_bytes()
        self.assertEqual(first_bytes, second_bytes)


if __name__ == "__main__":
    unittest.main()
