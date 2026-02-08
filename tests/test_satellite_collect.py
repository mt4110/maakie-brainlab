import json
import sys
import unittest
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import feedparser

# Fix import path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from satellite.collect import Collector, compute_raw_uid  # noqa: E402

class TestSatelliteCollect(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.test_dir.name)
        
        # Setup foundation structure
        (self.root / "satellite/sources").mkdir(parents=True)
        (self.root / "satellite/rules").mkdir(parents=True)
        (self.root / "satellite/prompts/test_src").mkdir(parents=True)
        
        self.source_id = "test_src"
        self.source_config = self.root / f"satellite/sources/{self.source_id}.toml"
        with open(self.source_config, "w") as f:
            f.write("url = 'https://example.com/rss'\n")
            
        # Create dummy rule/prompt for config_sha (manifest requirement)
        (self.root / f"satellite/rules/{self.source_id}.toml").touch()
        (self.root / f"satellite/prompts/{self.source_id}/v1.txt").touch()

    def tearDown(self):
        self.test_dir.cleanup()

    def test_compute_raw_uid_deterministic(self):
        """Test that raw_uid is stable."""
        uid1 = compute_raw_uid("src1", "http://example.com/1")
        uid2 = compute_raw_uid("src1", "http://example.com/1")
        self.assertEqual(uid1, uid2)
        
        uid3 = compute_raw_uid("src1", "http://example.com/2")
        self.assertNotEqual(uid1, uid3)

    @patch("satellite.collect.Collector.fetch_feed")
    def test_collector_run_with_fixture(self, mock_fetch):
        """Test full run using local fixture (no network)."""
        # Load fixture content
        fixture_path = ROOT / "tests/fixtures/rss_sample.xml"
        if not fixture_path.exists():
            self.skipTest("Fixture not found")
            
        # Mock feedparser response
        # We parse the fixture using real feedparser to simulate real object structure
        feed_obj = feedparser.parse(fixture_path.read_text())
        mock_fetch.return_value = feed_obj
        
        date = "2023-10-06"
        col = Collector(self.source_id, date, self.root)
        col.run()
        
        # Verify RAW output
        raw_dir = self.root / f"data/satellite/{self.source_id}/raw/{date}"
        self.assertTrue(raw_dir.exists())
        
        files = list(raw_dir.glob("*.json"))
        self.assertEqual(len(files), 2) # 2 items in fixture
        
        # Verify Manifest
        manifest_path = self.root / f"data/satellite/{self.source_id}/manifests/{date}.manifest.json"
        self.assertTrue(manifest_path.exists())
        
        with open(manifest_path, "rb") as f:
            manifest = json.load(f)
            
        self.assertEqual(manifest["source_id"], self.source_id)
        self.assertEqual(len(manifest["artifacts"]), 2)
        
        # Verify artifact sorting (Policy B check implicitly via manifest util, but explicit check here)
        paths = [a["path"] for a in manifest["artifacts"]]
        self.assertEqual(paths, sorted(paths))

    @patch("satellite.collect.datetime")
    @patch("satellite.collect.Collector.fetch_feed")
    def test_collector_idempotency(self, mock_fetch, mock_dt):
        """Test that running twice produces identical state (no phantom duplicates)."""
        fixture_path = ROOT / "tests/fixtures/rss_sample.xml"
        if not fixture_path.exists():
            self.skipTest("Fixture not found")
        
        # Mock datetime to ensure fetched_at is constant
        mock_now = datetime(2023, 10, 6, 12, 0, 0)
        mock_dt.utcnow.return_value = mock_now
        mock_dt.now.return_value = mock_now

        mock_dt.isoformat.return_value = "2023-10-06T12:00:00"

        feed_obj = feedparser.parse(fixture_path.read_text())
        mock_fetch.return_value = feed_obj
        
        date = "2023-10-06"
        col = Collector(self.source_id, date, self.root)
        
        # Run 1
        col.run()
        manifest1_path = self.root / f"data/satellite/{self.source_id}/manifests/{date}.manifest.json"
        with open(manifest1_path, "rb") as f:
            m1 = f.read()
            
        # Run 2
        col.run()
        
        # Verify Raw File Count (Should still be 2)
        raw_dir = self.root / f"data/satellite/{self.source_id}/raw/{date}"
        files = list(raw_dir.glob("*.json"))
        self.assertEqual(len(files), 2, "Raw files should not multiply on re-run")
        
        # Verify Manifest Identity
        with open(manifest1_path, "rb") as f:
            m2 = f.read()
            
        self.assertEqual(m1, m2, "Manifest should be byte-identical after re-run")

if __name__ == "__main__":
    unittest.main()
