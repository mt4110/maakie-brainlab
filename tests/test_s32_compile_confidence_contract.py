import os
import unittest

from src.il_compile import compile_request_bundle


class TestS32CompileConfidenceContract(unittest.TestCase):
    def _request(self, *, text: str = "find alpha", artifacts: int = 1, max_steps: int = 4) -> dict:
        pointers = [{"path": "tests/fixtures/il_exec/retrieve_db.json"}]
        if artifacts == 0:
            pointers = []
        elif artifacts > 1:
            pointers = pointers + [{"path": "tests/fixtures/il_exec/retrieve_docs.jsonl"}]
        return {
            "schema": "IL_COMPILE_REQUEST_v1",
            "request_text": text,
            "context": {"keywords": ["alpha"]},
            "constraints": {
                "allowed_opcodes": ["SEARCH_TERMS", "RETRIEVE", "ANSWER", "CITE"],
                "forbidden_keys": [],
                "max_steps": max_steps,
            },
            "artifact_pointers": pointers,
            "determinism": {"temperature": 0.0, "top_p": 1.0, "seed": 7, "stream": False},
        }

    def test_confidence_is_deterministic_for_same_input(self):
        req = self._request()
        a = compile_request_bundle(req, provider="rule_based")
        b = compile_request_bundle(req, provider="rule_based")
        self.assertEqual(a.get("status"), "OK")
        self.assertEqual(b.get("status"), "OK")
        ra = a.get("report", {})
        rb = b.get("report", {})
        self.assertEqual(ra.get("confidence"), rb.get("confidence"))
        self.assertEqual(ra.get("confidence_status"), rb.get("confidence_status"))
        self.assertIsInstance(ra.get("confidence_factors"), list)
        self.assertGreater(len(ra.get("confidence_factors", [])), 0)

    def test_low_confidence_can_be_identified(self):
        req = self._request(text="alpha", artifacts=0, max_steps=6)
        bundle = compile_request_bundle(req, provider="rule_based")
        self.assertEqual(bundle.get("status"), "OK")
        report = bundle.get("report", {})
        self.assertLess(float(report.get("confidence", 1.0)), float(report.get("confidence_warn_threshold", 0.0)))
        self.assertEqual(report.get("confidence_status"), "LOW")

    def test_confidence_threshold_override_with_arg(self):
        req = self._request(text="alpha", artifacts=0, max_steps=6)
        bundle = compile_request_bundle(req, provider="rule_based", confidence_warn_threshold=0.40)
        report = bundle.get("report", {})
        self.assertEqual(bundle.get("status"), "OK")
        self.assertEqual(report.get("confidence_warn_threshold"), 0.4)
        self.assertEqual(report.get("confidence_status"), "OK")

    def test_confidence_threshold_override_with_env(self):
        req = self._request(text="alpha", artifacts=0, max_steps=6)
        old = os.environ.get("IL_COMPILE_CONFIDENCE_WARN_BELOW")
        try:
            os.environ["IL_COMPILE_CONFIDENCE_WARN_BELOW"] = "0.40"
            bundle = compile_request_bundle(req, provider="rule_based")
        finally:
            if old is None:
                os.environ.pop("IL_COMPILE_CONFIDENCE_WARN_BELOW", None)
            else:
                os.environ["IL_COMPILE_CONFIDENCE_WARN_BELOW"] = old
        report = bundle.get("report", {})
        self.assertEqual(report.get("confidence_warn_threshold"), 0.4)
        self.assertEqual(report.get("confidence_status"), "OK")


if __name__ == "__main__":
    unittest.main()
