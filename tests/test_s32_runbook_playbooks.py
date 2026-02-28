import unittest
from pathlib import Path


class TestS32RunbookPlaybooks(unittest.TestCase):
    def test_runbook_contains_s32_playbooks(self):
        repo_root = Path(__file__).resolve().parent.parent
        runbook = (repo_root / "docs" / "ops" / "IL_ENTRY_RUNBOOK.md").read_text(encoding="utf-8")

        self.assertIn("Decision Playbooks (S32-23)", runbook)
        self.assertIn("Playbook A: compile parse failure", runbook)
        self.assertIn("Playbook B: no-hit", runbook)
        self.assertIn("Playbook C: lock conflict", runbook)
        self.assertIn("Playbook D: retry saturation", runbook)
        self.assertIn("Playbook E: latency breach", runbook)
        self.assertIn("確認コマンド", runbook)
        self.assertIn("判断条件", runbook)
        self.assertIn("次アクション", runbook)


if __name__ == "__main__":
    unittest.main()
