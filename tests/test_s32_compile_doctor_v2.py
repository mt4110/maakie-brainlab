import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestS32CompileDoctorV2(unittest.TestCase):
    def test_doctor_summary_has_compile_health_section(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "il_doctor.py"

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "doctor_out"
            cp = subprocess.run(
                ["python3", str(script), "--out", str(out_dir)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            output = (cp.stdout or "") + (cp.stderr or "")
            self.assertEqual(cp.returncode, 0, msg=output)

            summary_path = out_dir / "il.doctor.summary.json"
            self.assertTrue(summary_path.exists())
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertIn("compile_health", summary)
            compile_health = summary.get("compile_health", {})
            self.assertIn("status", compile_health)
            self.assertIn("checks", compile_health)
            self.assertIsInstance(compile_health.get("checks", []), list)


if __name__ == "__main__":
    unittest.main()
