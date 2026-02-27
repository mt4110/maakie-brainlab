import importlib.util
import unittest


def _load_module():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s27_medium_eval_wall_v2.py"
    spec = importlib.util.spec_from_file_location("s27_medium_eval_wall_v2", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S27MediumEvalWallV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_validate_config(self):
        cfg = {
            "schema_version": "s27-medium-eval-wall-v2",
            "dataset_id": "x",
            "cases_path": "a.jsonl",
            "meta_path": "b.json",
            "baseline_cases_path": "c.jsonl",
            "contract": {
                "min_cases": 1,
                "max_cases": 10,
                "min_must_answer_true": 1,
                "min_must_answer_false": 0,
                "min_must_cite_true": 1,
                "max_unknown_ratio_warn": 0.4,
            },
            "tag_min_counts": {"provider": 1},
            "taxonomy_map": {"provider": ["provider"]},
        }
        ok, reason = self.m.validate_config(cfg)
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    def test_compute_taxonomy(self):
        cases = [
            {"tags": ["provider"]},
            {"tags": ["network"]},
            {"tags": ["weird"]},
        ]
        out = self.m.compute_taxonomy(cases, {"provider": ["provider"], "network": ["network"]})
        self.assertEqual(out["counts"]["provider"], 1)
        self.assertEqual(out["counts"]["network"], 1)
        self.assertEqual(out["counts"]["unknown"], 1)

    def test_validate_contract(self):
        dist = {"total_cases": 3, "must_answer_true": 2, "must_answer_false": 1, "must_cite_true": 2, "tag_counts": {"provider": 2}}
        contract = {"min_cases": 2, "max_cases": 10, "min_must_answer_true": 2, "min_must_answer_false": 1, "min_must_cite_true": 2}
        errs = self.m.validate_contract(dist, contract, {"provider": 1})
        self.assertEqual(errs, [])


if __name__ == "__main__":
    unittest.main()
