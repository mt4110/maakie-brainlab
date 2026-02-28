import tempfile
import unittest

from src.il_executor import execute_il


class TestS31ExecutionBudgetGuard(unittest.TestCase):
    def test_max_steps_budget_blocks(self):
        il = {
            "il": {
                "opcodes": [
                    {"op": "SEARCH_TERMS", "args": {}},
                    {"op": "RETRIEVE", "args": {}},
                ],
                "search_terms": ["alpha"],
                "budget": {"max_steps": 1},
            },
            "meta": {"version": "il_contract_v1"},
            "evidence": {},
        }
        with tempfile.TemporaryDirectory() as tmp:
            report = execute_il(il, tmp)
            self.assertEqual(report.get("overall_status"), "ERROR")
            self.assertIn("E_BUDGET_MAX_STEPS", report.get("steps", [])[0].get("reason", ""))


if __name__ == "__main__":
    unittest.main()
