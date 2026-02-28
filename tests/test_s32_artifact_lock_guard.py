import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from typing import Optional

from scripts.il_thread_runner_v2 import run_thread_runner


class TestS32ArtifactLockGuard(unittest.TestCase):
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

    def _write_cases(self, path: Path) -> None:
        rows = [{"id": "l1", "request": self._request("alpha")}]
        with open(path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _set_env(self, key: str, value: str):
        old = os.environ.get(key)
        os.environ[key] = value
        return old

    def _restore_env(self, key: str, old: Optional[str]):
        if old is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old

    def test_lock_timeout_returns_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cases = tmp_path / "cases.jsonl"
            out_dir = tmp_path / "out"
            self._write_cases(cases)
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / ".artifact.lock.json").write_text('{"owner":"test"}', encoding="utf-8")

            old_timeout = self._set_env("IL_THREAD_LOCK_TIMEOUT_SEC", "1")
            old_stale = self._set_env("IL_THREAD_LOCK_STALE_SEC", "999")
            try:
                rc = run_thread_runner(cases_path=cases, mode="validate-only", out_dir=out_dir)
            finally:
                self._restore_env("IL_THREAD_LOCK_TIMEOUT_SEC", old_timeout)
                self._restore_env("IL_THREAD_LOCK_STALE_SEC", old_stale)

            self.assertEqual(rc, 1)

    def test_stale_lock_is_cleaned_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cases = tmp_path / "cases.jsonl"
            out_dir = tmp_path / "out"
            self._write_cases(cases)
            out_dir.mkdir(parents=True, exist_ok=True)
            lock = out_dir / ".artifact.lock.json"
            lock.write_text('{"owner":"test"}', encoding="utf-8")
            old_mtime = time.time() - 60
            os.utime(lock, (old_mtime, old_mtime))

            old_timeout = self._set_env("IL_THREAD_LOCK_TIMEOUT_SEC", "1")
            old_stale = self._set_env("IL_THREAD_LOCK_STALE_SEC", "1")
            try:
                rc = run_thread_runner(cases_path=cases, mode="validate-only", out_dir=out_dir)
            finally:
                self._restore_env("IL_THREAD_LOCK_TIMEOUT_SEC", old_timeout)
                self._restore_env("IL_THREAD_LOCK_STALE_SEC", old_stale)

            self.assertEqual(rc, 0)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary.get("total_cases"), 1)
            self.assertFalse(lock.exists())


if __name__ == "__main__":
    unittest.main()
