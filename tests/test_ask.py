import os
import unittest
from unittest.mock import patch

from src.ask import resolve_local_model_backend, resolve_local_model_name


class TestAskBackendResolution(unittest.TestCase):
    def test_resolve_local_model_backend_uses_local_then_compile_fallback(self):
        with patch.dict(
            os.environ,
            {
                "LOCAL_MODEL_BACKEND": "",
                "IL_COMPILE_MODEL_BACKEND": "gemma_lab",
                "GEMMA_MODEL_ID": "google/gemma-4-E2B-it",
            },
            clear=False,
        ):
            self.assertEqual(resolve_local_model_backend(), "gemma_lab")
            self.assertEqual(resolve_local_model_name(), "google/gemma-4-E2B-it")

    def test_resolve_local_model_backend_prefers_local_model_backend(self):
        with patch.dict(
            os.environ,
            {
                "LOCAL_MODEL_BACKEND": "openai_compat",
                "IL_COMPILE_MODEL_BACKEND": "gemma_lab",
            },
            clear=False,
        ):
            self.assertEqual(resolve_local_model_backend(), "openai_compat")

    def test_resolve_local_model_name_matches_dashboard_default(self):
        with patch.dict(
            os.environ,
            {
                "LOCAL_MODEL_BACKEND": "openai_compat",
                "LOCAL_GGUF_MODEL": "",
                "IL_COMPILE_MODEL_BACKEND": "",
            },
            clear=False,
        ):
            self.assertEqual(resolve_local_model_name(), "Qwen2.5-7B-Instruct")

    def test_resolve_local_model_backend_rejects_unknown_values(self):
        with patch.dict(
            os.environ,
            {
                "LOCAL_MODEL_BACKEND": "not_real_backend",
                "IL_COMPILE_MODEL_BACKEND": "",
            },
            clear=False,
        ):
            with self.assertRaises(ValueError):
                resolve_local_model_backend()
