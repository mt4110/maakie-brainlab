import unittest

from src.il_compile import compile_request_bundle


class TestS32CompileProfileAutoSelect(unittest.TestCase):
    def _base_request(self) -> dict:
        return {
            "schema": "IL_COMPILE_REQUEST_v1",
            "request_text": "find alpha overview",
            "context": {"keywords": ["alpha"]},
            "constraints": {
                "allowed_opcodes": ["SEARCH_TERMS", "RETRIEVE", "ANSWER", "CITE"],
                "forbidden_keys": [],
                "max_steps": 4,
            },
            "artifact_pointers": [{"path": "tests/fixtures/il_exec/retrieve_db.json"}],
            "determinism": {"temperature": 0.0, "top_p": 1.0, "seed": 7, "stream": False},
        }

    def test_default_prompt_profile_uses_auto_selection(self):
        req = self._base_request()
        bundle = compile_request_bundle(req, provider="rule_based")
        report = bundle.get("report", {})
        self.assertEqual(bundle.get("status"), "OK")
        self.assertEqual(report.get("profile_selected_by"), "auto")
        self.assertEqual(report.get("prompt_profile"), "v1")

    def test_auto_select_medium_complexity_strict_json_v2(self):
        req = self._base_request()
        req["request_text"] = "Please build a deterministic compile flow with additional evidence pointers and robust parse guard"
        req["artifact_pointers"] = [
            {"path": "tests/fixtures/il_exec/retrieve_db.json"},
            {"path": "tests/fixtures/il_exec/retrieve_docs.jsonl"},
        ]
        bundle = compile_request_bundle(req, provider="rule_based", prompt_profile="auto")
        report = bundle.get("report", {})
        self.assertEqual(bundle.get("status"), "OK")
        self.assertEqual(report.get("profile_selected_by"), "auto")
        self.assertEqual(report.get("prompt_profile"), "strict_json_v2")

    def test_auto_select_high_complexity_contract_json_v3(self):
        req = self._base_request()
        req["request_text"] = "x" * 300
        req["artifact_pointers"] = [
            {"path": "tests/fixtures/il_exec/retrieve_db.json"},
            {"path": "tests/fixtures/il_exec/retrieve_docs.jsonl"},
            {"path": "tests/fixtures/il_exec/retrieve_docs_policy.jsonl"},
            {"path": "tests/fixtures/rss_sample.xml"},
        ]
        bundle = compile_request_bundle(req, provider="rule_based", prompt_profile="auto")
        report = bundle.get("report", {})
        self.assertEqual(bundle.get("status"), "OK")
        self.assertEqual(report.get("profile_selected_by"), "auto")
        self.assertEqual(report.get("prompt_profile"), "contract_json_v3")

    def test_manual_profile_override_kept(self):
        req = self._base_request()
        bundle = compile_request_bundle(req, provider="rule_based", prompt_profile="strict_json_v2")
        report = bundle.get("report", {})
        self.assertEqual(bundle.get("status"), "OK")
        self.assertEqual(report.get("prompt_profile"), "strict_json_v2")
        self.assertEqual(report.get("profile_selected_by"), "manual")


if __name__ == "__main__":
    unittest.main()
