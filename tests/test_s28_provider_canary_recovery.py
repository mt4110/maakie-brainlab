import importlib.util
import unittest


def _load_module():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s28_provider_canary_recovery.py"
    spec = importlib.util.spec_from_file_location("s28_provider_canary_recovery", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S28ProviderCanaryRecoveryTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
