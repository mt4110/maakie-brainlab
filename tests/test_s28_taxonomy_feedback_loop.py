import importlib.util
import unittest


def _load_module():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s28_taxonomy_feedback_loop.py"
    spec = importlib.util.spec_from_file_location("s28_taxonomy_feedback_loop", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S28TaxonomyFeedbackLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_suggest_taxonomy(self):
        self.assertEqual(self.m.suggest_taxonomy(["provider"], ""), "provider")
        self.assertEqual(self.m.suggest_taxonomy([], "timeout issue"), "timeout")

    def test_build_collection_actions(self):
        actions = self.m.build_collection_actions(
            [
                {"suggested_taxonomy": "provider"},
                {"suggested_taxonomy": "provider"},
                {"suggested_taxonomy": "network"},
            ],
            3,
        )
        self.assertEqual(actions[0], "Collect at least 2 additional labeled cases for taxonomy 'provider'.")

    def test_validate_config(self):
        ok, reason = self.m.validate_config(
            {
                "schema_version": "s28-taxonomy-feedback-loop-v1",
                "cases_path": "x.jsonl",
                "known_tags": ["provider"],
                "unknown_ratio_target": 0.1,
            }
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    def test_candidate_priority_prefers_more_unknown_tags(self):
        known = {"provider", "network"}
        a = {"case_id": "a", "tags": ["provider", "new-x"], "query": "q"}
        b = {"case_id": "b", "tags": ["provider"], "query": "long query"}
        self.assertGreater(self.m.candidate_priority(a, known), self.m.candidate_priority(b, known))

    def test_dedupe_candidates(self):
        rows = [
            {"case_id": "c1", "tags": ["unknown"], "query": "a"},
            {"case_id": "c1", "tags": ["unknown"], "query": "b"},
            {"case_id": "c2", "tags": ["unknown"], "query": "c"},
        ]
        deduped = self.m.dedupe_candidates(rows)
        self.assertEqual(len(deduped), 2)


if __name__ == "__main__":
    unittest.main()
