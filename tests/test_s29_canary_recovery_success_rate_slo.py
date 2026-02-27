import importlib.util
import unittest


def _load_module():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s29_canary_recovery_success_rate_slo.py"
    spec = importlib.util.spec_from_file_location("s29_canary_recovery_success_rate_slo", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S29ProviderCanaryRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_trailing_nonpass_streak(self):
        runs = [
            {"status": "PASS"},
            {"status": "SKIP"},
            {"status": "FAIL"},
            {"status": "SKIP"},
        ]
        self.assertEqual(self.m.trailing_nonpass_streak(runs), 3)

    def test_trailing_nonpass_streak_zero(self):
        self.assertEqual(self.m.trailing_nonpass_streak([{"status": "PASS"}]), 0)

    def test_classify_skip_reason(self):
        self.assertEqual(self.m.classify_skip_reason("MISSING_PROVIDER_ENV"), self.m.SKIP_CAUSE_ENV)
        self.assertEqual(self.m.classify_skip_reason("POLICY_INVALID"), self.m.SKIP_CAUSE_CONFIG)
        self.assertEqual(self.m.classify_skip_reason("NETWORK_TIMEOUT"), self.m.SKIP_CAUSE_RUNTIME)

    def test_summarize_skip_causes_and_dominant(self):
        rows = [
            {"status": "SKIP", "reason_code": "MISSING_PROVIDER_ENV"},
            {"status": "SKIP", "reason_code": "MISSING_PROVIDER_ENV"},
            {"status": "SKIP", "reason_code": "NETWORK_TIMEOUT"},
            {"status": "PASS", "reason_code": ""},
        ]
        counts = self.m.summarize_skip_causes(rows)
        self.assertEqual(counts[self.m.SKIP_CAUSE_ENV], 2)
        self.assertEqual(self.m.dominant_cause(counts), self.m.SKIP_CAUSE_ENV)
        env = self.m.env_skip_metrics(rows)
        self.assertEqual(env["env_skip_runs"], 2)
        self.assertAlmostEqual(env["env_skip_rate"], 0.6667, places=4)

    def test_build_recommended_actions_env(self):
        actions = self.m.build_recommended_actions(
            rollback_cmd="python3 rollback.py",
            top_cause=self.m.SKIP_CAUSE_ENV,
            trailing=4,
            recovery_threshold=3,
        )
        self.assertTrue(any("env variables" in a for a in actions))
        self.assertTrue(any("status transition to PASS" in a for a in actions))

    def test_redact_sensitive_text(self):
        redacted = self.m.redact_sensitive_text("api_key=abc token=def bearer ghp_zzz")
        self.assertIn("[REDACTED]", redacted)
        self.assertNotIn("abc", redacted)
        self.assertNotIn("def", redacted)
        self.assertNotIn("ghp_zzz", redacted)

    def test_estimate_recovery_success_metrics(self):
        rows = [
            {"status": "FAIL"},
            {"status": "PASS"},
            {"status": "SKIP"},
            {"status": "FAIL"},
        ]
        out = self.m.estimate_recovery_success_metrics(rows, {"attempted": False, "status": "SKIP"})
        self.assertGreaterEqual(out["attempts"], 1)
        self.assertGreaterEqual(out["success_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
