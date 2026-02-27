import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s26_orchestration_core.py"
    spec = importlib.util.spec_from_file_location("s26_orchestration_core", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S26OrchestrationCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_read_json_if_exists(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "s.json"
            p.write_text('{"summary":{"status":"PASS"}}\n', encoding="utf-8")
            out = self.m.read_json_if_exists(p)
            self.assertEqual(out["summary"]["status"], "PASS")

    def test_build_markdown_contains_summary(self):
        payload = {
            "captured_at_utc": "2026-01-01T00:00:00Z",
            "git": {"branch": "x", "head": "y"},
            "summary": {"status": "PASS", "failed_steps": 0},
            "steps": [{"name": "a", "status": "PASS", "returncode": 0}],
            "artifact_names": {"json": "orchestration_core_latest.json"},
        }
        md = self.m.build_markdown(payload)
        self.assertIn("S26-04", md)
        self.assertIn("PASS", md)

    def test_run_step_records_display_command(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            run_dir = repo / "run"
            run_dir.mkdir(parents=True, exist_ok=True)
            out = self.m.run_step(
                repo_root=repo,
                run_dir=run_dir,
                name="x",
                exec_cmd=[sys.executable, "-c", "print('ok')"],
                display_cmd=["python3", "scripts/ops/x.py"],
                timeout_sec=5,
            )
            self.assertEqual(out["status"], "PASS")
            self.assertEqual(out["command"], ["python3", "scripts/ops/x.py"])


if __name__ == "__main__":
    unittest.main()
