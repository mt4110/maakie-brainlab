import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s25_ml_experiment.py"
    spec = importlib.util.spec_from_file_location("s25_ml_experiment", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S25MLExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_metric_by_path(self):
        obj = {"a": {"b": 1.25}, "c": 3}
        self.assertEqual(self.m._metric_by_path(obj, "a.b"), 1.25)
        self.assertEqual(self.m._metric_by_path(obj, "c"), 3.0)
        self.assertIsNone(self.m._metric_by_path(obj, "a.x"))

    def test_validate_template(self):
        tpl = {
            "schema_version": "s25-ml-experiment-template-v1",
            "input": {"cases_path": "x"},
            "config": {"seed": 7},
            "evaluation": {"thresholds": [{"metric": "x", "op": ">=", "value": 0.0}]},
        }
        ok, why = self.m.validate_template(tpl)
        self.assertTrue(ok)
        self.assertEqual(why, "")

        bad = {"schema_version": "bad"}
        ok2, why2 = self.m.validate_template(bad)
        self.assertFalse(ok2)
        self.assertTrue(why2)

    def test_build_bench_cmd_seed_override(self):
        tpl = {
            "input": {"cases_path": "tests/fixtures/il_compile/bench_cases.jsonl"},
            "config": {
                "provider": "rule_based",
                "model": "rule_based_v1",
                "prompt_profile": "v1",
                "seed": 7,
                "expand_factor": 0,
                "allow_fallback": True,
            },
        }
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "scripts").mkdir(parents=True, exist_ok=True)
            (repo / "scripts" / "il_compile_bench.py").write_text("print('x')\n", encoding="utf-8")
            (repo / "tests" / "fixtures" / "il_compile").mkdir(parents=True, exist_ok=True)
            (repo / "tests" / "fixtures" / "il_compile" / "bench_cases.jsonl").write_text("", encoding="utf-8")
            run_dir = repo / ".local" / "obs" / "run"
            cmd = self.m.build_bench_cmd(repo, run_dir, tpl, seed_override=11)
            self.assertIn("--seed", cmd)
            idx = cmd.index("--seed")
            self.assertEqual(cmd[idx + 1], "11")

    def test_run_bench_timeout_returns_structured_failure(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            run_dir = repo / ".local" / "obs" / "run"
            run_dir.mkdir(parents=True, exist_ok=True)
            cmd = ["python3", "-c", "print('x')"]
            timeout_exc = subprocess.TimeoutExpired(cmd=cmd, timeout=1, output="partial", stderr="err")
            with patch("subprocess.run", side_effect=timeout_exc):
                out = self.m.run_bench(cmd=cmd, repo_root=repo, run_dir=run_dir, timeout_sec=1, seed=7)
            self.assertEqual(out["rc"], 124)
            self.assertTrue(out["timed_out"])
            self.assertIn("timeout", out["output"])
            self.assertTrue((run_dir / "01_ml_experiment.log").exists())


if __name__ == "__main__":
    unittest.main()
