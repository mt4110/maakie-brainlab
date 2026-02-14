import unittest
import json
import tempfile
import sys
from pathlib import Path


# Fix import path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from satellite.normalize import Normalizer  # noqa: E402

class TestSatelliteNormalize(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.test_dir.name)
        self.source_id = "test_src"
        self.date = "2023-10-06"
        
        # Setup directories
        self.raw_dir = self.root / f"data/satellite/{self.source_id}/raw/{self.date}"
        self.raw_dir.mkdir(parents=True)
        
        # Create Dummy Raw Files
        self.item1 = {
            "feed_entry": {
                "link": "http://example.com/1",
                "title": "Title 1",
                "summary": "Text 1",
                "published": "2023-10-06T12:00:00"
            },
            "fetched_at": "2023-10-06T12:00:00Z"
        }
        # UID for item1 -> sha256(test_src|http://example.com/1)
        # We'll save it as if Collect did it
        (self.raw_dir / "item1.json").write_text(json.dumps(self.item1))

        self.item2 = {
            "feed_entry": {
                "link": "http://example.com/2",
                "title": "Title 2",
                "summary": "Text 2"
            },
            "fetched_at": "2023-10-06T13:00:00Z"
        }
         # item2 has no published date, ensure it handles it
        (self.raw_dir / "item2.json").write_text(json.dumps(self.item2))

    def tearDown(self):
        self.test_dir.cleanup()

    def test_normalize_output_schema_and_sort(self):
        """Test IL schema fields and sorting by UID."""
        norm = Normalizer(self.source_id, self.date, self.root)
        norm.run()
        
        output_path = self.root / f"data/satellite/{self.source_id}/norm/{self.date}.jsonl"
        self.assertTrue(output_path.exists())
        
        lines = output_path.read_text("utf-8").strip().split("\n")
        self.assertEqual(len(lines), 2)
        
        items = [json.loads(line) for line in lines]
        
        # Check Sorting (UID ascending)
        self.assertLess(items[0]["il"]["uid"], items[1]["il"]["uid"])
        
        # Check Fields (Item 1)
        # Find item1 by link
        i1 = next(i for i in items if i["il"]["canonical_url"] == "http://example.com/1")
        self.assertEqual(i1["il"]["title"], "Title 1")
        self.assertEqual(i1["il"]["text"], "Text 1")
        self.assertEqual(i1["il"]["published_at"], "2023-10-06T12:00:00")
        self.assertTrue(i1["il"]["raw_ref"].endswith("item1.json"))
        
        # Check Fields (Item 2 - missing date)
        i2 = next(i for i in items if i["il"]["canonical_url"] == "http://example.com/2")
        self.assertNotIn("published_at", i2["il"])
        
        # Check Determinism (Run Again)
        norm.run()
        # Content should be identical
        lines2 = output_path.read_text("utf-8").strip().split("\n")
        self.assertEqual(lines, lines2)

    def test_skip_invalid_raw(self):
        """Test skipping invalid/empty raw files."""
        # Bad JSON
        (self.raw_dir / "bad.json").write_text("{bad json")
        # Missing Link
        (self.raw_dir / "no_link.json").write_text(json.dumps({"feed_entry": {}}))
        
        norm = Normalizer(self.source_id, self.date, self.root)
        norm.run()
        
        output_path = self.root / f"data/satellite/{self.source_id}/norm/{self.date}.jsonl"
        lines = output_path.read_text("utf-8").strip().split("\n")
        # Should still be 2 (valid ones), ignoring bad ones
        self.assertEqual(len(lines), 2)

if __name__ == "__main__":
    unittest.main()
