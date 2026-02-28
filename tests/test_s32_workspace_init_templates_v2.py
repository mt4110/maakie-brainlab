import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestS32WorkspaceInitTemplatesV2(unittest.TestCase):
    def test_template_incident_generates_expected_files(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "il_workspace_init.py"

        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws_incident"
            cp = subprocess.run(
                ["python3", str(script), "--out", str(ws), "--template", "incident"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            output = (cp.stdout or "") + (cp.stderr or "")
            self.assertEqual(cp.returncode, 0, msg=output)
            self.assertIn("template=incident", output)

            req = json.loads((ws / "request.sample.json").read_text(encoding="utf-8"))
            self.assertIn("incident", str(req.get("request_text", "")).lower())
            case_lines = [x for x in (ws / "cases.sample.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
            case = json.loads(case_lines[0])
            self.assertEqual(case.get("id"), "incident_timeline")
            readme = (ws / "README.md").read_text(encoding="utf-8")
            self.assertIn("Template: incident", readme)

    def test_unknown_template_is_fail_closed(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "il_workspace_init.py"
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws_unknown"
            cp = subprocess.run(
                ["python3", str(script), "--out", str(ws), "--template", "unknown"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            output = (cp.stdout or "") + (cp.stderr or "")
            self.assertEqual(cp.returncode, 1)
            self.assertIn("unknown template", output)


if __name__ == "__main__":
    unittest.main()
