import importlib.util
import unittest


def _load_module():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s27_acceptance_wall_v2.py"
    spec = importlib.util.spec_from_file_location("s27_acceptance_wall_v2", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S27AcceptanceWallV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_validate_case(self):
        ok, reason = self.m.validate_case(
            {
                "id": "A1",
                "severity": "critical",
                "artifact": "x.json",
                "assertion": {"path": "a", "op": "eq", "value": 1},
            }
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "")

        ok2, reason2 = self.m.validate_case({"id": "A1", "severity": "x", "artifact": "x.json", "assertion": {"path": "a", "op": "eq", "value": 1}})
        self.assertFalse(ok2)
        self.assertIn("severity", reason2)


if __name__ == "__main__":
    unittest.main()
