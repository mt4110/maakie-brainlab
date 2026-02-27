import importlib.util
import tempfile
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s26_regression_safety.py"
    spec = importlib.util.spec_from_file_location("s26_regression_safety", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S26RegressionSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_detect_contract_breaks(self):
        self.assertEqual(self.m.detect_contract_breaks(["a.md"], expected_min=1), [])
        issues = self.m.detect_contract_breaks([], expected_min=1)
        self.assertEqual(len(issues), 1)

    def test_read_contract_markers(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p1 = root / "a.md"
            p2 = root / "b.md"
            p1.write_text("milestone checks are non-blocking\n", encoding="utf-8")
            p2.write_text("no marker\n", encoding="utf-8")
            markers, errs = self.m.read_contract_markers(root, ["a.md", "b.md", "c.md"])
            self.assertEqual(markers, ["a.md"])
            self.assertEqual(len(errs), 1)


if __name__ == "__main__":
    unittest.main()
