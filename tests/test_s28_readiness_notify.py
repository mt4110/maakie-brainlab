import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


def _load_module():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s28_readiness_notify.py"
    spec = importlib.util.spec_from_file_location("s28_readiness_notify", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S28ReadinessNotifyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_compose_message(self):
        msg = self.m.compose_message(
            "#ops",
            {"summary": {"readiness": "READY", "status": "PASS", "reason_code": "", "blocked_total": 0}},
            {"summary": {"status": "PASS", "reason_code": ""}},
        )
        self.assertIn("channel=#ops", msg)
        self.assertIn("readiness=READY", msg)

    def test_resolve_primary_or_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            primary = root / "primary.json"
            fallback = root / "fallback.json"
            fallback.write_text('{"summary":{"status":"WARN"}}\n', encoding="utf-8")
            doc, resolved, used_fallback = self.m.resolve_primary_or_fallback(primary, fallback)
            self.assertEqual(doc["summary"]["status"], "WARN")
            self.assertEqual(resolved, fallback)
            self.assertTrue(used_fallback)

    def test_deliver_with_retries(self):
        state = {"calls": 0}

        def sender():
            state["calls"] += 1
            if state["calls"] < 3:
                return {"sent": False, "http_status": 500, "response_tail": "", "error": "boom"}
            return {"sent": True, "http_status": 200, "response_tail": "ok", "error": ""}

        out = self.m.deliver_with_retries(sender, max_retries=3, retry_backoff_sec=0.0, sleep_fn=lambda _: None)
        self.assertTrue(out["sent"])
        self.assertEqual(out["attempt_count"], 3)

    def test_compute_delivery_rate(self):
        self.assertIsNone(self.m.compute_delivery_rate(sent=False, attempt_count=0, attempted=False))
        self.assertEqual(self.m.compute_delivery_rate(sent=False, attempt_count=2, attempted=True), 0.0)
        self.assertEqual(self.m.compute_delivery_rate(sent=True, attempt_count=2, attempted=True), 0.5)

    def test_delivery_state(self):
        self.assertEqual(self.m.delivery_state(sent=False, attempt_count=0, attempted=False), "NOT_ATTEMPTED")
        self.assertEqual(self.m.delivery_state(sent=False, attempt_count=1, attempted=True), "FAILED")
        self.assertEqual(self.m.delivery_state(sent=True, attempt_count=1, attempted=True), "SENT")

    def test_send_requested_without_webhook_keeps_not_attempted(self):
        root = Path(__file__).resolve().parents[1]
        script = root / "scripts" / "ops" / "s28_readiness_notify.py"
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            out_dir = tdir / "out"
            readiness = tdir / "readiness.json"
            schedule = tdir / "schedule.json"
            readiness.write_text(
                json.dumps({"summary": {"readiness": "WARN_ONLY", "status": "WARN", "reason_code": "SOFT_SLO_WARN", "blocked_total": 1}}) + "\n",
                encoding="utf-8",
            )
            schedule.write_text(json.dumps({"summary": {"status": "PASS", "reason_code": ""}}) + "\n", encoding="utf-8")

            env = os.environ.copy()
            env.pop("S28_READINESS_WEBHOOK_URL", None)
            py_path = f"{root / 'src'}:{root}"
            if env.get("PYTHONPATH"):
                py_path = f"{py_path}:{env['PYTHONPATH']}"
            env["PYTHONPATH"] = py_path
            cp = subprocess.run(
                [
                    "python3",
                    str(script),
                    "--send",
                    "--out-dir",
                    str(out_dir),
                    "--readiness-json",
                    str(readiness),
                    "--schedule-json",
                    str(schedule),
                    "--obs-root",
                    str(tdir / "obs"),
                ],
                cwd=str(root),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)

            payload = json.loads((out_dir / "readiness_notify_latest.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["reason_code"], self.m.REASON_WEBHOOK_NOT_CONFIGURED)
            self.assertFalse(payload["notification"]["attempted"])
            self.assertEqual(payload["notification"]["delivery_state"], "NOT_ATTEMPTED")
            self.assertIsNone(payload["notification"]["delivery_rate"])


if __name__ == "__main__":
    unittest.main()
