import importlib.util
import unittest


def _load_module():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s29_reliability_soak_v3.py"
    spec = importlib.util.spec_from_file_location("s29_reliability_soak_v3", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S29ReliabilitySoakV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_longest_consecutive_status(self):
        rows = [{"status": "PASS"}, {"status": "FAIL"}, {"status": "SKIP"}, {"status": "PASS"}]
        self.assertEqual(self.m.longest_consecutive_status(rows, {"FAIL", "SKIP"}), 2)

    def test_parse_hour(self):
        self.assertEqual(self.m.parse_hour("2026-02-27T03:00:00Z"), 3)
        self.assertEqual(self.m.parse_hour(""), -1)

    def test_reason_code_counts(self):
        rows = [
            {"status": "SKIP", "reason_code": "MISSING_PROVIDER_ENV"},
            {"status": "SKIP", "reason_code": "MISSING_PROVIDER_ENV"},
            {"status": "FAIL", "reason_code": "TIMEOUT"},
        ]
        counts = self.m.reason_code_counts(rows)
        self.assertEqual(counts["MISSING_PROVIDER_ENV"], 2)
        profile = self.m.env_gap_profile(rows)
        self.assertEqual(profile["env_gap_runs"], 2)
        self.assertAlmostEqual(profile["env_gap_ratio"], 0.6667, places=4)

    def test_evaluate_reliability_status_target_runs(self):
        status, reason = self.m.evaluate_reliability_status(
            history_present=True,
            total_runs=8,
            min_runs=6,
            target_runs=24,
            max_consecutive_nonpass=1,
            max_consecutive_threshold=4,
            fail_rate=0.0,
            fail_rate_hard_threshold=0.3,
            skip_rate=0.0,
            skip_rate_warn_threshold=0.5,
            recovery_present=True,
            dominant_reason_code="",
            env_gap_ratio=0.0,
        )
        self.assertEqual(status, "WARN")
        self.assertEqual(reason, self.m.REASON_TARGET_RUNS_NOT_REACHED)

    def test_evaluate_reliability_status_skip_env_gap(self):
        status, reason = self.m.evaluate_reliability_status(
            history_present=True,
            total_runs=12,
            min_runs=6,
            target_runs=24,
            max_consecutive_nonpass=1,
            max_consecutive_threshold=4,
            fail_rate=0.0,
            fail_rate_hard_threshold=0.3,
            skip_rate=0.9,
            skip_rate_warn_threshold=0.5,
            recovery_present=True,
            dominant_reason_code="MISSING_PROVIDER_ENV",
            env_gap_ratio=0.9,
        )
        self.assertEqual(status, "WARN")
        self.assertEqual(reason, self.m.REASON_SKIP_RATE_HIGH_ENV_GAP)


if __name__ == "__main__":
    unittest.main()
