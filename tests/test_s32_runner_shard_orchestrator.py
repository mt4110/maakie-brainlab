import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.il_thread_runner_v2 import run_thread_runner


class TestS32RunnerShardOrchestrator(unittest.TestCase):
    def _request(self, word: str) -> dict:
        return {
            "schema": "IL_COMPILE_REQUEST_v1",
            "request_text": f"find {word}",
            "context": {"keywords": [word]},
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
            {"id": "o1", "request": self._request("alpha")},
            {"id": "o2", "request": self._request("beta")},
            {"id": "o3", "request": self._request("alpha")},
            {"id": "o4", "request": self._request("beta")},
        ]
        with open(path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def test_orchestrator_matches_single_run_summary(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "il_thread_runner_v2_orchestrator.py"

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cases = tmp_path / "cases.jsonl"
            single_out = tmp_path / "single"
            orchestrated_out = tmp_path / "orchestrated"
            self._write_cases(cases)

            rc_single = run_thread_runner(cases_path=cases, mode="validate-only", out_dir=single_out)
            self.assertEqual(rc_single, 0)
            single_summary = json.loads((single_out / "summary.json").read_text(encoding="utf-8"))

            cp = subprocess.run(
                [
                    "python3",
                    str(script),
                    "--cases",
                    str(cases),
                    "--mode",
                    "validate-only",
                    "--out",
                    str(orchestrated_out),
                    "--shard-count",
                    "2",
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            output = (cp.stdout or "") + (cp.stderr or "")
            self.assertEqual(cp.returncode, 0, msg=output)

            orchestrated = json.loads((orchestrated_out / "summary.orchestrator.json").read_text(encoding="utf-8"))
            merged = orchestrated.get("merged_summary", {})
            self.assertEqual(orchestrated.get("status"), "OK")
            self.assertEqual(merged.get("total_cases"), single_summary.get("total_cases"))
            self.assertEqual(merged.get("compile_ok_count"), single_summary.get("compile_ok_count"))
            self.assertEqual(merged.get("compile_error_count"), single_summary.get("compile_error_count"))


if __name__ == "__main__":
    unittest.main()
