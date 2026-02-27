import importlib.util
import unittest


def _load_module():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s28_slo_readiness_v2.py"
    spec = importlib.util.spec_from_file_location("s28_slo_readiness_v2", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S28SLOReadinessV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_evaluate_slo_soft(self):
        out = self.m.evaluate_slo(
            skip_rate=0.6,
            unknown_ratio=0.05,
            acceptance_pass_rate=1.0,
            notify_delivery_rate=1.0,
            reliability_total_runs=30,
            skip_soft=0.5,
            skip_hard=1.0,
            unknown_soft=0.1,
            unknown_hard=0.25,
            acceptance_soft=0.95,
            acceptance_hard=0.85,
            notify_soft=1.0,
            notify_hard=0.5,
            reliability_runs_soft_min=24,
            reliability_runs_hard_min=12,
        )
        self.assertEqual(len(out["hard"]), 0)
        self.assertEqual(len(out["soft"]), 1)

    def test_evaluate_slo_hard_by_reliability_runs(self):
        out = self.m.evaluate_slo(
            skip_rate=0.0,
            unknown_ratio=0.01,
            acceptance_pass_rate=1.0,
            notify_delivery_rate=1.0,
            reliability_total_runs=3,
            skip_soft=0.2,
            skip_hard=0.5,
            unknown_soft=0.05,
            unknown_hard=0.25,
            acceptance_soft=0.95,
            acceptance_hard=0.85,
            notify_soft=0.95,
            notify_hard=0.5,
            reliability_runs_soft_min=24,
            reliability_runs_hard_min=12,
        )
        self.assertEqual(len(out["hard"]), 1)
        self.assertEqual(out["hard"][0]["metric"], "reliability_total_runs")

    def test_compute_notify_delivery_rate(self):
        self.assertEqual(
            self.m.compute_notify_delivery_rate(notify_sent=False, notify_attempt_count=0, notify_attempted=False),
            0.0,
        )
        self.assertEqual(
            self.m.compute_notify_delivery_rate(notify_sent=True, notify_attempt_count=2, notify_attempted=True),
            0.5,
        )

    def test_build_gate_rows(self):
        rows = self.m.build_gate_rows(
            {
                "S28-01": {"summary": {"status": "PASS"}},
                "S28-02": {"summary": {"status": "WARN"}},
                "S28-03": {},
                "S28-04": {"summary": {"status": "PASS"}},
                "S28-05": {"summary": {"status": "PASS"}},
                "S28-06": {"summary": {"status": "PASS"}},
                "S28-07": {"summary": {"status": "PASS"}},
                "S28-08": {"summary": {"status": "PASS"}},
            }
        )
        self.assertEqual(len(rows), 8)
        self.assertFalse(next(r for r in rows if r["phase"] == "S28-03")["passed"])

    def test_build_waiver_context(self):
        context = self.m.build_waiver_context(
            d01={"trend": {"dominant_skip_cause": "env", "env_skip_rate": 1.0}},
            d02={"metrics": {"candidate_count": 6, "unknown_ratio": 0.31}, "collection_actions": ["a1"]},
            d03={"summary": {"reason_code": "NOTIFY_DRY_RUN"}, "notification": {"attempted": False, "delivery_state": "NOT_ATTEMPTED"}},
            d06={"summary": {"reason_code": "INSUFFICIENT_RUNS_ENV_GAP"}, "metrics": {"env_gap_ratio": 1.0}},
            env_gap_waiver_min_rate=0.8,
        )
        self.assertTrue(context["provider_env_gap"])
        self.assertTrue(context["notify_not_attempted"])
        self.assertTrue(context["reliability_env_gap"])
        self.assertTrue(context["taxonomy_feedback_active"])

    def test_apply_metric_waivers(self):
        hard = [
            {"metric": "skip_rate", "value": 1.0, "threshold": 0.5, "rule": "value <= hard"},
            {"metric": "unknown_ratio", "value": 0.31, "threshold": 0.25, "rule": "value <= hard"},
            {"metric": "notify_delivery_rate", "value": 0.0, "threshold": 0.5, "rule": "value >= hard"},
            {"metric": "reliability_total_runs", "value": 3, "threshold": 12, "rule": "value >= hard"},
        ]
        out = self.m.apply_metric_waivers(
            hard,
            context={
                "provider_env_gap": True,
                "notify_not_attempted": True,
                "reliability_env_gap": True,
                "taxonomy_feedback_active": True,
                "taxonomy_candidate_count": 6,
                "taxonomy_action_count": 3,
                "unknown_ratio": 0.31,
            },
            taxonomy_waiver_min_candidates=5,
            taxonomy_waiver_max_unknown=0.35,
        )
        self.assertEqual(len(out["hard"]), 0)
        self.assertEqual(len(out["waived_hard"]), 4)
        self.assertEqual(len(out["soft_from_hard"]), 4)


if __name__ == "__main__":
    unittest.main()
