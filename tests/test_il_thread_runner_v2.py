import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.il_thread_runner_v2 import load_cases, parse_args, run_thread_runner


class TestILThreadRunnerV2(unittest.TestCase):
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

    def _bad_request_temperature(self) -> dict:
        req = self._good_request("search beta")
        req["determinism"]["temperature"] = 0.2
        return req

    def _write_cases(self, path: Path, rows: list[dict]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _sha256_file(self, path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def test_parse_args_validation(self):
        _, _, _, _, _, _, _, _, errors, _ = parse_args(["--mode", "run"])
        self.assertIn("missing required --cases", errors)
        self.assertIn("missing required --out", errors)

        _, _, _, _, _, _, _, _, errors2, _ = parse_args(
            ["--cases", "x.jsonl", "--mode", "bad", "--out", "tmp/out"]
        )
        self.assertIn("invalid --mode: bad", errors2)

    def test_load_cases_collects_schema_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            cases = Path(tmp) / "cases.jsonl"
            cases.write_text(
                '\n'.join(
                    [
                        '{"id":"ok","request":{"schema":"IL_COMPILE_REQUEST_v1"}}',
                        '{"id":"","request":{}}',
                        '{"id":"ng","request":"not-object"}',
                        '{invalid json}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            rows = load_cases(cases)
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]["id"], "ok")
            self.assertEqual(rows[0]["errors"], [])
            self.assertTrue(rows[1]["errors"])
            self.assertTrue(rows[2]["errors"])
            self.assertTrue(rows[3]["errors"])
            self.assertEqual(rows[0]["fixture_db"], None)

    def test_validate_only_skips_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cases_path = tmp_path / "cases.jsonl"
            out_dir = tmp_path / "out_validate"
            rows = [
                {"id": "c1", "request": self._good_request("Find alpha")},
                {"id": "c2", "request": self._good_request("Find beta")},
            ]
            self._write_cases(cases_path, rows)

            rc = run_thread_runner(cases_path=cases_path, mode="validate-only", out_dir=out_dir)
            self.assertEqual(rc, 0)

            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["schema"], "IL_THREAD_RUNNER_V2_SUMMARY_v1")
            self.assertEqual(summary["total_cases"], 2)
            self.assertEqual(summary["compile_ok_count"], 2)
            self.assertEqual(summary["entry_skip_count"], 2)
            self.assertEqual(summary["entry_ok_count"], 0)
            self.assertEqual(summary["error_count"], 0)

            case0 = out_dir / "cases" / "0001_c1"
            case1 = out_dir / "cases" / "0002_c2"
            self.assertTrue((case0 / "compile" / "il.compiled.json").exists())
            self.assertTrue((case1 / "compile" / "il.compiled.json").exists())
            self.assertFalse((case0 / "entry").exists())
            self.assertFalse((case1 / "entry").exists())

    def test_run_executes_entry_for_compile_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cases_path = tmp_path / "cases.jsonl"
            out_dir = tmp_path / "out_run"

            rows = [
                {
                    "id": "run_ok",
                    "request": self._good_request("Find alpha"),
                    "fixture_db": "tests/fixtures/il_exec/retrieve_db.json",
                }
            ]
            self._write_cases(cases_path, rows)
            rc = run_thread_runner(cases_path=cases_path, mode="run", out_dir=out_dir)
            self.assertEqual(rc, 0)

            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["compile_ok_count"], 1)
            self.assertEqual(summary["entry_ok_count"], 1)
            self.assertEqual(summary["entry_error_count"], 0)

            case_dir = out_dir / "cases" / "0001_run_ok"
            self.assertTrue((case_dir / "entry" / "il.exec.report.json").exists())

    def test_fail_closed_when_compile_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cases_path = tmp_path / "cases.jsonl"
            out_dir = tmp_path / "out_fail_closed"

            rows = [
                {"id": "bad_compile", "request": self._bad_request_temperature()},
                {
                    "id": "good_compile",
                    "request": self._good_request("search alpha"),
                    "fixture_db": "tests/fixtures/il_exec/retrieve_db.json",
                },
            ]
            self._write_cases(cases_path, rows)

            rc = run_thread_runner(cases_path=cases_path, mode="run", out_dir=out_dir)
            self.assertEqual(rc, 1)

            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["compile_error_count"], 1)
            self.assertEqual(summary["entry_skip_count"], 1)
            self.assertEqual(summary["entry_ok_count"], 1)
            self.assertEqual(summary["error_count"], 1)

            bad_case = out_dir / "cases" / "0001_bad_compile"
            self.assertTrue((bad_case / "compile" / "il.compile.error.json").exists())
            self.assertFalse((bad_case / "entry").exists())

    def test_duplicate_case_id_is_error_but_continues(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cases_path = tmp_path / "cases.jsonl"
            out_dir = tmp_path / "out_dup"
            rows = [
                {"id": "dup", "request": self._good_request("a alpha")},
                {"id": "dup", "request": self._good_request("b beta")},
            ]
            self._write_cases(cases_path, rows)

            rc = run_thread_runner(cases_path=cases_path, mode="validate-only", out_dir=out_dir)
            self.assertEqual(rc, 1)

            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["total_cases"], 2)
            self.assertEqual(summary["compile_error_count"], 1)
            self.assertEqual(summary["compile_ok_count"], 1)

    def test_determinism_cases_jsonl_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cases_path = tmp_path / "cases.jsonl"
            out1 = tmp_path / "run1"
            out2 = tmp_path / "run2"
            rows = [
                {"id": "c1", "request": self._good_request("alpha")},
                {"id": "c2", "request": self._good_request("beta")},
            ]
            self._write_cases(cases_path, rows)

            rc1 = run_thread_runner(cases_path=cases_path, mode="validate-only", out_dir=out1)
            rc2 = run_thread_runner(cases_path=cases_path, mode="validate-only", out_dir=out2)
            self.assertEqual(rc1, 0)
            self.assertEqual(rc2, 0)

            s1 = json.loads((out1 / "summary.json").read_text(encoding="utf-8"))
            s2 = json.loads((out2 / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(s1["sha256_cases_jsonl"], s2["sha256_cases_jsonl"])
            self.assertEqual(self._sha256_file(out1 / "cases.jsonl"), self._sha256_file(out2 / "cases.jsonl"))

    def test_cli_help_and_invalid_mode(self):
        repo_root = Path(__file__).resolve().parent.parent
        runner = repo_root / "scripts" / "il_thread_runner_v2.py"

        help_run = subprocess.run(
            ["python3", str(runner), "--help"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(help_run.returncode, 0)
        self.assertIn("usage:", (help_run.stdout or "") + (help_run.stderr or ""))

        invalid = subprocess.run(
            ["python3", str(runner), "--cases", "x", "--mode", "bad", "--out", "y"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        out = (invalid.stdout or "") + (invalid.stderr or "")
        self.assertIn("invalid --mode", out)
        self.assertIn("ERROR: il_thread_runner_v2 exit=1", out)


if __name__ == "__main__":
    unittest.main()
