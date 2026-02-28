import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestS32DoctorV3FixHints(unittest.TestCase):
    def test_doctor_summary_contains_fix_hints_and_next_commands(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "il_doctor.py"

        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "doctor_out"
            cp = subprocess.run(
                ["python3", str(script), "--out", str(out_dir)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            output = (cp.stdout or "") + (cp.stderr or "")
            self.assertEqual(cp.returncode, 0, msg=output)
            summary = json.loads((out_dir / "il.doctor.summary.json").read_text(encoding="utf-8"))
            self.assertIn("fix_hints", summary)
            self.assertIn("next_commands", summary)
            self.assertIsInstance(summary.get("fix_hints"), list)
            self.assertIsInstance(summary.get("next_commands"), list)


if __name__ == "__main__":
    unittest.main()
