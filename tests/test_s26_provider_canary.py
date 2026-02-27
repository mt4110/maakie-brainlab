import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def _load_module():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s26_provider_canary.py"
    spec = importlib.util.spec_from_file_location("s26_provider_canary", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S26ProviderCanaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_validate_config_ok(self):
        cfg = {
            "schema_version": "s26-provider-canary-v1",
            "provider": {
                "id": "x",
                "base_url_env": "BASE",
                "api_key_env": "KEY",
                "model_env": "MODEL",
                "path": "/v1/chat/completions",
            },
            "policy": {
                "timeout_sec": 5,
                "max_retries": 2,
                "retry_backoff_ms": 100,
                "jitter_ms": 0,
                "circuit_open_sec": 10,
                "max_inflight": 1,
                "retryable_reason_codes": ["TIMEOUT", "NETWORK_ERROR"],
                "non_retryable_reason_codes": ["AUTH_ERROR"],
            },
            "rollback": {"command": "python3 x.py"},
            "cases": [{"id": "c1", "prompt": "pong", "expect_substring": "pong", "must_pass": True}],
        }
        ok, reason = self.m.validate_config(cfg)
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    def test_validate_config_rejects_bad_schema(self):
        cfg = {"schema_version": "unknown"}
        ok, reason = self.m.validate_config(cfg)
        self.assertFalse(ok)
        self.assertIn("schema_version", reason)

    def test_validate_config_rejects_max_inflight_not_one(self):
        cfg = {
            "schema_version": "s26-provider-canary-v1",
            "provider": {
                "id": "x",
                "base_url_env": "BASE",
                "api_key_env": "KEY",
                "model_env": "MODEL",
                "path": "/v1/chat/completions",
            },
            "policy": {
                "timeout_sec": 5,
                "max_retries": 2,
                "retry_backoff_ms": 100,
                "jitter_ms": 0,
                "circuit_open_sec": 10,
                "max_inflight": 2,
                "retryable_reason_codes": ["TIMEOUT", "NETWORK_ERROR"],
                "non_retryable_reason_codes": ["AUTH_ERROR"],
            },
            "rollback": {"command": "python3 x.py"},
            "cases": [{"id": "c1", "prompt": "pong", "expect_substring": "pong", "must_pass": True}],
        }
        ok, reason = self.m.validate_config(cfg)
        self.assertFalse(ok)
        self.assertIn("max_inflight", reason)

    def test_classify_http_reason(self):
        self.assertEqual(self.m.classify_http_reason(429), "HTTP_429")
        self.assertEqual(self.m.classify_http_reason(503), "HTTP_5XX")
        self.assertEqual(self.m.classify_http_reason(401), "AUTH_ERROR")
        self.assertEqual(self.m.classify_http_reason(404), "HTTP_4XX")

    def test_should_retry_respects_non_retryable_codes(self):
        self.assertTrue(self.m.should_retry("TIMEOUT", ["TIMEOUT"], ["AUTH_ERROR"]))
        self.assertFalse(self.m.should_retry("AUTH_ERROR", ["AUTH_ERROR"], ["AUTH_ERROR"]))

    def test_is_must_pass_violation(self):
        self.assertFalse(self.m.is_must_pass_violation({"must_pass": True}, {"status": "PASS"}))
        self.assertTrue(self.m.is_must_pass_violation({"must_pass": True}, {"status": "SKIP"}))
        self.assertFalse(self.m.is_must_pass_violation({"must_pass": False}, {"status": "FAIL"}))

    def test_run_case_with_retry_recovers_after_timeout(self):
        calls = {"n": 0}

        def requester(_url, _headers, _payload, _timeout):
            calls["n"] += 1
            if calls["n"] == 1:
                return {"ok": False, "timeout": True, "status_code": 0, "json": None, "text": "", "error": "timeout"}
            return {
                "ok": True,
                "timeout": False,
                "status_code": 200,
                "json": {"choices": [{"message": {"content": "pong"}}]},
                "text": "",
                "error": "",
            }

        out = self.m.run_case_with_retry(
            case={"id": "c1", "prompt": "Return pong", "expect_substring": "pong", "must_pass": True},
            runtime={"base_url": "http://x", "path": "/v1/chat/completions", "api_key": "k", "model": "m"},
            policy={
                "timeout_sec": 1,
                "max_retries": 1,
                "retry_backoff_ms": 0,
                "jitter_ms": 0,
                "circuit_open_sec": 30,
                "retryable_reason_codes": ["TIMEOUT", "NETWORK_ERROR", "HTTP_429", "HTTP_5XX"],
            },
            requester=requester,
            circuit_state={"open_until": 0.0},
            now_fn=lambda: 0.0,
            sleep_fn=lambda _x: None,
        )
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(len(out["attempts"]), 2)

    def test_run_case_with_retry_opens_circuit_when_exhausted(self):
        circuit = {"open_until": 0.0}

        def requester(_url, _headers, _payload, _timeout):
            return {"ok": False, "timeout": True, "status_code": 0, "json": None, "text": "", "error": "timeout"}

        now = {"t": 100.0}

        def now_fn():
            return now["t"]

        out = self.m.run_case_with_retry(
            case={"id": "c2", "prompt": "ping", "expect_substring": "pong", "must_pass": True},
            runtime={"base_url": "http://x", "path": "/v1/chat/completions", "api_key": "k", "model": "m"},
            policy={
                "timeout_sec": 1,
                "max_retries": 0,
                "retry_backoff_ms": 0,
                "jitter_ms": 0,
                "circuit_open_sec": 20,
                "retryable_reason_codes": ["TIMEOUT", "NETWORK_ERROR"],
            },
            requester=requester,
            circuit_state=circuit,
            now_fn=now_fn,
            sleep_fn=lambda _x: None,
        )
        self.assertEqual(out["status"], "FAIL")
        self.assertEqual(out["reason_code"], "TIMEOUT")
        self.assertGreater(circuit["open_until"], 100.0)

    def test_main_handles_bad_toml_and_writes_artifact(self):
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            bad_cfg = Path(td) / "bad.toml"
            out_dir = Path(td) / "out"
            bad_cfg.write_text("schema_version = [", encoding="utf-8")
            cp = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "scripts" / "ops" / "s26_provider_canary.py"),
                    "--config",
                    str(bad_cfg),
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
            payload = json.loads((out_dir / "provider_canary_latest.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["reason_code"], self.m.REASON_CONFIG_INVALID)

    def test_main_strict_provider_env_writes_failure_artifact(self):
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "canary.toml"
            out_dir = Path(td) / "out"
            cfg.write_text(
                "\n".join(
                    [
                        'schema_version = "s26-provider-canary-v1"',
                        "",
                        "[provider]",
                        'id = "x"',
                        'base_url_env = "MISSING_BASE_URL"',
                        'api_key_env = "MISSING_API_KEY"',
                        'model_env = "MISSING_MODEL"',
                        'path = "/v1/chat/completions"',
                        "",
                        "[policy]",
                        "timeout_sec = 3",
                        "max_retries = 0",
                        "retry_backoff_ms = 0",
                        "jitter_ms = 0",
                        "circuit_open_sec = 1",
                        "max_inflight = 1",
                        'retryable_reason_codes = ["TIMEOUT"]',
                        'non_retryable_reason_codes = ["AUTH_ERROR"]',
                        "",
                        "[rollback]",
                        'command = "python3 noop.py"',
                        "",
                        "[[cases]]",
                        'id = "c1"',
                        'prompt = "pong"',
                        "must_pass = true",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            env = {**os.environ}
            env.pop("MISSING_BASE_URL", None)
            env.pop("MISSING_API_KEY", None)
            env.pop("MISSING_MODEL", None)
            env["PYTHONPATH"] = "./src:."
            cp = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "scripts" / "ops" / "s26_provider_canary.py"),
                    "--config",
                    str(cfg),
                    "--out-dir",
                    str(out_dir),
                    "--strict-provider-env",
                ],
                cwd=str(repo_root),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 1)
            payload = json.loads((out_dir / "provider_canary_latest.json").read_text(encoding="utf-8"))
            expected_reason = (
                self.m.REASON_MISSING_PROVIDER_ENV if getattr(self.m, "tomllib", None) is not None else self.m.REASON_CONFIG_INVALID
            )
            self.assertEqual(payload["summary"]["reason_code"], expected_reason)


if __name__ == "__main__":
    unittest.main()
