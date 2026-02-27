import importlib.util
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s30_quality_burndown.py"
    spec = importlib.util.spec_from_file_location("s30_quality_burndown", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S30QualityBurndownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_evaluate_checks_warn_case(self):
        checks = self.m.evaluate_checks(
            closeout={"summary": {"waived_hard_count": 5, "unresolved_risk_count": 14}},
            readiness={
                "metrics": {
                    "skip_rate": 1.0,
                    "notify_delivery_rate": 0.0,
                    "recovery_success_rate": 0.0,
                    "reliability_total_runs": 3,
                },
                "slo": {
                    "waived_hard_violations": [
                        {"metric": "skip_rate"},
                        {"metric": "unknown_ratio"},
                        {"metric": "notify_delivery_rate"},
                        {"metric": "recovery_success_rate"},
                        {"metric": "reliability_total_runs"},
                    ]
                },
            },
            canary={"trend": {"trailing_nonpass_streak": 3, "env_skip_rate": 1.0}},
            taxonomy={"metrics": {"unknown_ratio": 0.31, "candidate_count": 5}},
            notify={
                "channels": [
                    {"attempted": True, "sent": False, "http_status": 0},
                    {"attempted": True, "sent": False, "http_status": 0},
                ],
                "inputs": {"max_retries": 2, "retry_backoff_sec": 1.0},
            },
            soak={"metrics": {"total_runs": 3}, "summary": {"status": "WARN"}},
            trend={"summary": {"warn_count": 5}},
        )
        self.assertEqual(len(checks), 19)
        summary = self.m.summarize(checks)
        self.assertEqual(summary["status"], "WARN")
        self.assertGreater(summary["remaining_checks"], 0)

        by_id = {row["id"]: row for row in checks}
        self.assertEqual(by_id["WVR-01"]["status"], "WARN")
        self.assertEqual(by_id["RSK-11"]["status"], "WARN")

    def test_evaluate_checks_all_pass(self):
        checks = self.m.evaluate_checks(
            closeout={"summary": {"waived_hard_count": 0, "unresolved_risk_count": 0}},
            readiness={
                "metrics": {
                    "skip_rate": 0.01,
                    "notify_delivery_rate": 1.0,
                    "recovery_success_rate": 1.0,
                    "reliability_total_runs": 30,
                },
                "slo": {"waived_hard_violations": []},
            },
            canary={"trend": {"trailing_nonpass_streak": 0, "env_skip_rate": 0.0}},
            taxonomy={"metrics": {"unknown_ratio": 0.01, "candidate_count": 1}},
            notify={
                "channels": [{"attempted": True, "sent": True, "http_status": 200}],
                "inputs": {"max_retries": 3, "retry_backoff_sec": 1.0},
            },
            soak={"metrics": {"total_runs": 30}, "summary": {"status": "PASS"}},
            trend={"summary": {"warn_count": 0}},
        )
        summary = self.m.summarize(checks)
        self.assertEqual(summary["status"], "PASS")
        self.assertEqual(summary["remaining_checks"], 0)
        self.assertEqual(sum(1 for c in checks if not c["done"]), 0)


if __name__ == "__main__":
    unittest.main()
