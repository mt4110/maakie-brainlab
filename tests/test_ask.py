import os
import unittest
from unittest.mock import patch

from src.ask import resolve_local_model_backend, resolve_local_model_name


class TestAskBackendResolution(unittest.TestCase):
    def test_resolve_local_model_backend_uses_shared_precedence(self):
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
