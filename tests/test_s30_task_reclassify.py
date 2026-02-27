import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s30_task_reclassify.py"
    spec = importlib.util.spec_from_file_location("s30_task_reclassify", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S30TaskReclassifyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_extract_pending_from_text(self):
        text = """
- [x] done
- [ ] run verify gate
  - [ ] nested pending
"""
        out = self.m.extract_pending_from_text("docs/ops/X_TASK.md", text)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0].task, "run verify gate")
        self.assertEqual(out[1].task, "nested pending")

    def test_classify_prefers_flow_axis(self):
        task = self.m.PendingTask(file="docs/ops/SX_TASK.md", line=10, task="run verify and gate readiness")
        out = self.m.classify_task(task)
        self.assertEqual(out.axis_id, "A_FLOW_FAILZERO")
        self.assertGreater(out.priority_score, 0)

    def test_classify_prefers_log_axis(self):
        task = self.m.PendingTask(file="docs/ops/SX_TASK.md", line=12, task="ログ output summary artifact を確認")
        out = self.m.classify_task(task)
        self.assertEqual(out.axis_id, "B_LOG_CLARITY")

    def test_collect_pending_tasks_includes_ptask(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "docs" / "ops").mkdir(parents=True, exist_ok=True)
            (root / "docs" / "ops" / "A_TASK.md").write_text("- [ ] docs task\n", encoding="utf-8")
            (root / "+PTASK+").write_text("- [ ] ptask item\n", encoding="utf-8")
            tasks = self.m.collect_pending_tasks(root, include_ptask=True)
            labels = {f"{t.file}:{t.task}" for t in tasks}
            self.assertIn("docs/ops/A_TASK.md:docs task", labels)
            self.assertIn("+PTASK+:ptask item", labels)

    def test_mark_checked_line(self):
        out, changed = self.m.mark_checked_line("- [ ] demo task\n")
        self.assertTrue(changed)
        self.assertEqual(out, "- [x] demo task\n")

    def test_apply_batch_rows(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "docs" / "ops" / "A_TASK.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("- [ ] one\n- [ ] two\n", encoding="utf-8")
            stats = self.m.apply_batch_rows(
                root,
                [
                    {"file": "docs/ops/A_TASK.md", "line": 1},
                    {"file": "docs/ops/A_TASK.md", "line": 2},
                ],
            )
            self.assertEqual(stats["targeted"], 2)
            self.assertEqual(stats["applied"], 2)
            self.assertEqual(target.read_text(encoding="utf-8"), "- [x] one\n- [x] two\n")


if __name__ == "__main__":
    unittest.main()
