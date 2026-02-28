import subprocess
import unittest
from pathlib import Path


class TestS31Ilctl(unittest.TestCase):
    def test_help_and_unknown(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "ilctl.py"

        help_run = subprocess.run(
            ["python3", str(script), "--help"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        out_help = (help_run.stdout or "") + (help_run.stderr or "")
        self.assertEqual(help_run.returncode, 0)
        self.assertIn("commands:", out_help)

        bad_run = subprocess.run(
            ["python3", str(script), "unknown"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        out_bad = (bad_run.stdout or "") + (bad_run.stderr or "")
        self.assertEqual(bad_run.returncode, 1)
        self.assertIn("unknown command", out_bad)


if __name__ == "__main__":
    unittest.main()
