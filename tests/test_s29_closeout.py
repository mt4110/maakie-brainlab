import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s29_closeout.py"
    spec = importlib.util.spec_from_file_location("s29_closeout", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S29CloseoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_read_json_if_exists_missing(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "none.json"
            self.assertEqual(self.m.read_json_if_exists(p), {})

    def test_write_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "out"
            out_dir.mkdir(parents=True, exist_ok=True)
            self.m.write_failure(
                root,
                out_dir,
                root / "r.json",
                root / "i.json",
                self.m.REASON_READINESS_MISSING,
                ["r1"],
                ["h1"],
            )
            payload = json.loads((out_dir / "closeout_latest.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["status"], "FAIL")
            self.assertEqual(payload["summary"]["reason"], self.m.REASON_READINESS_MISSING)

    def test_derive_unresolved_risks(self):
        risks = self.m.derive_unresolved_risks(
            {
                "slo": {
                    "hard_violations": [{"metric": "notify_delivery_rate"}],
                    "soft_violations": [{"metric": "skip_rate"}],
                    "waived_hard_violations": [{"metric": "unknown_ratio", "waiver_code": "UNKNOWN_RATIO_WITH_ACTIONS"}],
                }
            },
            {"summary": {"warn_count": 2, "failed_count": 0}},
        )
        self.assertTrue(any("notify_delivery_rate" in r for r in risks))
        self.assertTrue(any("skip_rate" in r for r in risks))
        self.assertTrue(any("UNKNOWN_RATIO_WITH_ACTIONS" in r for r in risks))


if __name__ == "__main__":
    unittest.main()
