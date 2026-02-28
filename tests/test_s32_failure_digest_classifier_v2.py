import json
import tempfile
import unittest
from pathlib import Path

from scripts.il_thread_runner_v2 import run_thread_runner


class TestS32FailureDigestClassifierV2(unittest.TestCase):
    def _good_request(self) -> dict:
        return {
            "schema": "IL_COMPILE_REQUEST_v1",
            "request_text": "find alpha",
            "context": {"keywords": ["alpha"]},
            "constraints": {
                "allowed_opcodes": ["SEARCH_TERMS", "RETRIEVE", "ANSWER", "CITE"],
                "forbidden_keys": [],
                "max_steps": 4,
            },
            "artifact_pointers": [{"path": "tests/fixtures/il_exec/retrieve_db.json"}],
            "determinism": {"temperature": 0.0, "top_p": 1.0, "seed": 7, "stream": False},
        }

    def _bad_compile_request(self) -> dict:
        req = self._good_request()
        req["determinism"]["temperature"] = 0.4
        return req

    def test_failure_digest_has_class_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cases = tmp_path / "cases.jsonl"
            out_dir = tmp_path / "run_out"
            rows = [
                {"id": "ok_case", "request": self._good_request()},
                {"id": "bad_compile", "request": self._bad_compile_request()},
            ]
            with open(cases, "w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")

            rc = run_thread_runner(cases_path=cases, mode="validate-only", out_dir=out_dir)
            self.assertEqual(rc, 1)

            digest = json.loads((out_dir / "failure_digest.json").read_text(encoding="utf-8"))
            self.assertIn("class_summary", digest)
            self.assertIn("representative_cases", digest)
            self.assertGreaterEqual(digest.get("failure_count", 0), 1)
            failures = digest.get("failures", [])
            self.assertTrue(failures)
            self.assertIn("root_cause_class", failures[0])
            self.assertIn("COMPILE", digest.get("class_summary", {}))


if __name__ == "__main__":
    unittest.main()
