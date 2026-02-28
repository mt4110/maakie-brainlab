import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s32_evidence_trend_index_v7.py"
    spec = importlib.util.spec_from_file_location("s32_evidence_trend_index_v7", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestS32EvidenceTrendIndexV7(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_infer_status(self):
        self.assertEqual(self.m._infer_status({"status": "PASS"}), "PASS")
        self.assertEqual(self.m._infer_status({"status": "ERROR"}), "WARN")
        self.assertEqual(self.m._infer_status({}), "WARN")

    def test_script_writes_latest_and_history(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "ops" / "s32_evidence_trend_index_v7.py"
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "evidence"
            cp = subprocess.run(
                ["python3", str(script), "--out-dir", str(out_dir)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            output = (cp.stdout or "") + (cp.stderr or "")
            self.assertEqual(cp.returncode, 1, msg=output)  # missing evidence => WARN
            payload = json.loads((out_dir / "evidence_trend_index_v7_latest.json").read_text(encoding="utf-8"))
            self.assertEqual(payload.get("schema"), "S32_EVIDENCE_TREND_INDEX_V7")
            self.assertTrue((out_dir / "evidence_trend_history_v7.json").exists())


if __name__ == "__main__":
    unittest.main()
