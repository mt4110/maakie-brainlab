import json
import tempfile
import unittest
from pathlib import Path

from scripts.il_thread_runner_v2 import run_thread_runner


class TestS32RetryPolicyMatrix(unittest.TestCase):
    def _request(self, text: str = "alpha") -> dict:
        return {
            "schema": "IL_COMPILE_REQUEST_v1",
            "request_text": text,
            "context": {"keywords": ["alpha"]},
            "constraints": {
                "allowed_opcodes": ["SEARCH_TERMS", "RETRIEVE", "ANSWER", "CITE"],
                "forbidden_keys": [],
                "max_steps": 4,
            },
            "artifact_pointers": [{"path": "tests/fixtures/il_exec/retrieve_db.json"}],
            "determinism": {"temperature": 0.0, "top_p": 1.0, "seed": 7, "stream": False},
        }

    def _write_cases(self, path: Path) -> None:
        rows = [{"id": "r1", "request": self._request("alpha")}]
        with open(path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _write_entry_protocol_script(self, path: Path) -> None:
        path.write_text(
            """#!/usr/bin/env python3
import sys
print("unexpected output without stop marker")
sys.exit(0)
""",
            encoding="utf-8",
        )

    def _write_flaky_return_code_script(self, path: Path) -> None:
        path.write_text(
            """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

args = sys.argv[1:]
out_dir = None
i = 0
while i < len(args):
    if args[i] == "--out" and i + 1 < len(args):
        out_dir = args[i + 1]
        i += 2
    elif args[i] == "--fixture-db":
        i += 2
    else:
        i += 1
if out_dir is None:
    sys.exit(2)
out = Path(out_dir)
out.mkdir(parents=True, exist_ok=True)
marker = out / "first_attempt.marker"
if not marker.exists():
    marker.write_text("1", encoding="utf-8")
    print("ERROR: simulated returncode failure")
    sys.exit(1)
(out / "il.exec.report.json").write_text(json.dumps({"schema":"IL_EXEC_REPORT_v1"}), encoding="utf-8")
print("OK: phase=end STOP=0")
""",
            encoding="utf-8",
        )

    def _write_entry_stop_script(self, path: Path) -> None:
        path.write_text(
            """#!/usr/bin/env python3
import sys
print("OK: phase=end STOP=1")
sys.exit(0)
""",
            encoding="utf-8",
        )

    def test_non_retriable_error_stops_without_extra_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cases = tmp_path / "cases.jsonl"
            out = tmp_path / "out_non_retriable"
            entry_script = tmp_path / "entry_stop.py"
            self._write_cases(cases)
            self._write_entry_protocol_script(entry_script)

            rc = run_thread_runner(
                cases_path=cases,
                mode="run",
                out_dir=out,
                entry_retries=3,
                entry_script=entry_script,
            )
            self.assertEqual(rc, 1)
            summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary.get("retries_used_count"), 0)
            rows = [json.loads(x) for x in (out / "cases.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
            self.assertEqual(rows[0].get("entry_attempts"), 1)
            self.assertEqual(rows[0].get("entry_error_reason"), "entry_missing_stop_marker")

    def test_retriable_error_retries_and_recovers(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cases = tmp_path / "cases.jsonl"
            out = tmp_path / "out_retriable"
            entry_script = tmp_path / "entry_flaky.py"
            self._write_cases(cases)
            self._write_flaky_return_code_script(entry_script)

            rc = run_thread_runner(
                cases_path=cases,
                mode="run",
                out_dir=out,
                entry_retries=2,
                entry_script=entry_script,
            )
            self.assertEqual(rc, 0)
            summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary.get("retries_used_count"), 1)
            self.assertEqual(summary.get("retry_attempts_total"), 1)
            rows = [json.loads(x) for x in (out / "cases.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
            self.assertEqual(rows[0].get("entry_status"), "OK")
            self.assertEqual(rows[0].get("entry_attempts"), 2)

    def test_entry_stop_is_non_retriable(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cases = tmp_path / "cases.jsonl"
            out = tmp_path / "out_stop_non_retriable"
            entry_script = tmp_path / "entry_stop_once.py"
            self._write_cases(cases)
            self._write_entry_stop_script(entry_script)

            rc = run_thread_runner(
                cases_path=cases,
                mode="run",
                out_dir=out,
                entry_retries=3,
                entry_script=entry_script,
            )
            self.assertEqual(rc, 1)
            rows = [json.loads(x) for x in (out / "cases.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
            self.assertEqual(rows[0].get("entry_attempts"), 1)
            self.assertEqual(rows[0].get("entry_error_codes"), ["E_ENTRY_STOP"])


if __name__ == "__main__":
    unittest.main()
