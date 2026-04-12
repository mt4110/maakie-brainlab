import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from src.il_model_backend import (
    ModelBackendRequest,
    OpenAICompatModelBackendAdapter,
    invoke_gemma_lab_bridge,
    resolve_local_ui_requested_model_backend,
)


class _FakeResponse:
    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class TestOpenAICompatModelBackendAdapter(unittest.TestCase):
    def _request(self) -> ModelBackendRequest:
        return ModelBackendRequest(
            prompt_text="hello",
            model="dummy-model",
            determinism={"temperature": 0.0, "top_p": 1.0},
        )

    def test_http_success_preserves_local_llama_failure_metadata(self):
        fake_module = types.ModuleType("src.local_llm")

        class FailingLocalLLM:
            def __init__(self, **_kwargs) -> None:
                pass

            def complete(self, *_args, **_kwargs):
                raise RuntimeError("local llama bootstrap failed")

        fake_module.LocalLlamaCppLLM = FailingLocalLLM
        adapter = OpenAICompatModelBackendAdapter(api_base="http://127.0.0.1:11434/v1")

        with patch.dict(sys.modules, {"src.local_llm": fake_module}):
            with patch(
                "requests.post",
                return_value=_FakeResponse({"choices": [{"message": {"content": "ok"}}]}),
            ):
                response = adapter.invoke(self._request())

        self.assertEqual(response.raw_text, "ok")
        self.assertEqual(
            response.metadata.get("local_llama_error"),
            "RuntimeError: local llama bootstrap failed",
        )

    def test_http_failure_surfaces_local_llama_error_context(self):
        fake_module = types.ModuleType("src.local_llm")

        class FailingLocalLLM:
            def __init__(self, **_kwargs) -> None:
                pass

            def complete(self, *_args, **_kwargs):
                raise RuntimeError("local llama bootstrap failed")

        fake_module.LocalLlamaCppLLM = FailingLocalLLM
        adapter = OpenAICompatModelBackendAdapter(api_base="http://127.0.0.1:11434/v1")

        with patch.dict(sys.modules, {"src.local_llm": fake_module}):
            with patch(
                "requests.post",
                side_effect=requests.exceptions.ConnectionError("network down"),
            ):
                with self.assertRaises(RuntimeError) as ctx:
                    adapter.invoke(self._request())

        self.assertIn("network down", str(ctx.exception))
        self.assertIn(
            "local_llama_error=RuntimeError: local llama bootstrap failed",
            str(ctx.exception),
        )


class TestModelBackendHelpers(unittest.TestCase):
    def test_resolve_local_ui_requested_model_backend_prefers_local_backend(self):
        with patch.dict(
            "os.environ",
            {
                "LOCAL_MODEL_BACKEND": "openai_compat",
                "IL_COMPILE_MODEL_BACKEND": "gemma_lab",
            },
            clear=False,
        ):
            self.assertEqual(resolve_local_ui_requested_model_backend(), "openai_compat")

    def test_invoke_gemma_lab_bridge_tolerates_non_json_stdout_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            bridge = tmp_path / "bridge.py"
            bridge.write_text("#!/usr/bin/env python3\n", encoding="utf-8")

            class _FailedProc:
                returncode = 1
                stdout = "warning: not json"
                stderr = "traceback detail"

            with patch("src.il_model_backend.subprocess.run", return_value=_FailedProc()):
                with self.assertRaises(RuntimeError) as ctx:
                    invoke_gemma_lab_bridge(
                        mode="chat",
                        model_id="dummy",
                        messages=[{"role": "user", "content": "hello"}],
                        gemma_root=tmp_path,
                        python_path="python3",
                        bridge_script=str(bridge),
                        timeout_s=1,
                        cwd=tmp_path,
                    )

        self.assertIn("traceback detail", str(ctx.exception))
