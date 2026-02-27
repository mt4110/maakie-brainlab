import importlib.util
import tempfile
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s28_policy_drift_guard_v2.py"
    spec = importlib.util.spec_from_file_location("s28_policy_drift_guard_v2", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S28PolicyDriftGuardV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_scan_and_diff(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a = root / "a.txt"
            b = root / "b.txt"
            a.write_text("x\n", encoding="utf-8")
            b.write_text("y\n", encoding="utf-8")
            s1 = self.m.scan_current(root, ["a.txt", "b.txt"])
            b.write_text("z\n", encoding="utf-8")
            s2 = self.m.scan_current(root, ["a.txt", "b.txt"])
            diff = self.m.diff_scans(s1, s2)
            self.assertEqual(diff["changed"], ["b.txt"])


if __name__ == "__main__":
    unittest.main()
