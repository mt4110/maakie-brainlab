import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def _load_module():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s27_reliability_soak.py"
    spec = importlib.util.spec_from_file_location("s27_reliability_soak", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S27ReliabilitySoakTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_longest_consecutive_status(self):
        rows = [{"status": "PASS"}, {"status": "FAIL"}, {"status": "FAIL"}, {"status": "PASS"}, {"status": "FAIL"}]
        self.assertEqual(self.m.longest_consecutive_status(rows, {"FAIL"}), 2)

    def test_parse_hour(self):
        self.assertEqual(self.m.parse_hour("2026-02-27T03:00:00Z"), 3)
        self.assertEqual(self.m.parse_hour(""), -1)

    def test_insufficient_runs_reason_not_overwritten_by_skip_rate(self):
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "out"
            hist = Path(td) / "history.json"
            hist.write_text(
                json.dumps({"runs": [{"captured_at_utc": "2026-02-27T03:00:00Z", "status": "SKIP"}]}),
                encoding="utf-8",
            )
            cp = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "scripts" / "ops" / "s27_reliability_soak.py"),
                    "--out-dir",
                    str(out_dir),
                    "--history-json",
                    str(hist),
                    "--min-runs",
                    "2",
                    "--skip-rate-warn-threshold",
                    "0.1",
                ],
                cwd=str(repo_root),
                env={**os.environ, "PYTHONPATH": "./src:."},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0)
            payload = json.loads((out_dir / "reliability_soak_latest.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["status"], "WARN")
            self.assertEqual(payload["summary"]["reason_code"], self.m.REASON_INSUFFICIENT_RUNS)


if __name__ == "__main__":
    unittest.main()
