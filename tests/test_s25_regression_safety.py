import importlib.util
import json
import tempfile
import textwrap
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s25_regression_safety.py"
    spec = importlib.util.spec_from_file_location("s25_regression_safety", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S25RegressionSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_detect_contract_breaks_forbidden_context(self):
        issues = self.m.detect_contract_breaks(
            docs_contexts=["test", "milestone_required"],
            ruleset_contexts=["body_required"],
        )
        self.assertEqual(len(issues), 1)
        self.assertIn("milestone_required", issues[0])

    def test_read_required_contexts_from_temp_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "docs" / "ops").mkdir(parents=True, exist_ok=True)
            (root / "ops").mkdir(parents=True, exist_ok=True)
            (root / "docs" / "ops" / "CI_REQUIRED_CHECKS.md").write_text(
                textwrap.dedent(
                    """
                    <!-- required_checks_sot:v1
                    # comment
                    test
                    verify-pack
                    -->
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            (root / "ops" / "ruleset_required_status_checks.json").write_text(
                json.dumps({"required_status_checks": ["test", "body_required"]}) + "\n",
                encoding="utf-8",
            )
            docs, rules = self.m.read_required_contexts(root)
            self.assertEqual(docs, ["test", "verify-pack"])
            self.assertEqual(rules, ["body_required", "test"])


if __name__ == "__main__":
    unittest.main()
