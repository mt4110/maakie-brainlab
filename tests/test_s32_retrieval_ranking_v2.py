import json
import tempfile
import unittest
from pathlib import Path

from src.il_executor import execute_il


class TestS32RetrievalRankingV2(unittest.TestCase):
    def _run_once(self, fixture_path: Path, out_dir: str):
        il = {
            "il": {
                "opcodes": [
                    {"op": "SEARCH_TERMS", "args": {}},
                    {"op": "RETRIEVE", "args": {"max_docs": 3}},
                ],
                "search_terms": ["alpha", "beta"],
            },
            "meta": {"version": "il_contract_v1"},
            "evidence": {},
        }
        return execute_il(il, out_dir, str(fixture_path))

    def test_retrieval_ranking_is_stable(self):
        fixture = {
            "docs": [
                {
                    "doc_id": "doc_a",
                    "title": "Alpha Beta Combined",
                    "text": "alpha beta short",
                    "source": "a.md",
                },
                {
                    "doc_id": "doc_b",
                    "title": "Alpha Heavy",
                    "text": "alpha " + ("noise " * 400),
                    "source": "b.md",
                },
                {
                    "doc_id": "doc_c",
                    "title": "Beta Only",
                    "text": "beta short",
                    "source": "c.md",
                },
            ],
            "index": {
                "alpha": ["doc_b", "doc_a"],
                "beta": ["doc_c", "doc_a"],
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            fixture_path = Path(tmp) / "fixture.json"
            fixture_path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")

            report1 = self._run_once(fixture_path, str(Path(tmp) / "out1"))
            report2 = self._run_once(fixture_path, str(Path(tmp) / "out2"))

            step1 = report1.get("steps", [])[1]
            step2 = report2.get("steps", [])[1]
            self.assertEqual(step1.get("status"), "OK")
            self.assertEqual(step2.get("status"), "OK")

            out1 = step1.get("out_summary", {})
            out2 = step2.get("out_summary", {})

            self.assertEqual(out1.get("ranking_version"), "v2")
            self.assertEqual(out1.get("doc_ids"), out2.get("doc_ids"))
            self.assertEqual(out1.get("score_preview"), out2.get("score_preview"))
            self.assertEqual(out1.get("doc_ids", [])[0], "doc_a")


if __name__ == "__main__":
    unittest.main()
