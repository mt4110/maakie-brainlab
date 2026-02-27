import importlib.util
import tempfile
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s26_rollback_artifact.py"
    spec = importlib.util.spec_from_file_location("s26_rollback_artifact", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S26RollbackArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_read_json_if_exists(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.json"
            p.write_text('{"a":1}\n', encoding="utf-8")
            out = self.m.read_json_if_exists(p)
            self.assertEqual(out["a"], 1)

    def test_read_json_if_exists_missing(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "missing.json"
            out = self.m.read_json_if_exists(p)
            self.assertEqual(out, {})


if __name__ == "__main__":
    unittest.main()
