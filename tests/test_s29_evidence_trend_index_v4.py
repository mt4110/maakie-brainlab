import importlib.util
import unittest


def _load_module():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s29_evidence_trend_index_v4.py"
    spec = importlib.util.spec_from_file_location("s29_evidence_trend_index_v4", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S29EvidenceTrendIndexV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_count_statuses_and_overall(self):
        rows = [
            {"present": True, "status": "PASS"},
            {"present": True, "status": "WARN"},
            {"present": True, "status": "FAIL"},
            {"present": True, "status": "MISSING"},
            {"present": False, "status": "MISSING"},
        ]
        counts = self.m.count_statuses(rows)
        self.assertEqual(counts["missing_count"], 1)
        self.assertEqual(counts["failed_count"], 2)
        self.assertEqual(self.m.overall_status(counts), "FAIL")

    def test_is_stale(self):
        now = 1_000_000.0
        self.assertTrue(self.m.is_stale("", now_epoch=now, stale_hours=1.0))
        self.assertFalse(self.m.is_stale("1970-01-12T13:46:40Z", now_epoch=1_000_001.0, stale_hours=1.0))

    def test_infer_status_missing_summary_fields(self):
        self.assertEqual(self.m.infer_status({}), "MISSING")
        self.assertEqual(self.m.infer_status({"summary": {"status": "UNKNOWN"}}), "MISSING")


if __name__ == "__main__":
    unittest.main()
