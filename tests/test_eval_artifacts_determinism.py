import json
import unittest
from eval.run_eval import sanitize_pf

class TestEvalDeterminism(unittest.TestCase):
    def test_sanitize_pf_removes_latency(self):
        pf = {
            "status": "ok",
            "latency_ms": 123,
            "model_id": "test-model",
            "reason_code": None,
            "exit_code": 0
        }
        sanitized = sanitize_pf(pf)
        self.assertNotIn("latency_ms", sanitized)
        self.assertEqual(sanitized["status"], "ok")
        self.assertEqual(sanitized["model_id"], "test-model")

    def test_stable_json_serialization(self):
        # Verify that the keys are sorted and separators are compact
        data = {"b": 2, "a": 1}
        serialized = json.dumps(data, sort_keys=True, separators=(",", ":"))
        self.assertEqual(serialized, '{"a":1,"b":2}')

    def test_preflight_meta_structure(self):
        # Simulate the meta structure in run_eval.py
        pf = {"status": "ok", "latency_ms": 123, "model_id": "m1"}
        meta = {
            "meta": "pre_flight",
            "pre_flight": sanitize_pf(pf)
        }
        self.assertNotIn("timestamp", meta)
        self.assertNotIn("latency_ms", meta["pre_flight"])

if __name__ == "__main__":
    unittest.main()
