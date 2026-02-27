import importlib.util
import unittest


def _load_module():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s26_release_readiness.py"
    spec = importlib.util.spec_from_file_location("s26_release_readiness", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S26ReleaseReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_build_gate_rows(self):
        docs = {
            "S26-01": {"summary": {"status": "SKIP"}},
            "S26-02": {"summary": {"status": "PASS"}},
            "S26-03": {"summary": {"status": "PASS"}},
            "S26-04": {"summary": {"status": "PASS"}},
            "S26-05": {"stop": 0},
            "S26-06": {"summary": {"failed_cases": 0}},
            "S26-07": {"summary": {"status": "WARN"}},
            "S26-08": {"summary": {"status": "WARN"}},
        }
        rows = self.m.build_gate_rows(docs)
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(bool(x["passed"]) for x in rows))

    def test_build_gate_rows_uses_safe_int(self):
        docs = {
            "S26-01": {"summary": {"status": "PASS"}},
            "S26-02": {"summary": {"status": "PASS"}},
            "S26-03": {"summary": {"status": "PASS"}},
            "S26-04": {"summary": {"status": "PASS"}},
            "S26-05": {"stop": "bad"},
            "S26-06": {"summary": {"failed_cases": "bad"}},
            "S26-07": {"summary": {"status": "PASS"}},
            "S26-08": {"summary": {"status": "PASS"}},
        }
        rows = self.m.build_gate_rows(docs)
        self.assertFalse(next(x for x in rows if x["phase"] == "S26-05")["passed"])
        self.assertFalse(next(x for x in rows if x["phase"] == "S26-06")["passed"])

    def test_is_stale_artifact(self):
        self.assertFalse(self.m.is_stale_artifact({}, "abc"))
        self.assertFalse(self.m.is_stale_artifact({"git": {"head": "abc"}}, "abc"))
        self.assertTrue(self.m.is_stale_artifact({"git": {"head": "def"}}, "abc"))


if __name__ == "__main__":
    unittest.main()
