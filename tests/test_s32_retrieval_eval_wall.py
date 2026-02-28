import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s32_retrieval_eval_wall.py"
    spec = importlib.util.spec_from_file_location("s32_retrieval_eval_wall", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestS32RetrievalEvalWall(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_evaluate_cases_pass(self):
        fixture = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "s32_05" / "retrieval_eval_cases.jsonl"
        rows, err = self.m.load_cases_jsonl(fixture)
        self.assertEqual(err, "")
        payload = self.m.evaluate_cases(
            rows,
            k=3,
            min_hit_rate=0.8,
            min_citation_coverage=0.5,
            max_no_hit_rate=0.2,
            max_policy_reject_rate=0.6,
        )
        summary = payload["summary"]
        self.assertEqual(summary["status"], "PASS")
        self.assertEqual(summary["metrics"]["hit_rate_at_k"], 1.0)
        self.assertEqual(summary["metrics"]["no_hit_rate"], 0.0)

    def test_main_warn_when_cases_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "out"
            rc = self.m.main(
                [
                    "--cases-jsonl",
                    "tests/fixtures/s32_05/does_not_exist.jsonl",
                    "--out-dir",
                    str(out_dir),
                ]
            )
            self.assertEqual(rc, 0)
            payload = json.loads((out_dir / "retrieval_eval_wall_latest.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["status"], "WARN")
            self.assertTrue(payload["summary"].get("error"))

    def test_main_error_when_quality_too_low(self):
        with tempfile.TemporaryDirectory() as tmp:
            cases_path = Path(tmp) / "retrieval_eval_cases_bad.jsonl"
            cases_path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "case_id": "bad_01",
                                "expected_doc_ids": ["doc_expected"],
                                "retrieved_doc_ids": [],
                                "cited_doc_ids": [],
                                "policy_rejected_count": 0,
                            }
                        ),
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            out_dir = Path(tmp) / "out"
            rc = self.m.main(
                [
                    "--cases-jsonl",
                    str(cases_path),
                    "--out-dir",
                    str(out_dir),
                ]
            )
            self.assertEqual(rc, 1)
            payload = json.loads((out_dir / "retrieval_eval_wall_latest.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["status"], "ERROR")


if __name__ == "__main__":
    unittest.main()
