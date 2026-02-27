import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s25_baseline_freeze.py"
    spec = importlib.util.spec_from_file_location("s25_baseline_freeze", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S25BaselineFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_parse_unittest_extracts_count(self):
        out = "Ran 3 tests in 0.004s\n\nOK\n"
        info = self.m.parse_unittest(out)
        self.assertEqual(info.get("tests_ran"), 3)
        self.assertTrue(info.get("passed"))

    def test_parse_ops_progress(self):
        out = "OK: progress=10%\nOK: checklist=1/10\n"
        self.assertEqual(self.m.parse_ops_progress(out), "10%")

    def test_parse_eval_summary_reads_summary_json(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_dir = root / ".local" / "rag_eval" / "runs" / "run__abc"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "summary.json").write_text(
                json.dumps({"counts": {"PASS": 2, "FAIL": 1, "SKIP": 0}}),
                encoding="utf-8",
            )
            output = f"[eval] Run artifacts saved to: {run_dir}\n"
            info = self.m.parse_eval_summary(output, repo_root=root)
            self.assertEqual(info.get("total"), 3)
            self.assertAlmostEqual(info.get("pass_rate"), 2 / 3, places=4)


if __name__ == "__main__":
    unittest.main()
