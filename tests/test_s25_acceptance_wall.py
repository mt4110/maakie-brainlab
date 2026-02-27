import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s25_acceptance_wall.py"
    spec = importlib.util.spec_from_file_location("s25_acceptance_wall", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S25AcceptanceWallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_validate_case(self):
        ok, reason = self.m.validate_case({"id": "A01", "command": "echo hi"})
        self.assertTrue(ok)
        self.assertEqual(reason, "")

        ok2, reason2 = self.m.validate_case({"id": "A01"})
        self.assertFalse(ok2)
        self.assertIn("missing command", reason2)

        ok3, reason3 = self.m.validate_case({"id": "A01", "command": "echo hi", "pass_regex": "("})
        self.assertFalse(ok3)
        self.assertIn("invalid pass_regex", reason3)

    def test_evaluate_case_rc_and_regex(self):
        case = {"must_pass": True, "pass_regex": "OK: done"}
        status, reason = self.m.evaluate_case(case, rc=0, output="OK: done\n")
        self.assertEqual(status, "PASS")
        self.assertEqual(reason, "")

        status2, reason2 = self.m.evaluate_case(case, rc=1, output="OK: done\n")
        self.assertEqual(status2, "FAIL")
        self.assertEqual(reason2, self.m.REASON_RC_NONZERO)

        status3, reason3 = self.m.evaluate_case(case, rc=0, output="no match\n")
        self.assertEqual(status3, "FAIL")
        self.assertEqual(reason3, self.m.REASON_PASS_REGEX_MISSING)

        bad_case = {"must_pass": True, "pass_regex": "("}
        status4, reason4 = self.m.evaluate_case(bad_case, rc=0, output="anything\n")
        self.assertEqual(status4, "FAIL")
        self.assertEqual(reason4, self.m.REASON_PASS_REGEX_INVALID)

    def test_load_cases(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "cases.json"
            p.write_text(
                json.dumps(
                    {
                        "schema_version": "s25-acceptance-cases-v1",
                        "cases": [{"id": "A01", "command": "echo hi"}],
                    }
                ),
                encoding="utf-8",
            )
            schema, cases = self.m.load_cases(p)
            self.assertEqual(schema, "s25-acceptance-cases-v1")
            self.assertEqual(len(cases), 1)
            self.assertEqual(cases[0]["id"], "A01")

    def test_run_case_command_timeout_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            exc = subprocess.TimeoutExpired(cmd=["bash"], timeout=1, output=b"partial", stderr=b"stderr")
            with patch("subprocess.run", side_effect=exc):
                rc, out = self.m.run_case_command("sleep 9", repo_root=Path(td), timeout_sec=1)
        self.assertEqual(rc, 124)
        self.assertIn("partial", out)
        self.assertIn("stderr", out)
        self.assertIn("timeout", out)


if __name__ == "__main__":
    unittest.main()
