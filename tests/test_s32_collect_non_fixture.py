import json
import tempfile
import unittest
from pathlib import Path

from src.il_executor import execute_il


class TestS32CollectNonFixture(unittest.TestCase):
    def test_collect_file_jsonl_pipeline(self):
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
            steps = report.get("steps", [])
            self.assertEqual(steps[1].get("status"), "OK")
            self.assertEqual(steps[1].get("opcode"), "COLLECT")
            self.assertGreater(steps[1].get("out_summary", {}).get("collected_count", 0), 0)

            result = json.loads((Path(tmp) / "il.exec.result.json").read_text(encoding="utf-8"))
            self.assertGreater(len(result.get("cites", [])), 0)
            first_cite = result["cites"][0]
            self.assertIn("snippet", first_cite)
            self.assertIn("source_path", first_cite)
            self.assertIn("snippet_sha256", first_cite)

    def test_collect_rss_pipeline(self):
        il = {
            "il": {
                "opcodes": [
                    {"op": "SEARCH_TERMS", "args": {}},
                    {
                        "op": "COLLECT",
                        "args": {
                            "source": "rss",
                            "path": "tests/fixtures/rss_sample.xml",
                        },
                    },
                    {"op": "NORMALIZE", "args": {}},
                    {"op": "INDEX", "args": {}},
                    {"op": "SEARCH_RAG", "args": {}},
                    {"op": "CITE_RAG", "args": {}},
                ],
                "search_terms": ["content"],
            },
            "meta": {"version": "il_contract_v1"},
            "evidence": {},
        }

        with tempfile.TemporaryDirectory() as tmp:
            report = execute_il(il, tmp)
            self.assertEqual(report.get("overall_status"), "OK")
            steps = report.get("steps", [])
            self.assertEqual(steps[1].get("status"), "OK")
            self.assertEqual(steps[1].get("opcode"), "COLLECT")

    def test_collect_path_guard_fail_closed(self):
        il = {
            "il": {
                "opcodes": [
                    {"op": "SEARCH_TERMS", "args": {}},
                    {
                        "op": "COLLECT",
                        "args": {
                            "source": "file_jsonl",
                            "path": "../not_allowed.jsonl",
                        },
                    },
                ],
                "search_terms": ["alpha"],
            },
            "meta": {"version": "il_contract_v1"},
            "evidence": {},
        }

        with tempfile.TemporaryDirectory() as tmp:
            report = execute_il(il, tmp)
            self.assertEqual(report.get("overall_status"), "ERROR")
            reason = report.get("steps", [])[1].get("reason", "")
            self.assertIn("E_RAG_COLLECT_PATH", reason)


if __name__ == "__main__":
    unittest.main()
