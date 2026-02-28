import json
import unittest

from src.il_compile import compile_request_bundle


class TestS31CompileParseGuard(unittest.TestCase):
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

    def test_parses_json_inside_code_fence(self):
        payload = {
            "il": {"opcodes": [{"op": "SEARCH_TERMS", "args": {}}], "search_terms": ["alpha"]},
            "meta": {"version": "il_contract_v1", "generator": "local"},
            "evidence": {"notes": "ok"},
        }

        def adapter(_prompt: str, _model: str, _det: dict) -> str:
            return "Here is result\n```json\n" + json.dumps(payload) + "\n```\nThanks"

        bundle = compile_request_bundle(
            self._request(),
            provider="local_llm",
            allow_fallback=False,
            llm_adapter=adapter,
        )
        self.assertEqual(bundle.get("status"), "OK")

    def test_parse_error_when_no_json(self):
        def adapter(_prompt: str, _model: str, _det: dict) -> str:
            return "not a json payload"

        bundle = compile_request_bundle(
            self._request(),
            provider="local_llm",
            allow_fallback=False,
            llm_adapter=adapter,
        )
        self.assertEqual(bundle.get("status"), "ERROR")
        codes = [e.get("code") for e in bundle.get("errors", [])]
        self.assertIn("E_PARSE", codes)


if __name__ == "__main__":
    unittest.main()
