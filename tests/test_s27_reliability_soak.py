import importlib.util
import unittest


def _load_module():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s27_reliability_soak.py"
    spec = importlib.util.spec_from_file_location("s27_reliability_soak", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S27ReliabilitySoakTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_longest_consecutive_status(self):
        rows = [{"status": "PASS"}, {"status": "FAIL"}, {"status": "FAIL"}, {"status": "PASS"}, {"status": "FAIL"}]
        self.assertEqual(self.m.longest_consecutive_status(rows, {"FAIL"}), 2)

    def test_parse_hour(self):
        self.assertEqual(self.m.parse_hour("2026-02-27T03:00:00Z"), 3)
        self.assertEqual(self.m.parse_hour(""), -1)


if __name__ == "__main__":
    unittest.main()
