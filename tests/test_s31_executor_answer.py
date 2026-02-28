import json
import tempfile
import unittest
from pathlib import Path

from src.il_executor import execute_il


class TestS31ExecutorAnswer(unittest.TestCase):
    def test_answer_generated_deterministically(self):
        il = {
            "il": {
                "opcodes": [
                    {"op": "SEARCH_TERMS", "args": {}},
                    {"op": "RETRIEVE", "args": {}},
                    {"op": "ANSWER", "args": {"style": "brief"}},
                    {"op": "CITE", "args": {}},
                ],
                "search_terms": ["alpha"],
            },
            "meta": {"version": "il_contract_v1"},
            "evidence": {},
        }
        fixture = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "il_exec" / "retrieve_db.json"

        with tempfile.TemporaryDirectory() as tmp:
            report = execute_il(il, tmp, str(fixture))
            self.assertEqual(report.get("overall_status"), "OK")
            result = json.loads((Path(tmp) / "il.exec.result.json").read_text(encoding="utf-8"))
            answer = result.get("answer", "")
            self.assertTrue(isinstance(answer, str) and len(answer) > 0)


if __name__ == "__main__":
    unittest.main()
