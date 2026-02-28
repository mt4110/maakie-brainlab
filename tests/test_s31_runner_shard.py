import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.il_thread_runner_v2 import run_thread_runner


class TestS31RunnerShard(unittest.TestCase):
    def _req(self, word: str) -> dict:
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
            {"id": "s1", "request": self._req("alpha")},
            {"id": "s2", "request": self._req("beta")},
            {"id": "s3", "request": self._req("alpha")},
            {"id": "s4", "request": self._req("beta")},
        ]
        with open(path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def test_shard_and_merge(self):
        repo_root = Path(__file__).resolve().parent.parent
        merge_script = repo_root / "scripts" / "il_thread_runner_v2_merge.py"

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cases = tmp_path / "cases.jsonl"
            self._write_cases(cases)

            shard0 = tmp_path / "shard0"
            shard1 = tmp_path / "shard1"
            merged = tmp_path / "merged"

            rc0 = run_thread_runner(cases, "validate-only", shard0, shard_index=0, shard_count=2)
            rc1 = run_thread_runner(cases, "validate-only", shard1, shard_index=1, shard_count=2)
            self.assertEqual(rc0, 0)
            self.assertEqual(rc1, 0)

            cp = subprocess.run(
                [
                    "python3",
                    str(merge_script),
                    "--inputs",
                    str(shard0),
                    str(shard1),
                    "--out",
                    str(merged),
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0)
            summary = json.loads((merged / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary.get("total_cases"), 4)


if __name__ == "__main__":
    unittest.main()
