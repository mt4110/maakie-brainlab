import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s32_reliability_soak_v3.py"
    spec = importlib.util.spec_from_file_location("s32_reliability_soak_v3", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestS32ReliabilitySoakV3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_evaluate_status_rules(self):
        warn = self.m._evaluate_status(total_runs=1, run_success_rate=1.0, timeout_rate=0.0, lock_conflict_rate=0.0)
        self.assertEqual(warn["status"], "WARN")
        self.assertEqual(warn["reason_code"], "INSUFFICIENT_SAMPLE")

        err = self.m._evaluate_status(total_runs=3, run_success_rate=0.5, timeout_rate=0.0, lock_conflict_rate=0.0)
        self.assertEqual(err["status"], "ERROR")

    def test_script_writes_artifacts(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "ops" / "s32_reliability_soak_v3.py"
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "evidence"
            cp = subprocess.run(
                ["python3", str(script), "--out-dir", str(out_dir), "--runs", "1"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            output = (cp.stdout or "") + (cp.stderr or "")
            self.assertEqual(cp.returncode, 1, msg=output)  # runs=1 => WARN
            payload = json.loads((out_dir / "reliability_soak_v3_latest.json").read_text(encoding="utf-8"))
            self.assertEqual(payload.get("schema"), "S32_RELIABILITY_SOAK_V3")
            self.assertIn("metrics", payload)
            self.assertTrue((out_dir / "reliability_soak_history_v3.json").exists())


if __name__ == "__main__":
    unittest.main()
