import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "ops" / "ci" / "decide_cost_scope.py"
POLICY = ROOT / "ops" / "ci" / "cost_scope_policy.json"


def _run_decide(extra_args):
    cp = subprocess.run(
        ["python3", str(SCRIPT), "--policy", str(POLICY), "--json"] + extra_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if cp.returncode != 0:
        raise AssertionError(f"decide_cost_scope failed: rc={cp.returncode}\nstdout={cp.stdout}\nstderr={cp.stderr}")
    return json.loads(cp.stdout.strip())


class TestCICostScope(unittest.TestCase):
    def test_balanced_docs_only_is_light(self):
        out = _run_decide(
            [
                "--event",
                "pull_request",
                "--ref",
                "refs/pull/1/merge",
                "--mode",
                "balanced",
                "--changed-file",
                "docs/ops/CI_REQUIRED_CHECKS.md",
                "--changed-file",
                "README.md",
            ]
        )
        self.assertEqual(out["mode"], "balanced")
        self.assertEqual(out["heavy_needed"], 0)
        self.assertEqual(out["reason"], "docs_only")

    def test_balanced_impact_change_is_heavy(self):
        out = _run_decide(
            [
                "--event",
                "pull_request",
                "--ref",
                "refs/pull/2/merge",
                "--mode",
                "balanced",
                "--changed-file",
                ".github/workflows/verify_pack.yml",
            ]
        )
        self.assertEqual(out["mode"], "balanced")
        self.assertEqual(out["heavy_needed"], 1)
        self.assertTrue(str(out["reason"]).startswith("impact_file:"))

    def test_lite_mode_is_light_for_impact_changes(self):
        out = _run_decide(
            [
                "--event",
                "pull_request",
                "--ref",
                "refs/pull/3/merge",
                "--mode",
                "lite",
                "--changed-file",
                ".github/workflows/verify_pack.yml",
            ]
        )
        self.assertEqual(out["mode"], "lite")
        self.assertEqual(out["heavy_needed"], 0)
        self.assertEqual(out["reason"], "mode_always_light")

    def test_full_mode_is_heavy_even_docs_only(self):
        out = _run_decide(
            [
                "--event",
                "pull_request",
                "--ref",
                "refs/pull/4/merge",
                "--mode",
                "full",
                "--changed-file",
                "docs/ops/RUN_ALWAYS.md",
            ]
        )
        self.assertEqual(out["mode"], "full")
        self.assertEqual(out["heavy_needed"], 1)
        self.assertEqual(out["reason"], "mode_always_heavy")

    def test_workflow_dispatch_forces_heavy(self):
        out = _run_decide(
            [
                "--event",
                "workflow_dispatch",
                "--ref",
                "refs/heads/feature/x",
                "--mode",
                "lite",
                "--changed-file",
                "docs/ops/RUN_ALWAYS.md",
            ]
        )
        self.assertEqual(out["mode"], "lite")
        self.assertEqual(out["heavy_needed"], 1)
        self.assertEqual(out["reason"], "force_event:workflow_dispatch")

    def test_invalid_mode_falls_back_to_default_balanced(self):
        out = _run_decide(
            [
                "--event",
                "pull_request",
                "--ref",
                "refs/pull/5/merge",
                "--mode",
                "turbo",
                "--changed-file",
                "docs/ops/RUN_ALWAYS.md",
            ]
        )
        self.assertEqual(out["mode"], "balanced")
        self.assertEqual(out["heavy_needed"], 0)
        self.assertTrue(str(out["reason"]).startswith("fallback_mode:turbo;"))


if __name__ == "__main__":
    unittest.main()
