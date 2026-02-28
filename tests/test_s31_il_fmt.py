import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestS31IlFmt(unittest.TestCase):
    def test_check_detects_non_canonical_and_write_fixes(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "il_fmt.py"

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            target = tmp_path / "sample.json"
            target.write_text('{"b": 2, "a": 1}\n', encoding="utf-8")

            check_before = subprocess.run(
                ["python3", str(script), "--check", str(target)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            out_before = (check_before.stdout or "") + (check_before.stderr or "")
            self.assertEqual(check_before.returncode, 1)
            self.assertIn("non_canonical", out_before)

            write_run = subprocess.run(
                ["python3", str(script), "--write", str(target)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            out_write = (write_run.stdout or "") + (write_run.stderr or "")
            self.assertEqual(write_run.returncode, 0)
            self.assertIn("formatted", out_write)

            content = target.read_text(encoding="utf-8")
            self.assertEqual(content, '{"a":1,"b":2}')

            check_after = subprocess.run(
                ["python3", str(script), "--check", str(target)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            out_after = (check_after.stdout or "") + (check_after.stderr or "")
            self.assertEqual(check_after.returncode, 0)
            self.assertIn("canonical", out_after)

    def test_directory_and_glob_resolution(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "il_fmt.py"

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            d = tmp_path / "dir"
            d.mkdir(parents=True)
            (d / "a.json").write_text('{"z": 1, "a": 2}', encoding="utf-8")
            (d / "b.json").write_text('{"k": [2,1]}', encoding="utf-8")

            run_dir = subprocess.run(
                ["python3", str(script), "--write", str(d)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(run_dir.returncode, 0)

            run_glob = subprocess.run(
                ["python3", str(script), "--check", str(d / "*.json")],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(run_glob.returncode, 0)

    def test_invalid_json_fails(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "il_fmt.py"

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "broken.json"
            target.write_text('{"a": 1', encoding="utf-8")

            run = subprocess.run(
                ["python3", str(script), "--check", str(target)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            out = (run.stdout or "") + (run.stderr or "")
            self.assertEqual(run.returncode, 1)
            self.assertIn("json_parse_failed", out)


if __name__ == "__main__":
    unittest.main()
