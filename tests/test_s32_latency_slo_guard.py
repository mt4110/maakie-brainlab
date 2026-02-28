import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s32_latency_slo_guard.py"
    spec = importlib.util.spec_from_file_location("s32_latency_slo_guard", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestS32LatencySloGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_evaluate_latency_guard_insufficient_sample(self):
        result = self.m.evaluate_latency_guard(
            [50.0],
            budget_p50_ms=80.0,
            budget_p95_ms=200.0,
            timeout_ms=1000.0,
            min_samples=3,
        )
        self.assertEqual(result["status"], "WARN")
        self.assertEqual(result["reason_code"], "INSUFFICIENT_SAMPLE")

    def test_collect_and_evaluate_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_dir = root / "run"
            run_dir.mkdir(parents=True, exist_ok=True)
            cases_path = run_dir / "cases.jsonl"
            case_rows = []
            for idx, ms in enumerate([50, 70, 90], 1):
                cdir = run_dir / "cases" / f"{idx:04d}_c{idx}" / "compile"
                cdir.mkdir(parents=True, exist_ok=True)
                rel = f"cases/{idx:04d}_c{idx}/compile/il.compile.report.json"
                (run_dir / rel).write_text(json.dumps({"compile_latency_ms": ms}), encoding="utf-8")
                case_rows.append({"id": f"c{idx}", "artifacts": {"compile_report": rel}})
            with open(cases_path, "w", encoding="utf-8") as f:
                for row in case_rows:
                    f.write(json.dumps(row) + "\n")

            latencies, details = self.m.collect_compile_latencies_ms(run_dir)
            self.assertEqual(len(latencies), 3)
            self.assertEqual(len(details), 3)
            result = self.m.evaluate_latency_guard(
                latencies,
                budget_p50_ms=80.0,
                budget_p95_ms=200.0,
                timeout_ms=1000.0,
                min_samples=3,
            )
            self.assertEqual(result["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
