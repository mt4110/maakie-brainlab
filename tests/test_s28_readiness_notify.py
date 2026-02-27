import importlib.util
import unittest


def _load_module():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s28_readiness_notify.py"
    spec = importlib.util.spec_from_file_location("s28_readiness_notify", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S28ReadinessNotifyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_compose_message(self):
        msg = self.m.compose_message(
            "#ops",
            {"summary": {"readiness": "READY", "status": "PASS", "reason_code": "", "blocked_total": 0}},
            {"summary": {"status": "PASS", "reason_code": ""}},
        )
        self.assertIn("channel=#ops", msg)
        self.assertIn("readiness=READY", msg)


if __name__ == "__main__":
    unittest.main()
