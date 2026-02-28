import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestS32AcceptanceWallV6(unittest.TestCase):
    def test_acceptance_wall_outputs_artifacts(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "ops" / "s32_acceptance_wall_v6.py"

        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "evidence"
            cp = subprocess.run(
                ["python3", str(script), "--out-dir", str(out_dir), "--skip-commands"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            output = (cp.stdout or "") + (cp.stderr or "")
            self.assertEqual(cp.returncode, 0, msg=output)
            payload = json.loads((out_dir / "acceptance_wall_v6_latest.json").read_text(encoding="utf-8"))
            self.assertEqual(payload.get("schema"), "S32_ACCEPTANCE_WALL_V6")
            self.assertIn("checks", payload)
            self.assertGreater(len(payload.get("checks", [])), 0)


if __name__ == "__main__":
    unittest.main()
