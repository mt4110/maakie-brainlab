import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestS32CloseoutV2(unittest.TestCase):
    def test_script_writes_closeout_artifacts(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "ops" / "s32_closeout_v2.py"
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "evidence"
            cp = subprocess.run(
                ["python3", str(script), "--out-dir", str(out_dir)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            output = (cp.stdout or "") + (cp.stderr or "")
            self.assertIn(cp.returncode, {0, 1}, msg=output)
            payload_path = out_dir / "closeout_latest.json"
            self.assertTrue(payload_path.exists(), msg=output)
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("schema"), "S32_CLOSEOUT_V2")
            self.assertIn("before_after", payload)
            self.assertIn("unresolved_risks", payload)


if __name__ == "__main__":
    unittest.main()
