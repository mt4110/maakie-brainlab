import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Optional

from src.il_compile import compile_request_bundle
from src.il_model_backend import ModelBackendResponse


class TestILCompile(unittest.TestCase):
    class _FakeModelBackend:
        backend_id = "fake_backend"

        def __init__(self, raw_text: str, target: str = "memory://fake", error: Optional[Exception] = None) -> None:
            self.raw_text = raw_text
            self.target = target
            self.error = error

        def invoke(self, _request) -> ModelBackendResponse:
            if self.error is not None:
                raise self.error
            return ModelBackendResponse(
                raw_text=self.raw_text,
                backend_id=self.backend_id,
                target=self.target,
            )

    def _good_request_payload(self) -> dict:
        return {
            "schema": "IL_COMPILE_REQUEST_v1",
            "request_text": "Please search alpha and beta from greek docs",
            "context": {"keywords": ["alpha", "beta"]},
            "constraints": {
                "allowed_opcodes": ["SEARCH_TERMS", "RETRIEVE", "ANSWER", "CITE"],
                "forbidden_keys": [],
                "max_steps": 4,
            },
            "artifact_pointers": [{"path": "tests/fixtures/il_exec/retrieve_db.json"}],
            "determinism": {"temperature": 0.0, "top_p": 1.0, "seed": 7, "stream": False},
        }

    def test_compile_success_and_il_entry_bridge(self):
        repo_root = Path(__file__).resolve().parent.parent
        compile_script = repo_root / "scripts" / "il_compile.py"
        il_entry_script = repo_root / "scripts" / "il_entry.py"
        fixture_db = repo_root / "tests" / "fixtures" / "il_exec" / "retrieve_db.json"

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            req_path = tmp_path / "request.good.json"
            compile_out = tmp_path / "compile_out"
            exec_out = tmp_path / "exec_out"

            req_payload = self._good_request_payload()
            req_path.write_text(json.dumps(req_payload, ensure_ascii=False, indent=2), encoding="utf-8")

            cp = subprocess.run(
                [
                    "python3",
                    str(compile_script),
                    "--request",
                    str(req_path),
                    "--out",
                    str(compile_out),
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            compile_output = (cp.stdout or "") + (cp.stderr or "")
            self.assertIn("OK: phase=end STOP=0", compile_output)
            self.assertTrue((compile_out / "il.compile.report.json").exists())
            self.assertTrue((compile_out / "il.compile.explain.md").exists())
            self.assertTrue((compile_out / "il.compiled.json").exists())
            self.assertTrue((compile_out / "il.compiled.canonical.json").exists())

            report = json.loads((compile_out / "il.compile.report.json").read_text(encoding="utf-8"))
            self.assertEqual(report.get("status"), "OK")
            self.assertEqual(report.get("error_count"), 0)

            compiled_path = compile_out / "il.compiled.json"
            ep = subprocess.run(
                [
                    "python3",
                    str(il_entry_script),
                    str(compiled_path),
                    "--out",
                    str(exec_out),
                    "--fixture-db",
                    str(fixture_db),
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            entry_output = (ep.stdout or "") + (ep.stderr or "")
            self.assertIn("OK: phase=end STOP=0", entry_output)
            self.assertTrue((exec_out / "il.exec.report.json").exists())

    def test_compile_failure_writes_structured_errors(self):
        repo_root = Path(__file__).resolve().parent.parent
        compile_script = repo_root / "scripts" / "il_compile.py"

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            req_path = tmp_path / "request.bad.json"
            out_dir = tmp_path / "compile_out"

            bad_payload = {
                "schema": "IL_COMPILE_REQUEST_v1",
                "request_text": "alpha",
                "context": {},
                "constraints": {"allowed_opcodes": ["SEARCH_TERMS"], "forbidden_keys": [], "max_steps": 1},
                "artifact_pointers": [],
                "determinism": {"temperature": 0.7, "top_p": 1.0, "seed": 7, "stream": False},
            }
            req_path.write_text(json.dumps(bad_payload, ensure_ascii=False, indent=2), encoding="utf-8")

            cp = subprocess.run(
                [
                    "python3",
                    str(compile_script),
                    "--request",
                    str(req_path),
                    "--out",
                    str(out_dir),
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            output = (cp.stdout or "") + (cp.stderr or "")
            self.assertIn("OK: phase=end STOP=1", output)
            self.assertTrue((out_dir / "il.compile.report.json").exists())
            self.assertTrue((out_dir / "il.compile.explain.md").exists())
            self.assertTrue((out_dir / "il.compile.error.json").exists())
            self.assertFalse((out_dir / "il.compiled.json").exists())

            report = json.loads((out_dir / "il.compile.report.json").read_text(encoding="utf-8"))
            self.assertEqual(report.get("status"), "ERROR")
            self.assertGreater(report.get("error_count", 0), 0)

            err_doc = json.loads((out_dir / "il.compile.error.json").read_text(encoding="utf-8"))
            codes = [e.get("code") for e in err_doc.get("errors", [])]
            self.assertIn("E_NONDETERMINISTIC", codes)

    def test_local_llm_provider_fallback_to_rule_based(self):
        req = self._good_request_payload()

        def failing_adapter(_prompt: str, _model: str, _det: dict) -> str:
            raise RuntimeError("simulated local llm outage")

        bundle = compile_request_bundle(
            req,
            provider="local_llm",
            model="dummy_local_model",
            allow_fallback=True,
            llm_adapter=failing_adapter,
        )
        self.assertEqual(bundle.get("status"), "OK")
        report = bundle.get("report", {})
        self.assertEqual(report.get("provider_requested"), "local_llm")
        self.assertEqual(report.get("provider_selected"), "rule_based")
        self.assertTrue(report.get("fallback_used"))
        self.assertIsNotNone(bundle.get("compiled_output"))
        self.assertIsNotNone(bundle.get("canonical_bytes"))

    def test_local_llm_provider_no_fallback_errors(self):
        req = self._good_request_payload()

        def failing_adapter(_prompt: str, _model: str, _det: dict) -> str:
            raise RuntimeError("simulated local llm outage")

        bundle = compile_request_bundle(
            req,
            provider="local_llm",
            model="dummy_local_model",
            allow_fallback=False,
            llm_adapter=failing_adapter,
        )
        self.assertEqual(bundle.get("status"), "ERROR")
        report = bundle.get("report", {})
        self.assertEqual(report.get("provider_requested"), "local_llm")
        self.assertEqual(report.get("provider_selected"), "local_llm")
        self.assertFalse(report.get("fallback_used"))
        self.assertEqual(bundle.get("raw_response_text"), "LOCAL_LLM_COMPILER: no raw response")
        codes = [e.get("code") for e in bundle.get("errors", [])]
        self.assertIn("E_MODEL", codes)

    def test_local_llm_provider_success_parses_json(self):
        req = self._good_request_payload()

        def ok_adapter(_prompt: str, _model: str, _det: dict) -> str:
            return json.dumps(
                {
                    "il": {
                        "opcodes": [
                            {"op": "SEARCH_TERMS", "args": {}},
                            {"op": "RETRIEVE", "args": {}},
                        ],
                        "search_terms": ["alpha", "beta"],
                    },
                    "meta": {"version": "il_contract_v1", "generator": "dummy_local_model"},
                    "evidence": {"notes": "from adapter"},
                },
                ensure_ascii=False,
            )

        bundle = compile_request_bundle(
            req,
            provider="local_llm",
            model="dummy_local_model",
            allow_fallback=False,
            llm_adapter=ok_adapter,
        )
        self.assertEqual(bundle.get("status"), "OK")
        report = bundle.get("report", {})
        self.assertEqual(report.get("provider_selected"), "local_llm")
        self.assertEqual(report.get("model_backend_requested"), "legacy_callable")
        self.assertEqual(report.get("model_backend_used"), "legacy_callable")
        self.assertFalse(report.get("fallback_used"))
        self.assertTrue(report.get("canonical_sha256"))

    def test_local_llm_provider_accepts_structured_model_backend(self):
        req = self._good_request_payload()
        backend = self._FakeModelBackend(
            json.dumps(
                {
                    "il": {
                        "opcodes": [
                            {"op": "SEARCH_TERMS", "args": {}},
                            {"op": "RETRIEVE", "args": {}},
                        ],
                        "search_terms": ["alpha", "beta"],
                    },
                    "meta": {"version": "il_contract_v1", "generator": "fake_backend"},
                    "evidence": {"notes": "from structured backend"},
                },
                ensure_ascii=False,
            ),
            target="memory://structured",
        )

        bundle = compile_request_bundle(
            req,
            provider="local_llm",
            model="dummy_local_model",
            allow_fallback=False,
            model_backend=backend,
        )
        self.assertEqual(bundle.get("status"), "OK")
        report = bundle.get("report", {})
        self.assertEqual(report.get("provider_selected"), "local_llm")
        self.assertEqual(report.get("model_backend_requested"), "fake_backend")
        self.assertEqual(report.get("model_backend_used"), "fake_backend")
        self.assertEqual(report.get("model_backend_target"), "memory://structured")

    def test_local_llm_unknown_model_backend_falls_back_when_allowed(self):
        req = self._good_request_payload()
        bundle = compile_request_bundle(
            req,
            provider="local_llm",
            model="dummy_local_model",
            allow_fallback=True,
            model_backend_id="not_real_backend",
        )
        self.assertEqual(bundle.get("status"), "OK")
        report = bundle.get("report", {})
        self.assertEqual(report.get("provider_requested"), "local_llm")
        self.assertEqual(report.get("provider_selected"), "rule_based")
        self.assertEqual(report.get("model_backend_requested"), "not_real_backend")
        self.assertTrue(report.get("fallback_used"))

    def test_local_llm_fallback_clears_attempted_backend_report_fields(self):
        req = self._good_request_payload()
        backend = self._FakeModelBackend(
            "",
            target="memory://structured",
            error=RuntimeError("simulated structured backend failure"),
        )
        bundle = compile_request_bundle(
            req,
            provider="local_llm",
            model="dummy_local_model",
            allow_fallback=True,
            model_backend=backend,
        )
        self.assertEqual(bundle.get("status"), "OK")
        report = bundle.get("report", {})
        self.assertEqual(report.get("provider_selected"), "rule_based")
        self.assertEqual(report.get("model_backend_requested"), "fake_backend")
        self.assertEqual(report.get("model_backend_used"), "")
        self.assertEqual(report.get("model_backend_target"), "")
        self.assertTrue(report.get("fallback_used"))

    def test_local_llm_unknown_model_backend_errors_without_fallback(self):
        req = self._good_request_payload()
        bundle = compile_request_bundle(
            req,
            provider="local_llm",
            model="dummy_local_model",
            allow_fallback=False,
            model_backend_id="not_real_backend",
        )
        self.assertEqual(bundle.get("status"), "ERROR")
        report = bundle.get("report", {})
        self.assertEqual(report.get("provider_requested"), "local_llm")
        self.assertEqual(report.get("provider_selected"), "local_llm")
        self.assertEqual(report.get("model_backend_requested"), "not_real_backend")
        codes = [e.get("code") for e in bundle.get("errors", [])]
        self.assertIn("E_BACKEND", codes)

    def test_prompt_profile_affects_report_and_prompt(self):
        req = self._good_request_payload()
        bundle = compile_request_bundle(
            req,
            provider="rule_based",
            prompt_profile="strict_json_v2",
        )
        report = bundle.get("report", {})
        self.assertEqual(report.get("prompt_profile"), "strict_json_v2")
        self.assertEqual(report.get("prompt_template_id"), "il_compile_prompt_strict_json_v2")
        prompt_text = bundle.get("prompt_text", "")
        self.assertIn("Return ONLY one JSON object", prompt_text)
        self.assertEqual(bundle.get("status"), "OK")

    def test_artifact_path_rejects_windows_style_traversal_and_unc(self):
        req = self._good_request_payload()
        req["artifact_pointers"] = [{"path": "..\\secret.txt"}]
        bundle = compile_request_bundle(req)
        self.assertEqual(bundle.get("status"), "ERROR")
        messages = [e.get("message", "") for e in bundle.get("errors", [])]
        self.assertIn("path traversal '..' is forbidden", messages)

        req_unc = self._good_request_payload()
        req_unc["artifact_pointers"] = [{"path": "\\\\server\\share\\x"}]
        bundle_unc = compile_request_bundle(req_unc)
        self.assertEqual(bundle_unc.get("status"), "ERROR")
        unc_messages = [e.get("message", "") for e in bundle_unc.get("errors", [])]
        self.assertIn("absolute path is forbidden", unc_messages)

    def test_cli_requires_out_argument(self):
        repo_root = Path(__file__).resolve().parent.parent
        compile_script = repo_root / "scripts" / "il_compile.py"
        with tempfile.TemporaryDirectory() as tmp:
            req_path = Path(tmp) / "request.good.json"
            req_payload = self._good_request_payload()
            req_path.write_text(json.dumps(req_payload, ensure_ascii=False, indent=2), encoding="utf-8")

            cp = subprocess.run(
                [
                    "python3",
                    str(compile_script),
                    "--request",
                    str(req_path),
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            output = (cp.stdout or "") + (cp.stderr or "")
            self.assertIn("missing required --out", output)
            self.assertIn("usage:", output)


if __name__ == "__main__":
    unittest.main()
