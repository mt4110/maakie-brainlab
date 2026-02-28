import subprocess
import tempfile
import unittest
from pathlib import Path


class TestS32IlctlScenarios(unittest.TestCase):
    def test_help_lists_scenarios(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "ilctl.py"
        cp = subprocess.run(
            ["python3", str(script), "--help"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        output = (cp.stdout or "") + (cp.stderr or "")
        self.assertEqual(cp.returncode, 0)
        self.assertIn("scenarios:", output)
        self.assertIn("quickstart", output)
        self.assertIn("triage", output)
        self.assertIn("verify-pack", output)

    def test_quickstart_scenario_runs_end_to_end(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "ilctl.py"
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws"
            cp = subprocess.run(
                ["python3", str(script), "quickstart", "--out", str(ws)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            output = (cp.stdout or "") + (cp.stderr or "")
            self.assertEqual(cp.returncode, 0, msg=output)
            self.assertTrue((ws / "out" / "compile" / "il.compiled.json").exists())
            self.assertTrue((ws / "out" / "entry" / "il.exec.report.json").exists())

    def test_verify_pack_rejects_extra_args(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "ilctl.py"
        cp = subprocess.run(
            ["python3", str(script), "verify-pack", "--bad"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        output = (cp.stdout or "") + (cp.stderr or "")
        self.assertEqual(cp.returncode, 1)
        self.assertIn("does not accept extra args", output)


if __name__ == "__main__":
    unittest.main()
