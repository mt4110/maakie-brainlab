import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestS31PolicyDriftGuard(unittest.TestCase):
    def test_missing_baseline_key_is_drift(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "ops" / "s31_policy_drift_guard.py"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out_dir = tmp_path / "evidence"
            baseline = tmp_path / "policy_drift_baseline.json"

            first = subprocess.run(
                ["python3", str(script), "--out-dir", str(out_dir), "--baseline", str(baseline)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(first.returncode, 0)
            self.assertTrue(baseline.exists())

            baseline_obj = json.loads(baseline.read_text(encoding="utf-8"))
            hashes = dict(baseline_obj.get("hashes", {}))
            self.assertTrue(hashes)
            removed_key = sorted(hashes.keys())[0]
            hashes.pop(removed_key)
            baseline_obj["hashes"] = hashes
            baseline.write_text(json.dumps(baseline_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            second = subprocess.run(
                ["python3", str(script), "--out-dir", str(out_dir), "--baseline", str(baseline)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            out = (second.stdout or "") + (second.stderr or "")
            self.assertEqual(second.returncode, 1)
            self.assertIn("status=WARN", out)

            report = json.loads((out_dir / "policy_drift_guard_latest.json").read_text(encoding="utf-8"))
            self.assertEqual(report.get("status"), "WARN")
            self.assertIn(removed_key, report.get("changed", []))


if __name__ == "__main__":
    unittest.main()
