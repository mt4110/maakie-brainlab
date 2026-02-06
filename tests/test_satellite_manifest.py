import unittest
import json
import tempfile
import sys
from pathlib import Path

# Fix import path for standalone execution
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from satellite.manifest import generate_run_id, save_manifest, compute_config_sha

class TestSatelliteManifest(unittest.TestCase):
    def test_generate_run_id_stability(self):
        """Test that run_id is deterministic for same inputs."""
        rid1 = generate_run_id("2023-10-01", "src1", "conf1", "v1")
        rid2 = generate_run_id("2023-10-01", "src1", "conf1", "v1")
        self.assertEqual(rid1, rid2)
        # Verify it changes if input changes
        rid3 = generate_run_id("2023-10-02", "src1", "conf1", "v1")
        self.assertNotEqual(rid1, rid3)

    def test_compute_config_sha(self):
        """Test config_sha calculation with mocked files."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_id = "test_src"
            
            # Setup directory structure required by Policy A
            (root / "satellite/sources").mkdir(parents=True)
            (root / "satellite/rules").mkdir(parents=True)
            (root / "satellite/prompts/test_src").mkdir(parents=True)
            
            # Create files with known content
            f1 = root / f"satellite/sources/{source_id}.toml"
            f1.write_text("source_config")
            
            f2 = root / f"satellite/rules/{source_id}.toml"
            f2.write_text("rule_config")
            
            f3 = root / f"satellite/prompts/{source_id}/v1.txt"
            f3.write_text("prompt_content")
            
            sha1 = compute_config_sha(source_id, root)
            
            # 1. Deterministic check
            sha2 = compute_config_sha(source_id, root)
            self.assertEqual(sha1, sha2)
            
            # 2. Content change affects hash
            f3.write_text("prompt_content_changed")
            sha3 = compute_config_sha(source_id, root)
            self.assertNotEqual(sha1, sha3)
            
            # 3. Missing file raises error
            f3.unlink()
            with self.assertRaises(FileNotFoundError):
                compute_config_sha(source_id, root)

    def test_save_manifest_strict_schema(self):
        """Test schema enforcement (Policy B)."""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "manifest.json"
            
            # Missing required fields
            bad_data = {"run_id": "123"}
            with self.assertRaisesRegex(ValueError, "Manifest missing required fields"):
                save_manifest(path, bad_data)
                
            # Valid data
            valid_data = {
                "run_id": "123",
                "date": "2023-01-01",
                "source_id": "src",
                "config_sha": "abc",
                "code_version": "v1",
                "artifacts": []
            }
            save_manifest(path, valid_data)
            self.assertTrue(path.exists())

    def test_save_manifest_sorting(self):
        """Test artifact sorting (Policy B)."""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "manifest.json"
            
            artifacts = [
                {"path": "b/file.txt", "sha256": "x", "bytes": 1},
                {"path": "a/file.txt", "sha256": "y", "bytes": 2}
            ]
            
            data = {
                "run_id": "123", "date": "2023-01-01", 
                "source_id": "src", "config_sha": "abc", 
                "code_version": "v1", "artifacts": artifacts
            }
            
            save_manifest(path, data)
            
            with open(path, "r") as f:
                saved = json.load(f)
            
            # Check sorting
            self.assertEqual(saved["artifacts"][0]["path"], "a/file.txt")
            self.assertEqual(saved["artifacts"][1]["path"], "b/file.txt")

if __name__ == "__main__":
    unittest.main()
