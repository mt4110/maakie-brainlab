import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s27_provider_canary_ops.py"
    spec = importlib.util.spec_from_file_location("s27_provider_canary_ops", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S27ProviderCanaryOpsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_validate_config(self):
        cfg = {
            "schema_version": "s26-provider-canary-v1",
            "ops_schema_version": "s27-provider-canary-ops-v1",
            "provider": {"id": "x"},
            "policy": {"timeout_sec": 3, "max_retries": 0, "retry_backoff_ms": 0, "jitter_ms": 0, "circuit_open_sec": 1, "max_inflight": 1, "retryable_reason_codes": ["TIMEOUT"], "non_retryable_reason_codes": ["AUTH_ERROR"]},
            "rollback": {"command": "python3 noop.py"},
            "cases": [{"id": "c1", "prompt": "pong", "must_pass": True}],
            "ops_policy": {"window_size": 5, "skip_rate_warn_threshold": 0.4, "max_history_entries": 10},
        }
        self.assertEqual(self.m.validate_config(cfg), "")

    def test_window_metrics(self):
        runs = [
            {"status": "PASS"},
            {"status": "SKIP"},
            {"status": "FAIL"},
            {"status": "SKIP"},
        ]
        out = self.m.window_metrics(runs, 3)
        self.assertEqual(out["window_count"], 3)
        self.assertGreater(out["skip_rate"], 0)

    def test_decide_ops_status(self):
        out = self.m.decide_ops_status("PASS", 0, {"skip_rate": 0.8, "fail_runs": 0}, 0.4, True)
        self.assertEqual(out["status"], "WARN")
        self.assertEqual(out["reason_code"], self.m.REASON_SKIP_RATE_HIGH)

    def test_main_handles_invalid_config(self):
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "bad.toml"
            out_dir = Path(td) / "out"
            cfg.write_text('schema_version = "s26-provider-canary-v1"\n', encoding="utf-8")
            cp = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "scripts" / "ops" / "s27_provider_canary_ops.py"),
                    "--config",
                    str(cfg),
                    "--out-dir",
                    str(out_dir),
                ],
                cwd=str(repo_root),
                env={**os.environ, "PYTHONPATH": "./src:."},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 1)
            payload = json.loads((out_dir / "provider_canary_ops_latest.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["reason_code"], self.m.REASON_CONFIG_INVALID)


if __name__ == "__main__":
    unittest.main()
