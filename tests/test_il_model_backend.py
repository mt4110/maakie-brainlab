import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from src.il_model_backend import (
    GemmaLabModelBackendAdapter,
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

    def test_blank_numeric_env_values_fall_back_to_defaults(self):
        with patch.dict(
            "os.environ",
            {
                "IL_COMPILE_LLM_TIMEOUT_S": "",
                "IL_COMPILE_LLM_MAX_TOKENS": "",
            },
            clear=False,
        ):
            adapter = OpenAICompatModelBackendAdapter(api_base="http://127.0.0.1:11434/v1")

        self.assertEqual(adapter.timeout_s, 60)
        self.assertEqual(adapter.max_tokens, 1024)

    def test_invalid_numeric_env_values_raise_clear_error(self):
        with patch.dict(
            "os.environ",
            {
                "IL_COMPILE_LLM_TIMEOUT_S": "not-a-number",
            },
            clear=False,
        ):
            with self.assertRaises(ValueError) as ctx:
                OpenAICompatModelBackendAdapter(api_base="http://127.0.0.1:11434/v1")

        self.assertIn("IL_COMPILE_LLM_TIMEOUT_S must be an integer", str(ctx.exception))


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

    def test_blank_gemma_timeout_env_uses_default(self):
        with patch.dict(
            "os.environ",
            {"IL_COMPILE_GEMMA_LAB_TIMEOUT_S": ""},
            clear=False,
        ):
            adapter = GemmaLabModelBackendAdapter(
                gemma_root="/tmp/gemma-lab",
                python_path="python3",
                bridge_script="/tmp/gemma_lab_bridge.py",
            )

        self.assertEqual(adapter.timeout_s, 600)

    def test_invoke_gemma_lab_bridge_resolves_relative_overrides_against_run_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            run_cwd = tmp_path / "workspace"
            run_cwd.mkdir()
            gemma_root = tmp_path / "gemma-lab"
            python_path = gemma_root / ".venv" / "bin" / "python"
            python_path.parent.mkdir(parents=True)
            python_path.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
            bridge = run_cwd / "bridge.py"
            bridge.write_text("#!/usr/bin/env python3\n", encoding="utf-8")

            class _OkProc:
                returncode = 0
                stdout = '{"status":"ok","output_text":"hi"}'
                stderr = ""

            with patch("src.il_model_backend.subprocess.run", return_value=_OkProc()) as run_mock:
                invoke_gemma_lab_bridge(
                    mode="chat",
                    model_id="dummy",
                    messages=[{"role": "user", "content": "hello"}],
                    gemma_root=Path("../gemma-lab"),
                    python_path="../gemma-lab/.venv/bin/python",
                    bridge_script="bridge.py",
                    timeout_s=1,
                    cwd=run_cwd,
                )

        args = run_mock.call_args.args[0]
        self.assertEqual(args[0], str(python_path.resolve()))
        self.assertEqual(args[1], str(bridge.resolve()))
        self.assertEqual(args[5], str(gemma_root.resolve()))
        self.assertEqual(run_mock.call_args.kwargs["cwd"], str(run_cwd.resolve()))
