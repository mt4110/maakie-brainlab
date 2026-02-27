import importlib.util
import unittest


def _load_module():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s28_incident_triage_pack_v2.py"
    spec = importlib.util.spec_from_file_location("s28_incident_triage_pack_v2", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S28IncidentTriagePackV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_top_reason_codes(self):
        rows = self.m.top_reason_codes({"A": 1, "B": 3, "C": 2})
        self.assertEqual(rows[0][0], "B")
        self.assertEqual(rows[0][1], 3)

    def test_dedupe_actions(self):
        out = self.m.dedupe_actions(["A", "a", "B"])
        self.assertEqual(out, ["A", "B"])

    def test_build_priority_actions(self):
        actions = self.m.build_priority_actions(
            {"recommended_actions": ["r1", "r1", "r2"]},
            {"collection_actions": ["c1"]},
            {"summary": {"status": "WARN", "reason_code": "NOTIFY_SEND_FAILED"}},
        )
        self.assertTrue(any("r1" == a for a in actions))
        self.assertTrue(any("Configure readiness webhook" in a for a in actions))


if __name__ == "__main__":
    unittest.main()
