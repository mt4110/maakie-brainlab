import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestILThreadRunnerV2Suite(unittest.TestCase):
    def test_suite_end_to_end_ok(self):
        repo_root = Path(__file__).resolve().parent.parent
        suite = repo_root / "scripts" / "il_thread_runner_v2_suite.py"
        cases = repo_root / "tests" / "fixtures" / "il_thread_runner" / "cases_smoke.jsonl"

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "suite_out"
            cp = subprocess.run(
                [
                    "python3",
                    str(suite),
                    "--cases",
                    str(cases),
                    "--out",
                    str(out_dir),
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            output = (cp.stdout or "") + (cp.stderr or "")
            self.assertEqual(cp.returncode, 0)
            self.assertIn("OK: il_thread_runner_v2_suite exit=0", output)

            summary_path = out_dir / "suite.summary.json"
            self.assertTrue(summary_path.exists())
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary.get("schema"), "IL_THREAD_V2_SUITE_v1")
            self.assertEqual(summary.get("status"), "OK")
            self.assertEqual(len(summary.get("steps", [])), 4)
            statuses = [s.get("status") for s in summary.get("steps", [])]
            self.assertTrue(all(st == "OK" for st in statuses))

    def test_suite_invalid_option(self):
        repo_root = Path(__file__).resolve().parent.parent
        suite = repo_root / "scripts" / "il_thread_runner_v2_suite.py"
        cp = subprocess.run(
            ["python3", str(suite), "--bad"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        output = (cp.stdout or "") + (cp.stderr or "")
        self.assertNotEqual(cp.returncode, 0)
        self.assertIn("unknown option", output)
        self.assertIn("ERROR: il_thread_runner_v2_suite exit=1", output)


if __name__ == "__main__":
    unittest.main()
