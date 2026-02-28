import importlib.util
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s32_release_readiness_v2.py"
    spec = importlib.util.spec_from_file_location("s32_release_readiness_v2", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestS32ReleaseReadinessV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_decide_readiness_ready(self):
        rows = [{"id": "a", "status": "PASS"}, {"id": "b", "status": "PASS"}]
        d = self.m.decide_readiness(rows)
        self.assertEqual(d["readiness"], "READY")

    def test_decide_readiness_conditional(self):
        rows = [{"id": "a", "status": "PASS"}, {"id": "b", "status": "WARN"}]
        d = self.m.decide_readiness(rows)
        self.assertEqual(d["readiness"], "CONDITIONAL_READY")

    def test_decide_readiness_blocked(self):
        rows = [{"id": "a", "status": "PASS"}, {"id": "b", "status": "MISSING"}]
        d = self.m.decide_readiness(rows)
        self.assertEqual(d["readiness"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
