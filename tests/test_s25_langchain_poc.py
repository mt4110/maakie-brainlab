import importlib.util
import subprocess
import tempfile
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

        bad2 = dict(cfg)
        bad2["docs"] = [{"path": "../escape.md", "content": "x"}]
        ok3, why3 = self.m.validate_config(bad2)
        self.assertFalse(ok3)
        self.assertIn("unsafe", why3)

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

    def test_source_match_avoids_substring_false_positive(self):
        rows = [
            {
                "source": "raw/not_sample_note.md#chunk-0",
                "path": "raw/not_sample_note.md",
                "text": "x",
                "score": 0.0,
            }
        ]
        self.assertFalse(self.m.source_matches(rows, "sample_note.md"))

    def test_materialize_docs_rejects_escape(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            with self.assertRaises(ValueError):
                self.m.materialize_docs(run_dir, [{"path": "../x.md", "content": "x"}])

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

    def test_build_sqlite_index_timeout_returns_124(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            raw_dir = repo / "raw"
            idx_dir = repo / "idx"
            raw_dir.mkdir(parents=True, exist_ok=True)
            idx_dir.mkdir(parents=True, exist_ok=True)
            exc = subprocess.TimeoutExpired(cmd=["python3"], timeout=1, output=b"partial", stderr=b"err")
            with patch("subprocess.run", side_effect=exc):
                rc, out = self.m.build_sqlite_index(
                    repo_root=repo,
                    raw_dir=raw_dir,
                    index_dir=idx_dir,
                    db_name="index.sqlite3",
                    chunk_size=800,
                    overlap=100,
                    timeout_sec=1,
                )
        self.assertEqual(rc, 124)
        self.assertIn("timeout", out)
        self.assertIn("partial", out)


if __name__ == "__main__":
    unittest.main()
