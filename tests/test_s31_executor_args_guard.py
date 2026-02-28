import tempfile
import unittest

from src.il_executor import execute_il


class TestS31ExecutorArgsGuard(unittest.TestCase):
    def test_invalid_args_fail_closed(self):
        il = {
            "il": {
                "opcodes": [
                    {"op": "SEARCH_TERMS", "args": {"max_terms": "bad"}},
                ],
                "search_terms": ["alpha"],
            },
            "meta": {"version": "il_contract_v1"},
            "evidence": {},
        }
        with tempfile.TemporaryDirectory() as tmp:
            report = execute_il(il, tmp)
            self.assertEqual(report.get("overall_status"), "ERROR")
            reason = report.get("steps", [])[0].get("reason", "")
            self.assertIn("E_OPCODE_ARGS", reason)


if __name__ == "__main__":
    unittest.main()
