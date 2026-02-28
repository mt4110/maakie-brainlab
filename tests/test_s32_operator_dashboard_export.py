import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.il_thread_runner_v2 import run_thread_runner


class TestS32OperatorDashboardExport(unittest.TestCase):
    def _request(self, text: str) -> dict:
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

    def test_dashboard_export_generates_stable_schema(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "ops" / "s32_operator_dashboard_export.py"

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cases = tmp_path / "cases.jsonl"
            run_dir = tmp_path / "runner_out"
            out_dir = tmp_path / "evidence"
            rows = [
                {"id": "d1", "request": self._request("alpha")},
                {"id": "d2", "request": self._request("beta")},
            ]
            with open(cases, "w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")

            rc = run_thread_runner(cases_path=cases, mode="validate-only", out_dir=run_dir)
            self.assertEqual(rc, 0)

            cp = subprocess.run(
                ["python3", str(script), "--run-dir", str(run_dir), "--out-dir", str(out_dir)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            output = (cp.stdout or "") + (cp.stderr or "")
            self.assertEqual(cp.returncode, 0, msg=output)

            payload = json.loads((out_dir / "operator_dashboard_latest.json").read_text(encoding="utf-8"))
            self.assertEqual(payload.get("schema"), "S32_OPERATOR_DASHBOARD_V1")
            self.assertIn("metrics", payload)
            metrics = payload.get("metrics", {})
            self.assertIn("throughput_cases_per_sec", metrics)
            self.assertIn("success_rate", metrics)
            self.assertIn("skip_breakdown", metrics)
            self.assertIn("retry_rate", metrics)
            self.assertIn("p95_latency_ms", metrics)


if __name__ == "__main__":
    unittest.main()
