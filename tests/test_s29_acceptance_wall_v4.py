import importlib.util
import unittest


def _load_module():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s29_acceptance_wall_v4.py"
    spec = importlib.util.spec_from_file_location("s29_acceptance_wall_v4", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S29AcceptanceWallV4Tests(unittest.TestCase):
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

    def test_normalize_severity(self):
        self.assertEqual(self.m.normalize_severity("critical"), "critical")
        self.assertEqual(self.m.normalize_severity("bad"), "critical")

    def test_evaluate_assertion_len_ops(self):
        self.assertTrue(self.m.evaluate_assertion([1, 2, 3], "len_gte", 2))
        self.assertTrue(self.m.evaluate_assertion([1], "len_lte", 1))
        self.assertFalse(self.m.evaluate_assertion([1], "len_gte", 2))


if __name__ == "__main__":
    unittest.main()
