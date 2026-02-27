import importlib.util
import tempfile
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s25_rag_tuning_loop.py"
    spec = importlib.util.spec_from_file_location("s25_rag_tuning_loop", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S25RagTuningLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_validate_config(self):
        cfg = {
            "schema_version": "s25-rag-tuning-v1",
            "loop": {"id": "x"},
            "storage": {"backend": "sqlite", "db_name": "index.sqlite3"},
            "profiles": {
                "baseline": {"chunk_size": 1200, "overlap": 200, "top_k": 1},
                "candidate": {"chunk_size": 800, "overlap": 100, "top_k": 3},
            },
            "evaluation": {"min_hit_rate_delta": -0.1},
            "docs": [{"path": "hello.md", "content": "hello"}],
            "cases": [{"id": "R01", "query": "q", "expected_source": "hello.md"}],
        }
        ok, why = self.m.validate_config(cfg)
        self.assertTrue(ok)
        self.assertEqual(why, "")

        bad = dict(cfg)
        bad["storage"] = {"backend": "postgres"}
        ok2, why2 = self.m.validate_config(bad)
        self.assertFalse(ok2)
        self.assertIn("sqlite", why2)

        bad2 = dict(cfg)
        bad2["docs"] = [{"path": "../escape.md", "content": "x"}]
        ok3, why3 = self.m.validate_config(bad2)
        self.assertFalse(ok3)
        self.assertIn("unsafe", why3)

    def test_compare_profiles(self):
        base = {"metrics": {"hit_rate": 0.5, "avg_latency_ms": 10}}
        cand = {"metrics": {"hit_rate": 0.7, "avg_latency_ms": 12}}
        comp = self.m.compare_profiles(base, cand, min_hit_rate_delta=0.1)
        self.assertEqual(comp["status"], "PASS")
        self.assertAlmostEqual(comp["delta_hit_rate"], 0.2)

        comp2 = self.m.compare_profiles(base, cand, min_hit_rate_delta=0.3)
        self.assertEqual(comp2["status"], "FAIL")

    def test_source_matches_expected_exact_suffix(self):
        self.assertTrue(self.m.source_matches_expected("sample_note.md", "raw/sample_note.md"))
        self.assertFalse(self.m.source_matches_expected("sample_note.md", "raw/not_sample_note.md"))

    def test_materialize_docs_rejects_escape(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            with self.assertRaises(ValueError):
                self.m.materialize_docs(run_dir, [{"path": "../x.md", "content": "x"}])


if __name__ == "__main__":
    unittest.main()
