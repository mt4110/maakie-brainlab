import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestS31CompileBenchDiff(unittest.TestCase):
    def test_bench_diff_ok(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "il_compile_bench_diff.py"

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            baseline = tmp_path / "baseline.json"
            candidate = tmp_path / "candidate.json"
            out = tmp_path / "diff.json"

            baseline.write_text(
                json.dumps(
                    {
                        "expected_match_rate": 0.9,
                        "reproducible_rate": 1.0,
                        "fallback_rate": 0.2,
                        "objective_score": 0.7,
                    }
                ),
                encoding="utf-8",
            )
            candidate.write_text(
                json.dumps(
                    {
                        "expected_match_rate": 0.92,
                        "reproducible_rate": 1.0,
                        "fallback_rate": 0.15,
                        "objective_score": 0.75,
                    }
                ),
                encoding="utf-8",
            )

            cp = subprocess.run(
                [
                    "python3",
                    str(script),
                    "--baseline",
                    str(baseline),
                    "--candidate",
                    str(candidate),
                    "--out",
                    str(out),
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("schema"), "IL_COMPILE_BENCH_DIFF_v1")
            self.assertEqual(payload.get("status"), "OK")


if __name__ == "__main__":
    unittest.main()
