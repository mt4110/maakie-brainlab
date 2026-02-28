import importlib.util
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s32_regression_safety_v3.py"
    spec = importlib.util.spec_from_file_location("s32_regression_safety_v3", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestS32RegressionSafetyV3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_matrix_defined(self):
        self.assertGreaterEqual(len(self.m.MATRIX), 4)

    def test_run_helper_pass(self):
        root = Path(__file__).resolve().parents[1]
        row = self.m._run(["python3", "-c", "print('ok')"], root)
        self.assertEqual(row.get("status"), "PASS")
        self.assertEqual(row.get("returncode"), 0)


if __name__ == "__main__":
    unittest.main()
