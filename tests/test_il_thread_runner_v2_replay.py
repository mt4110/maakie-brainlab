import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestILThreadRunnerV2Replay(unittest.TestCase):
    def test_replay_check_validate_only_ok(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "il_thread_runner_v2_replay_check.py"
        cases = repo_root / "tests" / "fixtures" / "il_thread_runner" / "cases_smoke.jsonl"

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "replay_out"
            cp = subprocess.run(
                [
                    "python3",
                    str(script),
                    "--cases",
                    str(cases),
                    "--out",
                    str(out_dir),
                    "--mode",
                    "validate-only",
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            output = (cp.stdout or "") + (cp.stderr or "")
            self.assertIn("OK: il_thread_runner_v2_replay_check exit=0", output)

            report_path = out_dir / "il.thread.replay.report.json"
            self.assertTrue(report_path.exists())
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report.get("schema"), "IL_THREAD_REPLAY_CHECK_v1")
            self.assertEqual(report.get("status"), "OK")
            self.assertTrue(report.get("match"))
            self.assertEqual(report.get("run1_stop"), 0)
            self.assertEqual(report.get("run2_stop"), 0)
            self.assertTrue(report.get("run1_sha256_cases_jsonl"))
            self.assertEqual(report.get("run1_sha256_cases_jsonl"), report.get("run2_sha256_cases_jsonl"))

    def test_replay_check_invalid_mode(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "il_thread_runner_v2_replay_check.py"
        cp = subprocess.run(
            ["python3", str(script), "--mode", "bad"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        output = (cp.stdout or "") + (cp.stderr or "")
        self.assertIn("invalid --mode", output)
        self.assertIn("ERROR: il_thread_runner_v2_replay_check exit=1", output)


if __name__ == "__main__":
    unittest.main()
