import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s26_closeout.py"
    spec = importlib.util.spec_from_file_location("s26_closeout", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S26CloseoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_read_json_if_exists_missing(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "no.json"
            self.assertEqual(self.m.read_json_if_exists(p), {})

    def test_phase_to_index_and_count(self):
        self.assertEqual(self.m.phase_to_index("S26-04"), 4)
        self.assertEqual(self.m.phase_to_index("S26-10"), 10)
        self.assertEqual(self.m.phase_to_index("S25-04"), -1)
        rows = [
            {"phase": "S26-01", "present": True},
            {"phase": "S26-04", "present": True},
            {"phase": "S26-05", "present": True},
            {"phase": "S26-10", "present": True},
        ]
        self.assertEqual(self.m.count_present_until(rows, max_index=4), 2)
        self.assertEqual(self.m.count_present_between(rows, min_index=5, max_index=10), 2)

    def test_build_markdown(self):
        payload = {
            "captured_at_utc": "2026-01-01T00:00:00Z",
            "git": {"branch": "b", "head": "h"},
            "summary": {"status": "PASS", "readiness": "READY", "blocked_gates": 0},
            "before_after": {
                "before_scope": "a",
                "after_scope": "b",
                "before_phases_present": 4,
                "after_phases_present": 10,
                "after_failed_count": 0,
                "after_warn_count": 1,
            },
            "unresolved_risks": ["r1"],
            "next_thread_handoff": ["h1"],
            "artifact_names": {"json": "closeout_latest.json"},
        }
        md = self.m.build_markdown(payload)
        self.assertIn("S26-10", md)
        self.assertIn("READY", md)

    def test_write_failure_artifacts_writes_closeout_payload(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            out_dir = repo / "out"
            out_dir.mkdir(parents=True, exist_ok=True)
            readiness = repo / "missing_readiness.json"
            index = repo / "missing_index.json"
            self.m.write_failure_artifacts(
                repo_root=repo,
                out_dir=out_dir,
                readiness_path=readiness,
                index_path=index,
                reason=self.m.REASON_READINESS_MISSING,
                unresolved_risks=["r1"],
                handoff_items=["h1"],
            )
            payload = json.loads((out_dir / "closeout_latest.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["status"], "FAIL")
            self.assertEqual(payload["summary"]["reason"], self.m.REASON_READINESS_MISSING)


if __name__ == "__main__":
    unittest.main()
