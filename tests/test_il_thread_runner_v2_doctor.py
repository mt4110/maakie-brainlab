import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.il_thread_runner_v2 import run_thread_runner


class TestILThreadRunnerV2Doctor(unittest.TestCase):
    def _good_request(self, text: str = "Find alpha in greek docs") -> dict:
        return {
            "schema": "IL_COMPILE_REQUEST_v1",
            "request_text": text,
            "context": {"keywords": ["alpha", "greek"]},
            "constraints": {
                "allowed_opcodes": ["SEARCH_TERMS", "RETRIEVE", "ANSWER", "CITE"],
                "forbidden_keys": [],
                "max_steps": 4,
            },
            "artifact_pointers": [{"path": "tests/fixtures/il_exec/retrieve_db.json"}],
            "determinism": {"temperature": 0.0, "top_p": 1.0, "seed": 7, "stream": False},
        }

    def _write_cases(self, path: Path) -> None:
        rows = [
            {"id": "d1", "request": self._good_request("alpha")},
            {"id": "d2", "request": self._good_request("beta")},
        ]
        with open(path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def test_doctor_ok_for_validate_only_output(self):
        repo_root = Path(__file__).resolve().parent.parent
        doctor = repo_root / "scripts" / "il_thread_runner_v2_doctor.py"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cases = tmp_path / "cases.jsonl"
            out_dir = tmp_path / "run_out"
            self._write_cases(cases)
            rc = run_thread_runner(cases_path=cases, mode="validate-only", out_dir=out_dir)
            self.assertEqual(rc, 0)

            cp = subprocess.run(
                ["python3", str(doctor), "--run-dir", str(out_dir)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            out = (cp.stdout or "") + (cp.stderr or "")
            self.assertEqual(cp.returncode, 0)
            self.assertIn("doctor_summary status=OK", out)
            self.assertIn("OK: il_thread_runner_v2_doctor exit=0", out)

    def test_doctor_errors_for_missing_files(self):
        repo_root = Path(__file__).resolve().parent.parent
        doctor = repo_root / "scripts" / "il_thread_runner_v2_doctor.py"
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "empty_run"
            out_dir.mkdir(parents=True, exist_ok=True)
            cp = subprocess.run(
                ["python3", str(doctor), "--run-dir", str(out_dir)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            out = (cp.stdout or "") + (cp.stderr or "")
            self.assertEqual(cp.returncode, 1)
            self.assertIn("missing summary.json", out)
            self.assertIn("ERROR: il_thread_runner_v2_doctor exit=1", out)


if __name__ == "__main__":
    unittest.main()
