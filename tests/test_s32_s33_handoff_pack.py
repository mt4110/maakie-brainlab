import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestS32S33HandoffPack(unittest.TestCase):
    def test_script_writes_backlog_and_handoff_artifacts(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "ops" / "s32_handoff_pack.py"
        with tempfile.TemporaryDirectory() as td:
            out29 = Path(td) / "s32-29"
            out30 = Path(td) / "s32-30"
            cp = subprocess.run(
                ["python3", str(script), "--out-dir-29", str(out29), "--out-dir-30", str(out30)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            output = (cp.stdout or "") + (cp.stderr or "")
            self.assertIn(cp.returncode, {0, 1}, msg=output)
            backlog_path = out29 / "s33_backlog_seed_latest.json"
            handoff_path = out30 / "handoff_latest.json"
            self.assertTrue(backlog_path.exists(), msg=output)
            self.assertTrue(handoff_path.exists(), msg=output)
            backlog = json.loads(backlog_path.read_text(encoding="utf-8"))
            handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
            self.assertEqual(backlog.get("schema"), "S32_S33_BACKLOG_SEED_PACK_V1")
            self.assertEqual(handoff.get("schema"), "S32_S33_HANDOFF_PACK_V1")
            self.assertIn("s33_start_conditions", handoff)


if __name__ == "__main__":
    unittest.main()
