import importlib.util
import tempfile
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s26_reliability_report.py"
    spec = importlib.util.spec_from_file_location("s26_reliability_report", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S26ReliabilityReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_count_reason_codes(self):
        rows = [{"reason_code": "TIMEOUT"}, {"reason_code": ""}, {"reason_code": "TIMEOUT"}, {"reason_code": "HTTP_429"}]
        out = self.m.count_reason_codes(rows)
        self.assertEqual(out["HTTP_429"], 1)
        self.assertEqual(out["TIMEOUT"], 2)

    def test_to_int_safe(self):
        self.assertEqual(self.m.to_int("7", 0), 7)
        self.assertEqual(self.m.to_int("bad", 9), 9)

    def test_read_json_if_exists_missing(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "none.json"
            self.assertEqual(self.m.read_json_if_exists(p), {})


if __name__ == "__main__":
    unittest.main()
