import importlib.util
import unittest


def _load_module():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s27_slo_readiness.py"
    spec = importlib.util.spec_from_file_location("s27_slo_readiness", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S27SLOReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_evaluate_slo(self):
        out = self.m.evaluate_slo(
            skip_rate=0.5,
            unknown_ratio=0.1,
            acceptance_pass_rate=0.95,
            skip_soft=0.4,
            skip_hard=0.8,
            unknown_soft=0.2,
            unknown_hard=0.4,
            acceptance_soft=0.9,
            acceptance_hard=0.75,
        )
        self.assertEqual(len(out["hard"]), 0)
        self.assertEqual(len(out["soft"]), 1)

    def test_build_gate_rows(self):
        rows = self.m.build_gate_rows({
            "S27-01": {"summary": {"status": "PASS"}},
            "S27-02": {"summary": {"status": "WARN"}},
            "S27-03": {},
            "S27-04": {"summary": {"status": "PASS"}},
            "S27-05": {"summary": {"status": "PASS"}},
            "S27-06": {"summary": {"status": "PASS"}},
            "S27-07": {"summary": {"status": "PASS"}},
            "S27-08": {"summary": {"status": "PASS"}},
        })
        self.assertEqual(len(rows), 8)
        self.assertFalse(next(r for r in rows if r["phase"] == "S27-03")["passed"])

    def test_infer_status_unknown_summary_returns_missing(self):
        self.assertEqual(self.m.infer_status({"summary": {"status": "???"}}), "MISSING")
        self.assertEqual(self.m.infer_status({"summary": {}}), "MISSING")

    def test_compute_blocked_total(self):
        out = self.m.compute_blocked_total(3, [{"metric": "skip_rate"}, {"metric": "unknown_ratio"}])
        self.assertEqual(out, 5)


if __name__ == "__main__":
    unittest.main()
