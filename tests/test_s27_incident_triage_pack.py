import importlib.util
import unittest


def _load_module():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s27_incident_triage_pack.py"
    spec = importlib.util.spec_from_file_location("s27_incident_triage_pack", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S27IncidentTriagePackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_top_reason_codes(self):
        rows = self.m.top_reason_codes({"A": 1, "B": 3, "C": 2})
        self.assertEqual(rows[0][0], "B")
        self.assertEqual(rows[0][1], 3)


if __name__ == "__main__":
    unittest.main()
