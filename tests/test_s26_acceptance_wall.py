import importlib.util
import tempfile
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s26_acceptance_wall.py"
    spec = importlib.util.spec_from_file_location("s26_acceptance_wall", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S26AcceptanceWallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_validate_case(self):
        ok, reason = self.m.validate_case(
            {"id": "A1", "artifact": "x.json", "assertion": {"path": "a", "op": "eq", "value": 1}}
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "")

        ok2, reason2 = self.m.validate_case({"id": "A1", "artifact": "x.json", "assertion": {"op": "eq", "value": 1}})
        self.assertFalse(ok2)
        self.assertIn("path", reason2)

        ok3, reason3 = self.m.validate_case(
            {"id": "A1", "artifact": "../escape.json", "assertion": {"path": "a", "op": "eq", "value": 1}}
        )
        self.assertFalse(ok3)
        self.assertIn("unsafe", reason3)

    def test_resolve_path_and_assertion(self):
        doc = {"summary": {"status": "PASS"}, "items": [{"v": 3}]}
        ok, val = self.m.resolve_path(doc, "summary.status")
        self.assertTrue(ok)
        self.assertEqual(val, "PASS")
        ok2, val2 = self.m.resolve_path(doc, "items.0.v")
        self.assertTrue(ok2)
        self.assertEqual(val2, 3)
        self.assertTrue(self.m.evaluate_assertion(3, "gte", 2))
        self.assertTrue(self.m.evaluate_assertion("abc", "contains", "b"))

    def test_run_case_missing_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_dir = root / "run"
            run_dir.mkdir(parents=True, exist_ok=True)
            out = self.m.run_case(
                repo_root=root,
                case={
                    "id": "A-404",
                    "title": "missing",
                    "artifact": "missing.json",
                    "assertion": {"path": "x", "op": "eq", "value": 1},
                },
                run_dir=run_dir,
            )
            self.assertEqual(out["status"], "FAIL")
            self.assertEqual(out["reason_code"], self.m.REASON_FILE_MISSING)

    def test_run_case_rejects_unsafe_artifact_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_dir = root / "run"
            run_dir.mkdir(parents=True, exist_ok=True)
            out = self.m.run_case(
                repo_root=root,
                case={
                    "id": "A-unsafe",
                    "title": "unsafe",
                    "artifact": "../x.json",
                    "assertion": {"path": "x", "op": "eq", "value": 1},
                },
                run_dir=run_dir,
            )
            self.assertEqual(out["status"], "FAIL")
            self.assertEqual(out["reason_code"], self.m.REASON_ARTIFACT_PATH_UNSAFE)

    def test_run_case_sanitizes_log_name(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_dir = root / "run"
            run_dir.mkdir(parents=True, exist_ok=True)
            artifact = root / "ok.json"
            artifact.write_text('{"summary":{"status":"PASS"}}\n', encoding="utf-8")
            out = self.m.run_case(
                repo_root=root,
                case={
                    "id": "../A-1",
                    "title": "safe-log",
                    "artifact": "ok.json",
                    "assertion": {"path": "summary.status", "op": "eq", "value": "PASS"},
                },
                run_dir=run_dir,
            )
            self.assertEqual(out["status"], "PASS")
            self.assertNotIn("/", out["log_path"])


if __name__ == "__main__":
    unittest.main()
