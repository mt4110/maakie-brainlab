import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.il_executor import execute_il


class TestS32CitationProvenanceV2(unittest.TestCase):
    def test_cite_contains_provenance_fields(self):
        il = {
            "il": {
                "opcodes": [
                    {"op": "SEARCH_TERMS", "args": {}},
                    {"op": "RETRIEVE", "args": {}},
                    {"op": "CITE", "args": {"max_cites": 2}},
                ],
                "search_terms": ["alpha"],
            },
            "meta": {"version": "il_contract_v1"},
            "evidence": {},
        }
        fixture = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "il_exec" / "retrieve_db.json"

        with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
            report1 = execute_il(il, tmp1, str(fixture))
            report2 = execute_il(il, tmp2, str(fixture))

            self.assertEqual(report1.get("overall_status"), "OK")
            self.assertEqual(report2.get("overall_status"), "OK")

            result1 = json.loads((Path(tmp1) / "il.exec.result.json").read_text(encoding="utf-8"))
            result2 = json.loads((Path(tmp2) / "il.exec.result.json").read_text(encoding="utf-8"))

            cites1 = result1.get("cites", [])
            cites2 = result2.get("cites", [])
            self.assertGreater(len(cites1), 0)
            self.assertEqual(cites1, cites2)

            cite = cites1[0]
            self.assertIn("snippet", cite)
            self.assertIn("source_path", cite)
            self.assertIn("snippet_sha256", cite)
            self.assertEqual(
                cite.get("snippet_sha256"),
                hashlib.sha256(cite.get("snippet", "").encode("utf-8")).hexdigest(),
            )

    def test_cite_rag_contains_provenance_fields(self):
        il = {
            "il": {
                "opcodes": [
                    {"op": "SEARCH_TERMS", "args": {}},
                    {
                        "op": "COLLECT",
                        "args": {
                            "source": "file_jsonl",
                            "path": "tests/fixtures/il_exec/retrieve_docs.jsonl",
                        },
                    },
                    {"op": "NORMALIZE", "args": {}},
                    {"op": "INDEX", "args": {}},
                    {"op": "SEARCH_RAG", "args": {}},
                    {"op": "CITE_RAG", "args": {}},
                ],
                "search_terms": ["alpha"],
            },
            "meta": {"version": "il_contract_v1"},
            "evidence": {},
        }

        with tempfile.TemporaryDirectory() as tmp:
            report = execute_il(il, tmp)
            self.assertEqual(report.get("overall_status"), "OK")
            result = json.loads((Path(tmp) / "il.exec.result.json").read_text(encoding="utf-8"))
            self.assertGreater(len(result.get("cites", [])), 0)
            cite = result["cites"][0]
            self.assertIn("source_path", cite)
            self.assertIn("snippet", cite)
            self.assertIn("snippet_sha256", cite)


if __name__ == "__main__":
    unittest.main()
