import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestS31IlLint(unittest.TestCase):
    def test_lint_ok_and_error(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "il_lint.py"
        good = repo_root / "tests" / "fixtures" / "il_exec" / "il_min.json"

        with tempfile.TemporaryDirectory() as tmp:
            out_report = Path(tmp) / "lint.good.json"
            cp = subprocess.run(
                ["python3", str(script), "--il", str(good), "--out", str(out_report)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            out = (cp.stdout or "") + (cp.stderr or "")
            self.assertEqual(cp.returncode, 0)
            self.assertIn("lint_status=OK", out)
            report = json.loads(out_report.read_text(encoding="utf-8"))
            self.assertEqual(report.get("schema"), "IL_LINT_REPORT_v1")
            self.assertEqual(report.get("status"), "OK")

            bad = Path(tmp) / "bad.json"
            bad.write_text('{"il":null,"meta":{"version":"il_contract_v1"},"evidence":{}}', encoding="utf-8")
            bad_report = Path(tmp) / "lint.bad.json"
            cp_bad = subprocess.run(
                ["python3", str(script), "--il", str(bad), "--out", str(bad_report)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            out_bad = (cp_bad.stdout or "") + (cp_bad.stderr or "")
            self.assertEqual(cp_bad.returncode, 1)
            self.assertIn("lint_summary", out_bad)
            report_bad = json.loads(bad_report.read_text(encoding="utf-8"))
            self.assertEqual(report_bad.get("status"), "ERROR")
            self.assertGreater(report_bad.get("error_count", 0), 0)


if __name__ == "__main__":
    unittest.main()
