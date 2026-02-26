import importlib.util
import tempfile
import unittest
from pathlib import Path


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
        self.assertEqual(self.m.detect_track("feature/s24-01-S24-10-work"), "S24-01-S24-10")
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


if __name__ == "__main__":
    unittest.main()
