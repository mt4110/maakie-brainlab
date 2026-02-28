import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestS32PromptLoopDatasetV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.bench = _load_module("il_compile_bench", root / "scripts" / "il_compile_bench.py")
        cls.loop = _load_module("il_compile_prompt_loop", root / "scripts" / "il_compile_prompt_loop.py")
        cls.repo_root = root

    def _good_request(self, text: str) -> dict:
        return {
            "schema": "IL_COMPILE_REQUEST_v1",
            "request_text": text,
            "context": {"keywords": ["alpha"]},
            "constraints": {
                "allowed_opcodes": ["SEARCH_TERMS", "RETRIEVE", "ANSWER", "CITE"],
                "forbidden_keys": [],
                "max_steps": 4,
            },
            "artifact_pointers": [{"path": "tests/fixtures/il_exec/retrieve_db.json"}],
            "determinism": {"temperature": 0.0, "top_p": 1.0, "seed": 7, "stream": False},
        }

    def _error_request(self) -> dict:
        req = self._good_request("and or the")
        req["context"] = {}
        req["artifact_pointers"] = []
        return req

    def test_load_cases_validates_v2_fields(self):
        with tempfile.TemporaryDirectory() as td:
            cases = Path(td) / "cases.jsonl"
            rows = [
                {
                    "id": "easy_ok",
                    "request": self._good_request("find alpha"),
                    "expected_status": "OK",
                    "difficulty_tag": "easy",
                },
                {
                    "id": "hard_error",
                    "request": self._error_request(),
                    "expected_status": "ERROR",
                    "difficulty_tag": "hard",
                    "expected_failure_codes": ["E_INPUT"],
                },
            ]
            with open(cases, "w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            loaded = self.bench.load_cases(cases)
            self.assertEqual(loaded[0]["difficulty_tag"], "easy")
            self.assertEqual(loaded[1]["expected_failure_codes"], ["E_INPUT"])

    def test_bench_outputs_tag_summary(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            cases = td_path / "cases.jsonl"
            out = td_path / "out"
            rows = [
                {
                    "id": "easy_ok",
                    "request": self._good_request("find alpha"),
                    "expected_status": "OK",
                    "difficulty_tag": "easy",
                },
                {
                    "id": "medium_ok",
                    "request": self._good_request("find alpha and beta details"),
                    "expected_status": "OK",
                    "difficulty_tag": "medium",
                },
                {
                    "id": "hard_error",
                    "request": self._error_request(),
                    "expected_status": "ERROR",
                    "difficulty_tag": "hard",
                    "expected_failure_codes": ["E_INPUT"],
                },
            ]
            with open(cases, "w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")

            rc = self.bench.run_bench(
                cases_path=cases,
                out_dir=out,
                provider="rule_based",
                model="rule_based_v1",
                prompt_profile="v1",
                seed=7,
                allow_fallback=True,
                expand_factor=0,
            )
            self.assertEqual(rc, 0)
            summary = json.loads((out / "il.compile.bench.summary.json").read_text(encoding="utf-8"))
            tag_summary = summary.get("tag_summary", {})
            self.assertIn("easy", tag_summary)
            self.assertIn("medium", tag_summary)
            self.assertIn("hard", tag_summary)
            self.assertEqual(tag_summary["hard"]["total_cases"], 1)
            self.assertEqual(tag_summary["hard"]["expected_match_count"], 1)

    def test_prompt_loop_collects_tag_summary(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            cases = td_path / "cases.jsonl"
            out = td_path / "prompt_loop"
            rows = [
                {
                    "id": "easy_ok",
                    "request": self._good_request("find alpha"),
                    "expected_status": "OK",
                    "difficulty_tag": "easy",
                }
            ]
            with open(cases, "w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")

            result = self.loop._run_profile(
                profile="v1",
                cases=cases,
                out_dir=out,
                model="rule_based_v1",
                seed=7,
                expand_factor=0,
                allow_fallback=True,
            )
            self.assertEqual(result.get("status"), "OK")
            self.assertIn("tag_summary", result)
            self.assertIn("easy", result.get("tag_summary", {}))


if __name__ == "__main__":
    unittest.main()
