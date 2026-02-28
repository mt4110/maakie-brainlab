import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestS31WorkspaceInit(unittest.TestCase):
    def test_workspace_init_and_force_behavior(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "il_workspace_init.py"

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "il_ws"

            first = subprocess.run(
                ["python3", str(script), "--out", str(workspace)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            first_out = (first.stdout or "") + (first.stderr or "")
            self.assertEqual(first.returncode, 0)
            self.assertIn("workspace_initialized", first_out)

            request_path = workspace / "request.sample.json"
            cases_path = workspace / "cases.sample.jsonl"
            readme_path = workspace / "README.md"
            out_dir = workspace / "out"

            self.assertTrue(request_path.exists())
            self.assertTrue(cases_path.exists())
            self.assertTrue(readme_path.exists())
            self.assertTrue(out_dir.exists())

            request_obj = json.loads(request_path.read_text(encoding="utf-8"))
            self.assertEqual(request_obj.get("schema"), "IL_COMPILE_REQUEST_v1")

            case_lines = [line for line in cases_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(case_lines), 1)
            case_obj = json.loads(case_lines[0])
            self.assertEqual(case_obj.get("id"), "sample_alpha")

            readme_text = readme_path.read_text(encoding="utf-8")
            self.assertIn("scripts/il_compile.py", readme_text)
            self.assertIn("scripts/il_thread_runner_v2.py", readme_text)

            second = subprocess.run(
                ["python3", str(script), "--out", str(workspace)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            second_out = (second.stdout or "") + (second.stderr or "")
            self.assertEqual(second.returncode, 1)
            self.assertIn("target already exists", second_out)

            force = subprocess.run(
                ["python3", str(script), "--out", str(workspace), "--force"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            force_out = (force.stdout or "") + (force.stderr or "")
            self.assertEqual(force.returncode, 0)
            self.assertIn("workspace_initialized", force_out)


if __name__ == "__main__":
    unittest.main()
