"""
E10: Tests for rag_pipeline.py
- Test1: normalize preserves leading whitespace
- Test2: determinism (2 runs, key artifacts byte-identical)
"""
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

# Ensure scripts/ is importable
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from rag_pipeline import step_normalize, run_pipeline, _sha256_text, _write_text


class TestNormalizePreservesLeading(unittest.TestCase):
    """A4 fix: normalize must NOT strip leading whitespace."""

    def test_leading_whitespace_preserved(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            obs_dir = tmp / "obs"
            obs_dir.mkdir()
            blobs_dir = obs_dir / "11_collect_blobs"
            blobs_dir.mkdir(parents=True)

            # Content with leading whitespace
            content = "  leading space line\n    indented\nno indent\n"
            doc_id = _sha256_text(content)
            blob_file = blobs_dir / (doc_id.replace(":", "_") + ".txt")
            _write_text(blob_file, content)

            manifest = [{"doc_id": doc_id, "src": "test.txt"}]
            norm_manifest, stop = step_normalize(obs_dir, manifest)

            self.assertEqual(stop, 0);
            self.assertEqual(len(norm_manifest), 1)

            # Read normalized text
            norm_file = obs_dir / "21_norm_text" / (doc_id.replace(":", "_") + ".txt")
            norm_text = norm_file.read_text(encoding="utf-8")

            # Leading whitespace must be preserved
            self.assertTrue(norm_text.startswith("  leading space line"),
                            f"Leading whitespace lost: {norm_text[:40]!r}")
            self.assertIn("    indented", norm_text)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestDeterminism(unittest.TestCase):
    """2 runs with identical inputs must produce byte-identical key artifacts."""

    KEY_ARTIFACTS = [
        "10_collect_manifest.jsonl",
        "20_norm_manifest.jsonl",
        "31_index.json",
        "40_search_query.json",
        "41_search_results.jsonl",
        "50_citations.jsonl",
    ]

    def _sha256_file(self, path: Path) -> str:
        if not path.exists():
            return "MISSING"
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_two_runs_identical(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            obs1 = tmp / "run1"
            obs2 = tmp / "run2"

            repo_root = Path(__file__).resolve().parent.parent
            sources = ["tests/fixtures/il_exec/retrieve_db.json"]
            # Deliberately unsorted terms to test determinism
            terms = ["greek", "alpha", "greek"]

            rc1 = run_pipeline(obs1, sources, terms, repo_root=repo_root)
            rc2 = run_pipeline(obs2, sources, terms, repo_root=repo_root)

            self.assertEqual(rc1, 0, "run1 should succeed")
            self.assertEqual(rc2, 0, "run2 should succeed")

            for name in self.KEY_ARTIFACTS:
                h1 = self._sha256_file(obs1 / name)
                h2 = self._sha256_file(obs2 / name)
                self.assertEqual(h1, h2,
                                 f"Determinism failed for {name}: {h1} != {h2}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
