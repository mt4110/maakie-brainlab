import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "current_point.py"
    spec = importlib.util.spec_from_file_location("current_point", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CurrentPointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_detect_track_thread_and_phase(self):
        self.assertEqual(self.m.detect_track("ops/S25-01-25-10"), "S25-01-25-10")
        self.assertEqual(self.m.detect_track("ops/S31-01--S31-30"), "S31-01-S31-30")
        self.assertEqual(self.m.detect_track("feature/s24-01-S24-10-work"), "S24-01-S24-10")
        self.assertEqual(self.m.detect_track("ops/S30-1-S30-900"), "S30-1-S30-900")
        self.assertEqual(self.m.detect_track("hotfix/S20-08"), "S20-08")

    def test_choose_task_file_prefers_matching_prefix(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "S24-01-S24-10-THREAD-V1_TASK.md").write_text("x", encoding="utf-8")
            (d / "S25-01-25-10-THREAD-V1_TASK.md").write_text("y", encoding="utf-8")
            (d / "S22-99_TASK.md").write_text("z", encoding="utf-8")
            chosen = self.m.choose_task_file(d, "S25-01-25-10")
            self.assertIsNotNone(chosen)
            self.assertEqual(chosen.name, "S25-01-25-10-THREAD-V1_TASK.md")

    def test_choose_task_file_prefers_highest_version_for_same_track(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "S28-01-S28-10-THREAD-V1_TASK.md").write_text("v1", encoding="utf-8")
            (d / "S28-01-S28-10-THREAD-V3_TASK.md").write_text("v3", encoding="utf-8")
            (d / "S28-01-S28-10-THREAD-V2_TASK.md").write_text("v2", encoding="utf-8")
            chosen = self.m.choose_task_file(d, "S28-01-S28-10")
            self.assertIsNotNone(chosen)
            self.assertEqual(chosen.name, "S28-01-S28-10-THREAD-V3_TASK.md")

    def test_parse_task_progress_and_next_items(self):
        text = """
## Progress
- S25-01-25-10: 10% (kickoff)

## Checklist
- [x] done one
- [ ] todo one
- [ ] todo two
"""
        progress, detail, checked, total, next_items = self.m.parse_task(text, max_next=1)
        self.assertEqual(progress, "10%")
        self.assertIn("S25-01-25-10", detail)
        self.assertEqual(checked, 1)
        self.assertEqual(total, 3)
        self.assertEqual(next_items, ["todo one"])

    def test_run_git_emits_warn_when_events_passed(self):
        cp = subprocess.CompletedProcess(args=["git", "x"], returncode=1, stdout="", stderr="fatal: bad")
        with tempfile.TemporaryDirectory() as td:
            events = []
            with patch("subprocess.run", return_value=cp):
                out = self.m.run_git(["x"], Path(td), events=events)
        self.assertIsNone(out)
        self.assertTrue(events)
        self.assertEqual(events[0]["level"], "WARN")
        self.assertIn("git failed args=x", events[0]["message"])


if __name__ == "__main__":
    unittest.main()
