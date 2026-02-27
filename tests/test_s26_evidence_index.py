import importlib.util
import tempfile
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s26_evidence_index.py"
    spec = importlib.util.spec_from_file_location("s26_evidence_index", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S26EvidenceIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_read_json_if_exists(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.json"
            p.write_text('{"summary":{"status":"PASS"}}\n', encoding="utf-8")
            out = self.m.read_json_if_exists(p)
            self.assertEqual(out["summary"]["status"], "PASS")

    def test_build_markdown(self):
        payload = {
            "captured_at_utc": "2026-01-01T00:00:00Z",
            "git": {"branch": "x", "head": "y"},
            "summary": {"status": "PASS", "phases_total": 1, "present_count": 1, "missing_count": 0, "failed_count": 0, "warn_count": 0},
            "phases": [{"phase": "S26-01", "status": "PASS", "captured_at_utc": "z", "artifact": "a"}],
            "artifact_names": {"json": "evidence_index_latest.json"},
        }
        md = self.m.build_markdown(payload)
        self.assertIn("S26-08", md)
        self.assertIn("PASS", md)


if __name__ == "__main__":
    unittest.main()
