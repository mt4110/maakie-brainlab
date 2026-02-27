import json
import tempfile
import unittest
from pathlib import Path

from satellite.digest import build_digest
from satellite.index import build_index_for_source


class SatelliteDigestIndexTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        self.source = "test_src"
        self.date = "2026-02-27"

        (self.root / f"data/satellite/{self.source}/norm").mkdir(parents=True, exist_ok=True)
        (self.root / f"data/satellite/{self.source}/decisions").mkdir(parents=True, exist_ok=True)
        (self.root / "src").mkdir(parents=True, exist_ok=True)

        # build_index.py is required by satellite.index module; copy from repository source.
        repo_root = Path(__file__).resolve().parents[1]
        (self.root / "src/build_index.py").write_text(
            (repo_root / "src/build_index.py").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        norm_rows = [
            {
                "il": {
                    "uid": "uid-1",
                    "canonical_url": "https://example.com/1",
                    "title": "AI update",
                    "text": "Alpha beta gamma.",
                    "raw_ref": "raw/1.json",
                }
            },
            {
                "il": {
                    "uid": "uid-2",
                    "canonical_url": "https://example.com/2",
                    "title": "General",
                    "text": "No keep content.",
                    "raw_ref": "raw/2.json",
                }
            },
        ]
        decisions = [
            {"uid": "uid-1", "decision": "KEEP", "reason_code": "RULE_PASS"},
            {"uid": "uid-2", "decision": "UNKNOWN", "reason_code": "ALLOWLIST_MISS"},
        ]

        norm_path = self.root / f"data/satellite/{self.source}/norm/{self.date}.jsonl"
        with norm_path.open("w", encoding="utf-8") as f:
            for row in norm_rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        decisions_path = self.root / f"data/satellite/{self.source}/decisions/{self.date}.jsonl"
        with decisions_path.open("w", encoding="utf-8") as f:
            for row in decisions:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def tearDown(self):
        self.td.cleanup()

    def test_digest_and_index(self):
        digest_summary = build_digest(self.source, self.date, self.root)
        self.assertEqual(digest_summary["counts"]["KEEP"], 1)

        digest_md = self.root / f"data/satellite/{self.source}/digest/{self.date}.md"
        self.assertTrue(digest_md.exists())
        self.assertIn("uid=`uid-1`", digest_md.read_text(encoding="utf-8"))

        index_summary = build_index_for_source(self.source, self.date, self.root, chunk_size=128, overlap=32)
        db_rel = index_summary["index"]["db"]
        db_path = self.root / db_rel
        self.assertTrue(db_path.exists())
        self.assertEqual(int(index_summary["index"]["doc_count"]), 1)

    def test_index_targets_only_requested_digest_date(self):
        build_digest(self.source, self.date, self.root)
        digest_dir = self.root / f"data/satellite/{self.source}/digest"
        (digest_dir / "2026-02-26.md").write_text("# old\nlegacy content\n", encoding="utf-8")

        index_summary = build_index_for_source(self.source, self.date, self.root, chunk_size=128, overlap=32)
        self.assertEqual(int(index_summary["index"]["doc_count"]), 1)


if __name__ == "__main__":
    unittest.main()
