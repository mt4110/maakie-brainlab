import sys
import types
import unittest
from unittest.mock import patch

import requests

from src.il_model_backend import ModelBackendRequest, OpenAICompatModelBackendAdapter


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
