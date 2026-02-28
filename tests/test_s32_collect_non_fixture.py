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

    def test_collect_jsonl_source_fallback_is_repo_relative(self):
        repo_root = Path(__file__).resolve().parent.parent
        fixtures_root = repo_root / "tests" / "fixtures"
        with tempfile.TemporaryDirectory(dir=fixtures_root) as td:
            tmp_path = Path(td)
            source_path = tmp_path / "collect_no_source.jsonl"
            source_path.write_text(
                json.dumps(
                    {
                        "doc_id": "src001",
                        "title": "Alpha",
                        "text": "alpha evidence",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            rel_path = source_path.resolve().relative_to(repo_root).as_posix()
            il = {
                "il": {
                    "opcodes": [
                        {"op": "SEARCH_TERMS", "args": {}},
                        {
                            "op": "COLLECT",
                            "args": {
                                "source": "file_jsonl",
                                "path": rel_path,
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
            with tempfile.TemporaryDirectory() as out_tmp:
                report = execute_il(il, out_tmp)
                self.assertEqual(report.get("overall_status"), "OK")
                result = json.loads((Path(out_tmp) / "il.exec.result.json").read_text(encoding="utf-8"))
                self.assertGreater(len(result.get("cites", [])), 0)
                source_ref = str(result["cites"][0].get("source_path", ""))
                self.assertTrue(source_ref.startswith("tests/fixtures/"))
                self.assertIn("#L1", source_ref)


if __name__ == "__main__":
    unittest.main()
