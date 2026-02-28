import json
import tempfile
import unittest
from pathlib import Path

from src.il_executor import execute_il


class TestS32CorpusPolicyFilter(unittest.TestCase):
    def _run_pipeline(self, collect_args):
        il = {
            "il": {
                "opcodes": [
                    {"op": "SEARCH_TERMS", "args": {}},
                    {"op": "COLLECT", "args": collect_args},
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
            result = json.loads((Path(tmp) / "il.exec.result.json").read_text(encoding="utf-8"))
            return report, result

    def test_policy_filter_default_a_profile(self):
        report, result = self._run_pipeline(
            {
                "source": "file_jsonl",
                "path": "tests/fixtures/il_exec/retrieve_docs_policy.jsonl",
            }
        )
        self.assertEqual(report.get("overall_status"), "OK")
        collect_step = report.get("steps", [])[1]
        self.assertEqual(collect_step.get("status"), "OK")

        policy = collect_step.get("out_summary", {}).get("policy", {})
        self.assertTrue(policy.get("policy_enabled"))
        self.assertEqual(policy.get("allow_langs"), ["en", "ja"])
        self.assertEqual(policy.get("accepted_count"), 3)
        self.assertEqual(policy.get("rejected_count"), 2)
        self.assertGreaterEqual(policy.get("warn_count", 0), 1)
        self.assertIn("E_RAG_POLICY_DENYLIST", policy.get("reject_reason_codes", []))
        self.assertIn("E_RAG_POLICY_LANG", policy.get("reject_reason_codes", []))

        cited_doc_ids = {str(c.get("doc_id", "")) for c in result.get("cites", [])}
        self.assertNotIn("p003", cited_doc_ids)
        self.assertNotIn("p004", cited_doc_ids)

    def test_policy_filter_with_size_override(self):
        report, _ = self._run_pipeline(
            {
                "source": "file_jsonl",
                "path": "tests/fixtures/il_exec/retrieve_docs_policy.jsonl",
                "policy_max_chars": 120,
            }
        )
        self.assertEqual(report.get("overall_status"), "OK")
        policy = report.get("steps", [])[1].get("out_summary", {}).get("policy", {})
        self.assertEqual(policy.get("accepted_count"), 2)
        self.assertEqual(policy.get("rejected_count"), 3)
        self.assertIn("E_RAG_POLICY_SIZE", policy.get("reject_reason_codes", []))

    def test_policy_filter_can_be_disabled(self):
        report, _ = self._run_pipeline(
            {
                "source": "file_jsonl",
                "path": "tests/fixtures/il_exec/retrieve_docs_policy.jsonl",
                "policy_filter": False,
            }
        )
        collect_step = report.get("steps", [])[1]
        policy = collect_step.get("out_summary", {}).get("policy", {})
        self.assertFalse(policy.get("policy_enabled"))
        self.assertEqual(policy.get("rejected_count"), 0)
        self.assertEqual(collect_step.get("out_summary", {}).get("collected_count"), 5)


if __name__ == "__main__":
    unittest.main()
