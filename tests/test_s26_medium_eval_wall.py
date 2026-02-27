import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def _load_module():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s26_medium_eval_wall.py"
    spec = importlib.util.spec_from_file_location("s26_medium_eval_wall", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S26MediumEvalWallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_validate_config_ok(self):
        cfg = {
            "schema_version": "s26-medium-eval-wall-v1",
            "dataset_id": "x",
            "cases_path": "a.jsonl",
            "meta_path": "b.json",
            "contract": {
                "min_cases": 10,
                "max_cases": 20,
                "min_must_answer_true": 5,
                "min_must_answer_false": 1,
                "min_must_cite_true": 5,
            },
            "tag_min_counts": {"basic": 2, "negative": 1},
        }
        ok, reason = self.m.validate_config(cfg)
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    def test_validate_case_schema_duplicate_case_id(self):
        cases = [
            {"case_id": "x", "query": "q1", "expectation": {"must_answer": True, "must_cite": True}, "tags": ["basic"]},
            {"case_id": "x", "query": "q2", "expectation": {"must_answer": True, "must_cite": True}, "tags": ["basic"]},
        ]
        errs = self.m.validate_case_schema(cases)
        self.assertTrue(any("duplicated" in e for e in errs))

    def test_validate_contract_detects_missing_tag_minimum(self):
        dist = {
            "total_cases": 12,
            "must_answer_true": 9,
            "must_answer_false": 3,
            "must_cite_true": 8,
            "tag_counts": {"basic": 3, "negative": 2},
        }
        contract = {
            "min_cases": 10,
            "max_cases": 20,
            "min_must_answer_true": 8,
            "min_must_answer_false": 2,
            "min_must_cite_true": 8,
        }
        errs = self.m.validate_contract(dist, contract, {"basic": 3, "policy": 1})
        self.assertTrue(any("policy" in e for e in errs))

    def test_compute_distribution(self):
        cases = [
            {"case_id": "a", "query": "q", "expectation": {"must_answer": True, "must_cite": True}, "tags": ["basic"]},
            {"case_id": "b", "query": "q", "expectation": {"must_answer": False, "must_cite": False}, "tags": ["negative", "security"]},
        ]
        dist = self.m.compute_distribution(cases)
        self.assertEqual(dist["total_cases"], 2)
        self.assertEqual(dist["must_answer_true"], 1)
        self.assertEqual(dist["must_answer_false"], 1)
        self.assertEqual(dist["must_cite_true"], 1)
        self.assertEqual(dist["tag_counts"]["basic"], 1)
        self.assertEqual(dist["tag_counts"]["negative"], 1)

    def test_compute_distribution_dedupes_tags_per_case(self):
        cases = [
            {
                "case_id": "a",
                "query": "q",
                "expectation": {"must_answer": True, "must_cite": True},
                "tags": ["basic", "basic", "basic"],
            }
        ]
        dist = self.m.compute_distribution(cases)
        self.assertEqual(dist["tag_counts"]["basic"], 1)

    def test_main_handles_bad_toml_and_writes_artifact(self):
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            bad_cfg = Path(td) / "bad.toml"
            out_dir = Path(td) / "out"
            bad_cfg.write_text("schema_version = [", encoding="utf-8")
            cp = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "scripts" / "ops" / "s26_medium_eval_wall.py"),
                    "--config",
                    str(bad_cfg),
                    "--out-dir",
                    str(out_dir),
                ],
                cwd=str(repo_root),
                env={**os.environ, "PYTHONPATH": "./src:."},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 1)
            payload = json.loads((out_dir / "medium_eval_wall_latest.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["reason_code"], self.m.REASON_CONFIG_INVALID)


if __name__ == "__main__":
    unittest.main()
