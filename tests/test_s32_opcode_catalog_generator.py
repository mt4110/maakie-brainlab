import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s32_opcode_catalog_generator.py"
    spec = importlib.util.spec_from_file_location("s32_opcode_catalog_generator", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestS32OpcodeCatalogGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_build_catalog_has_opcodes(self):
        catalog = self.m.build_catalog("SEARCH\nANSWER\nCITE")
        self.assertEqual(catalog.get("schema"), "S32_OPCODE_CATALOG_V1")
        self.assertGreater(catalog.get("summary", {}).get("opcode_count", 0), 0)
        self.assertIn("opcodes", catalog)

    def test_script_outputs_json_and_md(self):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "ops" / "s32_opcode_catalog_generator.py"
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "catalog"
            cp = subprocess.run(
                ["python3", str(script), "--out-dir", str(out_dir)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            output = (cp.stdout or "") + (cp.stderr or "")
            self.assertIn(cp.returncode, {0, 1}, msg=output)
            payload_path = out_dir / "opcode_catalog_latest.json"
            self.assertTrue(payload_path.exists(), msg=output)
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("schema"), "S32_OPCODE_CATALOG_V1")
            self.assertTrue((out_dir / "opcode_catalog_latest.md").exists())


if __name__ == "__main__":
    unittest.main()
