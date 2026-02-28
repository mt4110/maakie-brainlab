import json
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s32_policy_drift_guard_v2.py"
    spec = importlib.util.spec_from_file_location("s32_policy_drift_guard_v2", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestS32PolicyDriftGuardV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_diff_hashes_respects_tracked_argument(self):
        baseline = {"a.txt": "x", "b.txt": "y"}
        current = {"a.txt": "x", "b.txt": "y", "c.txt": "z"}
        diff = self.m.diff_hashes(baseline, current, ["c.txt"])
        self.assertEqual(diff.get("missing"), [])
        self.assertEqual(diff.get("changed"), ["c.txt"])

    def test_diff_hashes_marks_missing_when_tracked_file_absent_in_current(self):
        baseline = {"a.txt": "x"}
        current = {}
        diff = self.m.diff_hashes(baseline, current, ["a.txt"])
        self.assertEqual(diff.get("missing"), ["a.txt"])
        self.assertEqual(diff.get("changed"), [])

    def test_missing_baseline_key_is_drift(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "ops" / "s32_policy_drift_guard_v2.py"

        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            out_dir = tmp_path / "evidence"
            baseline = tmp_path / "policy_drift_baseline_v2.json"

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

            report = json.loads((out_dir / "policy_drift_guard_v2_latest.json").read_text(encoding="utf-8"))
            self.assertEqual(report.get("status"), "WARN")
            self.assertIn(removed_key, report.get("changed", []))


if __name__ == "__main__":
    unittest.main()
