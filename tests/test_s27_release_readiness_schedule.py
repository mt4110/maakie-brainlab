import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s27_release_readiness_schedule.py"
    spec = importlib.util.spec_from_file_location("s27_release_readiness_schedule", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S27ReleaseReadinessScheduleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_summarize_readiness(self):
        out = self.m.summarize_readiness({"summary": {"readiness": "READY", "blocked_gates": 0}})
        self.assertEqual(out["readiness"], "READY")
        self.assertEqual(out["blocked"], 0)

    def test_summarize_readiness_uses_blocked_total(self):
        out = self.m.summarize_readiness(
            {"summary": {"readiness": "BLOCKED", "blocked_gates": 0, "blocked_total": 3}}
        )
        self.assertEqual(out["readiness"], "BLOCKED")
        self.assertEqual(out["blocked"], 3)

    def test_main_fail_when_artifacts_missing(self):
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "out"
            cp = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "scripts" / "ops" / "s27_release_readiness_schedule.py"),
                    "--out-dir",
                    str(out_dir),
                    "--skip-run",
                    "--primary-artifact",
                    str(Path(td) / "missing_primary.json"),
                    "--fallback-artifact",
                    str(Path(td) / "missing_fallback.json"),
                ],
                cwd=str(repo_root),
                env={**os.environ, "PYTHONPATH": "./src:."},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 1)
            payload = json.loads((out_dir / "release_readiness_schedule_latest.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["reason_code"], self.m.REASON_READINESS_MISSING)

    def test_main_fail_when_both_commands_fail_even_with_primary_artifact(self):
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "out"
            primary_artifact = Path(td) / "primary.json"
            primary_artifact.write_text(
                json.dumps({"summary": {"readiness": "READY", "blocked_gates": 0}}),
                encoding="utf-8",
            )
            cp = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "scripts" / "ops" / "s27_release_readiness_schedule.py"),
                    "--out-dir",
                    str(out_dir),
                    "--primary-artifact",
                    str(primary_artifact),
                    "--fallback-artifact",
                    str(Path(td) / "missing_fallback.json"),
                    "--primary-cmd",
                    "__definitely_missing_primary_command__",
                    "--fallback-cmd",
                    "__definitely_missing_fallback_command__",
                ],
                cwd=str(repo_root),
                env={**os.environ, "PYTHONPATH": "./src:."},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 1)
            payload = json.loads((out_dir / "release_readiness_schedule_latest.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["status"], "FAIL")
            self.assertEqual(payload["summary"]["reason_code"], self.m.REASON_PRIMARY_AND_FALLBACK_FAILED)


if __name__ == "__main__":
    unittest.main()
