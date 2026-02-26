import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestILCompileBench(unittest.TestCase):
    def test_bench_rule_based_dataset(self):
        repo_root = Path(__file__).resolve().parent.parent
        bench_script = repo_root / "scripts" / "il_compile_bench.py"
        cases = repo_root / "tests" / "fixtures" / "il_compile" / "bench_cases.jsonl"

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "bench_out"
            cp = subprocess.run(
                [
                    "python3",
                    str(bench_script),
                    "--cases",
                    str(cases),
                    "--out",
                    str(out_dir),
                    "--provider",
                    "rule_based",
                    "--model",
                    "rule_based_v1",
                    "--prompt-profile",
                    "v1",
                    "--seed",
                    "7",
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            output = (cp.stdout or "") + (cp.stderr or "")
            self.assertEqual(cp.returncode, 0)
            self.assertIn("OK: il_compile_bench exit=0", output)

            summary_path = out_dir / "il.compile.bench.summary.json"
            result_path = out_dir / "il.compile.bench.results.jsonl"
            self.assertTrue(summary_path.exists())
            self.assertTrue(result_path.exists())

            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary.get("schema"), "IL_COMPILE_BENCH_SUMMARY_v2")
            self.assertEqual(summary.get("expected_match_rate"), 1.0)
            self.assertEqual(summary.get("reproducible_rate"), 1.0)
            self.assertGreaterEqual(summary.get("il_validity_rate", 0.0), 0.8)
            self.assertIn("term_summary", summary)
            self.assertIn("opcode_summary", summary)
            self.assertIsNotNone(summary["term_summary"].get("micro_f1"))
            self.assertIsNotNone(summary["opcode_summary"].get("micro_f1"))

    def test_bench_auto_expand(self):
        repo_root = Path(__file__).resolve().parent.parent
        bench_script = repo_root / "scripts" / "il_compile_bench.py"
        cases = repo_root / "tests" / "fixtures" / "il_compile" / "bench_cases.jsonl"

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "bench_out_expand"
            cp = subprocess.run(
                [
                    "python3",
                    str(bench_script),
                    "--cases",
                    str(cases),
                    "--out",
                    str(out_dir),
                    "--provider",
                    "rule_based",
                    "--expand-factor",
                    "1",
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            output = (cp.stdout or "") + (cp.stderr or "")
            self.assertEqual(cp.returncode, 0)
            self.assertIn("OK: il_compile_bench exit=0", output)
            summary = json.loads((out_dir / "il.compile.bench.summary.json").read_text(encoding="utf-8"))
            self.assertGreater(summary.get("expanded_cases", 0), 0)


if __name__ == "__main__":
    unittest.main()
