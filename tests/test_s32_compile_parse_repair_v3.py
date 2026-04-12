import json
import unittest

from src.il_compile import compile_request_bundle


class TestS32CompileParseRepairV3(unittest.TestCase):
    def _request(self) -> dict:
        return {
            "schema": "IL_COMPILE_REQUEST_v1",
            "request_text": "Find alpha in docs",
            "context": {"keywords": ["alpha"]},
            "constraints": {
                "allowed_opcodes": ["SEARCH_TERMS", "RETRIEVE", "ANSWER", "CITE"],
                "forbidden_keys": [],
                "max_steps": 4,
            },
            "artifact_pointers": [{"path": "tests/fixtures/il_exec/retrieve_db.json"}],
            "determinism": {"temperature": 0.0, "top_p": 1.0, "seed": 7, "stream": False},
        }

    def test_repair_applies_trailing_comma_rule(self):
        payload = {
            "il": {"opcodes": [{"op": "SEARCH_TERMS", "args": {}}, {"op": "RETRIEVE", "args": {}}], "search_terms": ["alpha"]},
            "meta": {"version": "il_contract_v1", "generator": "local"},
            "evidence": {"notes": "ok"},
        }
        text = json.dumps(payload, ensure_ascii=False).replace('"evidence": {"notes": "ok"}', '"evidence": {"notes": "ok"},')

        def adapter(_prompt: str, _model: str, _det: dict) -> str:
            return text

        bundle = compile_request_bundle(
            self._request(),
            provider="local_llm",
            allow_fallback=False,
            llm_adapter=adapter,
        )
        report = bundle.get("report", {})
        self.assertEqual(bundle.get("status"), "OK")
        self.assertTrue(report.get("repair_applied"))
        self.assertEqual(report.get("repair_rule_id"), "R_PARSE_TRAILING_COMMA")

    def test_repair_applies_close_brace_rule(self):
        raw = (
            '{"il":{"opcodes":[{"op":"SEARCH_TERMS","args":{}},{"op":"RETRIEVE","args":{}}],"search_terms":["alpha"]},'
            '"meta":{"version":"il_contract_v1","generator":"local"},'
            '"evidence":{"notes":"ok"}'
        )

        def adapter(_prompt: str, _model: str, _det: dict) -> str:
            return raw

        bundle = compile_request_bundle(
            self._request(),
            provider="local_llm",
            allow_fallback=False,
            llm_adapter=adapter,
        )
        report = bundle.get("report", {})
        self.assertEqual(bundle.get("status"), "OK")
        self.assertTrue(report.get("repair_applied"))
        self.assertEqual(report.get("repair_rule_id"), "R_PARSE_CLOSE_BRACE")

    def test_trailing_comma_repair_does_not_mutate_string_literals(self):
        raw = (
            '{"il":{"opcodes":[{"op":"SEARCH_TERMS","args":{}},{"op":"RETRIEVE","args":{}}],"search_terms":["alpha"]},'
            '"meta":{"version":"il_contract_v1","generator":"local"},'
            '"evidence":{"notes":"tag,}"},}'
        )

        def adapter(_prompt: str, _model: str, _det: dict) -> str:
            return raw

        bundle = compile_request_bundle(
            self._request(),
            provider="local_llm",
            allow_fallback=False,
            llm_adapter=adapter,
        )
        self.assertEqual(bundle.get("status"), "OK")
        compiled = dict(bundle.get("compiled_output", {}))
        evidence = dict(compiled.get("evidence", {}))
        self.assertEqual(evidence.get("notes"), "tag,}")
        report = bundle.get("report", {})
        self.assertTrue(report.get("repair_applied"))
        self.assertEqual(report.get("repair_rule_id"), "R_PARSE_TRAILING_COMMA")

    def test_repair_applies_missing_object_brace_before_array_end(self):
        raw = (
            '{"il":{"opcodes":[{"op":"SEARCH_TERMS","args":{}},{"op":"RETRIEVE","args":{"context_json":{"keywords":["alpha","greek"]}}],'
            '"search_terms":["alpha"]},"meta":{"version":"il_contract_v1","generator":"local"},'
            '"evidence":{"notes":"ok"}}'
        )

        def adapter(_prompt: str, _model: str, _det: dict) -> str:
            return raw

        bundle = compile_request_bundle(
            self._request(),
            provider="local_llm",
            allow_fallback=False,
            llm_adapter=adapter,
        )
        report = bundle.get("report", {})
        self.assertEqual(bundle.get("status"), "OK")
        self.assertTrue(report.get("repair_applied"))
        self.assertEqual(report.get("repair_rule_id"), "R_PARSE_CLOSE_OBJECT_BEFORE_ARRAY_END")

    def test_repair_relocates_trailing_brace_before_array_end(self):
        raw = (
            '{"il":{"opcodes":[{"op":"SEARCH_TERMS","args":{}},{"op":"RETRIEVE","args":{"context_json":{"keywords":["alpha","greek"]}}],'
            '"search_terms":["alpha"]},"meta":{"version":"il_contract_v1","generator":"local_llm"},'
            '"evidence":{"notes":"Searching Greek documents for an overview of alpha.","compile_contract":"il_compile_contract_v1"}}}'
        )

        def adapter(_prompt: str, _model: str, _det: dict) -> str:
            return raw

        bundle = compile_request_bundle(
            self._request(),
            provider="local_llm",
            allow_fallback=False,
            llm_adapter=adapter,
        )
        report = bundle.get("report", {})
        self.assertEqual(bundle.get("status"), "OK")
        self.assertTrue(report.get("repair_applied"))
        self.assertEqual(report.get("repair_rule_id"), "R_PARSE_CLOSE_OBJECT_BEFORE_ARRAY_END")

    def test_out_of_allowlist_repair_fails_closed(self):
        def adapter(_prompt: str, _model: str, _det: dict) -> str:
            return "{'il': {'opcodes': []}}"  # single-quote JSON is out-of-allowlist repair

        bundle = compile_request_bundle(
            self._request(),
            provider="local_llm",
            allow_fallback=False,
            llm_adapter=adapter,
        )
        report = bundle.get("report", {})
        self.assertEqual(bundle.get("status"), "ERROR")
        self.assertFalse(report.get("repair_applied"))
        self.assertEqual(report.get("repair_rule_id"), "")
        codes = [e.get("code") for e in bundle.get("errors", [])]
        self.assertIn("E_PARSE", codes)


if __name__ == "__main__":
    unittest.main()
