import json
import unittest

from src.il_compile import compile_request_bundle


class TestS31CompileReportV2(unittest.TestCase):
    def test_report_has_enriched_fields(self):
        req = {
            "schema": "IL_COMPILE_REQUEST_v1",
            "request_text": "find alpha",
            "context": {"keywords": ["alpha"]},
            "constraints": {"allowed_opcodes": ["SEARCH_TERMS", "RETRIEVE"], "forbidden_keys": [], "max_steps": 2},
            "artifact_pointers": [{"path": "tests/fixtures/il_exec/retrieve_db.json"}],
            "determinism": {"temperature": 0.0, "top_p": 1.0, "seed": 7, "stream": False},
        }
        bundle = compile_request_bundle(req, provider="rule_based")
        report = bundle.get("report", {})
        self.assertIn("request_sha256", report)
        self.assertIn("prompt_sha256", report)
        self.assertIn("artifact_pointer_count", report)
        self.assertIn("compile_latency_ms", report)
        self.assertEqual(report.get("artifact_pointer_count"), 1)


if __name__ == "__main__":
    unittest.main()
