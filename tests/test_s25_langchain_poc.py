import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s25_langchain_poc.py"
    spec = importlib.util.spec_from_file_location("s25_langchain_poc", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S25LangChainPocTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_validate_config(self):
        cfg = {
            "schema_version": "s25-langchain-poc-v1",
            "poc": {"id": "x", "top_k": 3},
            "index": {"db_name": "index.sqlite3", "chunk_size": 800, "overlap": 100},
            "smoke": {"question": "sample_note.md のバナナ価格を教えてください。", "expected_source": "sample_note.md"},
            "docs": [{"path": "hello.md", "content": "hello"}],
        }
        ok, why = self.m.validate_config(cfg)
        self.assertTrue(ok)
        self.assertEqual(why, "")

        bad = dict(cfg)
        bad["schema_version"] = "unknown"
        ok2, why2 = self.m.validate_config(bad)
        self.assertFalse(ok2)
        self.assertIn("schema_version", why2)

    def test_evaluate_smoke_match(self):
        flow = {
            "status": "PASS",
            "backend": "langchain-core",
            "reason_code": "",
            "answer": "ok",
            "error": "",
        }
        rows = [
            {
                "source": "/tmp/sample_note.md#chunk-0",
                "path": "/tmp/sample_note.md",
                "text": "Banana price is 120 yen.",
                "score": 0.0,
            }
        ]
        result = self.m.evaluate_smoke(flow, rows=rows, expected_source="sample_note.md")
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["matched_expected_source"])

    def test_run_langchain_poc_without_dependency(self):
        rows = [
            {
                "source": "/tmp/sample_note.md#chunk-0",
                "path": "/tmp/sample_note.md",
                "text": "Banana price is 120 yen.",
                "score": 0.0,
            }
        ]
        with patch.dict("sys.modules", {"langchain_core": None}):
            out = self.m.run_langchain_poc(question="q", rows=rows)
        self.assertIn(out["status"], {"PASS", "SKIP", "FAIL"})


if __name__ == "__main__":
    unittest.main()
