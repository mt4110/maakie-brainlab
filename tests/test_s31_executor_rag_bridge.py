import tempfile
import unittest
from pathlib import Path

from src.il_executor import execute_il


class TestS31ExecutorRagBridge(unittest.TestCase):
    def test_rag_bridge_flow(self):
        il = {
            "il": {
                "opcodes": [
                    {"op": "SEARCH_TERMS", "args": {}},
                    {"op": "COLLECT", "args": {}},
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
        fixture = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "il_exec" / "retrieve_db.json"

        with tempfile.TemporaryDirectory() as tmp:
            report = execute_il(il, tmp, str(fixture))
            self.assertEqual(report.get("schema"), "IL_EXEC_REPORT_v1")
            steps = report.get("steps", [])
            self.assertEqual(len(steps), 6)
            # CITE_RAG should not be ERROR in normal fixture flow.
            self.assertNotEqual(steps[-1].get("status"), "ERROR")


if __name__ == "__main__":
    unittest.main()
