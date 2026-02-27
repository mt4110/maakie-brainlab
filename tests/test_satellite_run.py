import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from satellite.run import run_pipeline


class SatelliteRunTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        self.source = "test_src"
        self.date = "2026-02-27"

        (self.root / "satellite/sources").mkdir(parents=True, exist_ok=True)
        (self.root / "satellite/rules").mkdir(parents=True, exist_ok=True)
        (self.root / f"satellite/prompts/{self.source}").mkdir(parents=True, exist_ok=True)
        (self.root / "src").mkdir(parents=True, exist_ok=True)

        (self.root / f"satellite/sources/{self.source}.toml").write_text(
            "url='https://example.com/rss.xml'\n", encoding="utf-8"
        )
        (self.root / f"satellite/rules/{self.source}.toml").write_text(
            """
[allowlist]
keywords=["AI","LLM"]
[denylist]
keywords=["Sponsored"]
[constraints]
min_chars=1
require_japanese=false
""".strip()
            + "\n",
            encoding="utf-8",
        )
        (self.root / f"satellite/prompts/{self.source}/v1.txt").write_text("prompt\n", encoding="utf-8")

        repo_root = Path(__file__).resolve().parents[1]
        (self.root / "src/build_index.py").write_text(
            (repo_root / "src/build_index.py").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        self.feed_bytes = (repo_root / "tests/fixtures/rss_sample.xml").read_bytes()

    def tearDown(self):
        self.td.cleanup()

    def test_run_pipeline_end_to_end(self):
        with patch("satellite.collect.Collector.fetch_feed", return_value=self.feed_bytes):
            out = run_pipeline(self.source, self.date, self.root, chunk_size=128, overlap=32)

        steps = out["steps"]
        self.assertTrue(steps["manifest_verify"]["ok"])
        self.assertGreaterEqual(steps["gate"]["total"], 1)
        self.assertTrue((self.root / f"data/satellite/{self.source}/digest/{self.date}.md").exists())
        self.assertTrue((self.root / f"data/satellite/{self.source}/index/index.sqlite3").exists())

    @patch("satellite.run.verify_manifest", return_value={"ok": False, "error_count": 2, "errors": ["e1", "e2"]})
    @patch("satellite.run.Collector.run", return_value=None)
    def test_run_pipeline_manifest_failure_includes_errors(self, _mock_collect, _mock_verify):
        with self.assertRaises(RuntimeError) as ctx:
            run_pipeline(self.source, self.date, self.root, chunk_size=128, overlap=32)
        msg = str(ctx.exception)
        self.assertIn("error_count=2", msg)
        self.assertIn("e1", msg)


if __name__ == "__main__":
    unittest.main()
