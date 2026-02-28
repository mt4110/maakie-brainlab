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
        parsed = parse_args(["--mode", "run"])
        errors = parsed[-2]
        self.assertIn("missing required --cases", errors)
        self.assertIn("missing required --out", errors)

        parsed2 = parse_args(
            ["--cases", "x.jsonl", "--mode", "bad", "--out", "tmp/out"]
        )
        errors2 = parsed2[-2]
        self.assertIn("invalid --mode: bad", errors2)

        parsed3 = parse_args(
            ["--cases", "x.jsonl", "--mode", "run", "--out", "tmp/out", "--entry-timeout-sec", "0"]
        )
        errors3 = parsed3[-2]
        self.assertIn("entry-timeout-sec must be > 0", errors3)

        parsed4 = parse_args(
            ["--cases", "x.jsonl", "--mode", "run", "--out", "tmp/out", "--entry-retries", "-1"]
        )
        errors4 = parsed4[-2]
        self.assertIn("entry-retries must be >= 0", errors4)

        parsed5 = parse_args(
            ["--cases", "x.jsonl", "--mode", "run", "--out", "tmp/out", "--shard-index", "2", "--shard-count", "2"]
        )
        errors5 = parsed5[-2]
        self.assertIn("shard-index must be < shard-count", errors5)

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
            self.assertTrue((out_dir / "cases.partial.jsonl").exists())
            self.assertTrue((out_dir / "summary.partial.json").exists())
            partial_lines = [x for x in (out_dir / "cases.partial.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
            self.assertEqual(len(partial_lines), 2)

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

    def _write_dummy_entry_script(self, path: Path, sleep_first_sec: int = 0) -> None:
        script = f"""#!/usr/bin/env python3
import json
import sys
import time
from pathlib import Path

args = sys.argv[1:]
il_path = args[0]
out_dir = None
i = 1
while i < len(args):
    if args[i] == "--out" and i + 1 < len(args):
        out_dir = args[i + 1]
        i += 2
    elif args[i] == "--fixture-db":
        i += 2
    else:
        i += 1

if out_dir is None:
    print("ERROR: missing --out")
    sys.exit(2)

out = Path(out_dir)
out.mkdir(parents=True, exist_ok=True)
if "0001_" in il_path and {sleep_first_sec} > 0:
    time.sleep({sleep_first_sec})

(out / "il.exec.report.json").write_text(json.dumps({{"schema":"IL_EXEC_REPORT_v1"}}), encoding="utf-8")
print("OK: phase=end STOP=0")
"""
        path.write_text(script, encoding="utf-8")

    def _write_flaky_entry_script(self, path: Path) -> None:
        script = """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

args = sys.argv[1:]
il_path = args[0]
out_dir = None
i = 1
while i < len(args):
    if args[i] == "--out" and i + 1 < len(args):
        out_dir = args[i + 1]
        i += 2
    elif args[i] == "--fixture-db":
        i += 2
    else:
        i += 1

if out_dir is None:
    print("ERROR: missing --out")
    sys.exit(2)

out = Path(out_dir)
out.mkdir(parents=True, exist_ok=True)
marker = out / "first_attempt.marker"
if not marker.exists():
    marker.write_text("1", encoding="utf-8")
    print("OK: phase=end STOP=1")
    sys.exit(0)

(out / "il.exec.report.json").write_text(json.dumps({"schema":"IL_EXEC_REPORT_v1"}), encoding="utf-8")
print("OK: phase=end STOP=0")
"""
        path.write_text(script, encoding="utf-8")

    def test_timeout_does_not_block_next_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cases_path = tmp_path / "cases.jsonl"
            out_dir = tmp_path / "out_timeout"
            entry_script = tmp_path / "dummy_entry.py"
            self._write_dummy_entry_script(entry_script, sleep_first_sec=2)

            rows = [
                {"id": "first_timeout", "request": self._good_request("alpha")},
                {"id": "second_ok", "request": self._good_request("beta")},
            ]
            self._write_cases(cases_path, rows)

            rc = run_thread_runner(
                cases_path=cases_path,
                mode="run",
                out_dir=out_dir,
                entry_timeout_sec=1,
                entry_script=entry_script,
            )
            self.assertEqual(rc, 1)

            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["compile_ok_count"], 2)
            self.assertEqual(summary["entry_error_count"], 1)
            self.assertEqual(summary["entry_ok_count"], 1)

            rows_out = [
                json.loads(line)
                for line in (out_dir / "cases.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(rows_out[0]["entry_status"], "ERROR")
            self.assertIn("E_TIMEOUT", rows_out[0]["entry_error_codes"])
            self.assertEqual(rows_out[1]["entry_status"], "OK")
            self.assertTrue((out_dir / "cases" / "0002_second_ok" / "entry" / "il.exec.report.json").exists())

    def test_retry_recovers_transient_entry_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cases_path = tmp_path / "cases.jsonl"
            out_dir = tmp_path / "out_retry"
            entry_script = tmp_path / "flaky_entry.py"
            self._write_flaky_entry_script(entry_script)

            rows = [{"id": "retry_ok", "request": self._good_request("alpha")}]
            self._write_cases(cases_path, rows)
            rc = run_thread_runner(
                cases_path=cases_path,
                mode="run",
                out_dir=out_dir,
                entry_retries=1,
                entry_script=entry_script,
            )
            self.assertEqual(rc, 0)

            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["entry_ok_count"], 1)
            self.assertEqual(summary["entry_error_count"], 0)
            self.assertEqual(summary["retries_used_count"], 1)

            rows_out = [
                json.loads(line)
                for line in (out_dir / "cases.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(rows_out[0]["entry_status"], "OK")
            self.assertEqual(rows_out[0]["entry_attempts"], 2)
            self.assertTrue((out_dir / "cases" / "0001_retry_ok" / "entry" / "entry.stdout.attempt01.log").exists())
            self.assertTrue((out_dir / "cases" / "0001_retry_ok" / "entry" / "entry.stdout.attempt02.log").exists())

    def test_resume_and_shard_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cases_path = tmp_path / "cases.jsonl"
            out_dir = tmp_path / "out_resume"
            rows = [
                {"id": "r1", "request": self._good_request("alpha")},
                {"id": "r2", "request": self._good_request("beta")},
            ]
            self._write_cases(cases_path, rows)

            rc1 = run_thread_runner(
                cases_path=cases_path,
                mode="validate-only",
                out_dir=out_dir,
                shard_index=0,
                shard_count=2,
            )
            self.assertEqual(rc1, 0)
            summary1 = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary1["total_cases"], 1)

            rc2 = run_thread_runner(
                cases_path=cases_path,
                mode="validate-only",
                out_dir=out_dir,
                resume=True,
            )
            self.assertEqual(rc2, 0)
            summary2 = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary2["total_cases"], 2)

    def test_resume_merges_partial_and_final_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cases_path = tmp_path / "cases.jsonl"
            shard0_dir = tmp_path / "out_shard0"
            shard1_dir = tmp_path / "out_shard1"
            resume_dir = tmp_path / "out_resume_merge"
            rows = [
                {"id": "r1", "request": self._good_request("alpha")},
                {"id": "r2", "request": self._good_request("beta")},
            ]
            self._write_cases(cases_path, rows)

            rc0 = run_thread_runner(
                cases_path=cases_path,
                mode="validate-only",
                out_dir=shard0_dir,
                shard_index=0,
                shard_count=2,
            )
            self.assertEqual(rc0, 0)
            rc1 = run_thread_runner(
                cases_path=cases_path,
                mode="validate-only",
                out_dir=shard1_dir,
                shard_index=1,
                shard_count=2,
            )
            self.assertEqual(rc1, 0)

            row_r1 = json.loads((shard0_dir / "cases.jsonl").read_text(encoding="utf-8").strip())
            row_r2 = json.loads((shard1_dir / "cases.jsonl").read_text(encoding="utf-8").strip())

            resume_dir.mkdir(parents=True, exist_ok=True)
            self._write_cases(resume_dir / "cases.jsonl", [row_r1])
            self._write_cases(resume_dir / "cases.partial.jsonl", [row_r2])

            rc_resume = run_thread_runner(
                cases_path=cases_path,
                mode="validate-only",
                out_dir=resume_dir,
                resume=True,
            )
            self.assertEqual(rc_resume, 0)

            summary = json.loads((resume_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["total_cases"], 2)
            self.assertFalse((resume_dir / "cases" / "0001_r1").exists())
            self.assertFalse((resume_dir / "cases" / "0002_r2").exists())

            out_rows = [
                json.loads(line)
                for line in (resume_dir / "cases.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(sorted(str(r.get("id", "")) for r in out_rows), ["r1", "r2"])

    def test_quarantine_case_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cases_path = tmp_path / "cases.jsonl"
            out_dir = tmp_path / "out_quarantine"
            rows = [
                {"id": "q1", "request": self._good_request("alpha")},
                {"id": "q2", "request": self._good_request("beta")},
            ]
            self._write_cases(cases_path, rows)

            rc = run_thread_runner(
                cases_path=cases_path,
                mode="validate-only",
                out_dir=out_dir,
                excluded_ids={"q1"},
            )
            self.assertEqual(rc, 0)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["quarantined_count"], 1)
            self.assertEqual(summary["compile_skip_count"], 1)
            digest = json.loads((out_dir / "failure_digest.json").read_text(encoding="utf-8"))
            self.assertEqual(digest.get("failure_count"), 0)

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
        self.assertEqual(invalid.returncode, 1)
        self.assertIn("invalid --mode", out)
        self.assertIn("ERROR: il_thread_runner_v2 exit=1", out)


if __name__ == "__main__":
    unittest.main()
