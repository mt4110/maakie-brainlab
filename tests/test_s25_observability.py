import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def _load(name: str, rel: str):
    root = Path(__file__).resolve().parents[1]
    path = root / rel
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S25ObservabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.obs = _load("obs_contract", "scripts/ops/obs_contract.py")
        cls.sum = _load("s25_obs_pr_summary", "scripts/ops/s25_obs_pr_summary.py")

    def test_emit_invalid_level_is_warn(self):
        events = []
        self.obs.emit("INFO", "hello", events)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["level"], "WARN")
        self.assertIn("invalid_level=INFO", events[0]["message"])

    def test_make_run_context_writes_meta(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_dir, meta, _events = self.obs.make_run_context(root, "unit-tool", obs_root=".local/obs/s25-ops")
            self.assertTrue(run_dir.exists())
            self.assertTrue((run_dir / "run.meta.json").exists())
            self.assertIn("unit-tool__", meta["run_id"])

    def test_collect_and_write_observability_report(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            obs_root = root / ".local" / "obs" / "s25-ops"
            tool_dir = obs_root / "current-point" / "run_a"
            tool_dir.mkdir(parents=True, exist_ok=True)
            (tool_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "tool": "current-point",
                        "run_id": "run_a",
                        "captured_at_utc": "2026-01-01T00:00:00+00:00",
                        "counts": {"OK": 3, "WARN": 0, "ERROR": 0, "SKIP": 1},
                    }
                ),
                encoding="utf-8",
            )
            baseline = root / "docs" / "evidence" / "s25-03" / "baseline_latest.json"
            baseline.parent.mkdir(parents=True, exist_ok=True)
            baseline.write_text(json.dumps({"summary": {"passed_commands": 1, "total_commands": 1}}), encoding="utf-8")

            latest = self.sum.collect_latest_tool_summaries(root, ".local/obs/s25-ops")
            self.assertIn("current-point", latest)
            out = self.sum.write_observability_report(
                repo_root=root,
                latest=latest,
                baseline_path=baseline,
                out_dir=root / "docs" / "evidence" / "s25-04",
            )
            self.assertTrue((root / out["json"]).exists())
            self.assertTrue((root / out["md"]).exists())
            md = (root / out["md"]).read_text(encoding="utf-8")
            self.assertIn("S25-04 Observability", md)
            self.assertIn("current-point", md)

    def test_sanitize_paths_masks_abs_outside_repo(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            payload = {"outside": "/Users/example/private/file.txt", "inside": str(root / "docs" / "a.json")}
            out = self.sum.sanitize_paths(root, payload)
            self.assertEqual(out["outside"], "file.txt")
            self.assertEqual(out["inside"], "docs/a.json")


if __name__ == "__main__":
    unittest.main()
