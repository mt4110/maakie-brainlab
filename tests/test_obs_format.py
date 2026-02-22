import unittest
import re
from pathlib import Path
import sys
import os

# Ensure scripts/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from obs_writer import OBSWriter

class TestOBSFormat(unittest.TestCase):
    def test_utc_naming(self):
        writer = OBSWriter("test_job")
        # Format: .local/obs/test_job_YYYYMMDDTHHMMSSZ
        # Using search instead of match because str(writer.obs_dir) might be relative
        pattern = r"\.local/obs/test_job_\d{8}T\d{6}Z$"
        self.assertTrue(re.search(pattern, str(writer.obs_dir)), f"Naming mismatch: {writer.obs_dir}")

    def test_log_format(self):
        # We check the format via string generation logic if possible, 
        # but here we just verify it doesn't crash and STOP=1 sets internal state.
        writer = OBSWriter("test_log")
        writer.log("OK", phase="test", ms=10)
        self.assertEqual(writer.stop, 0)
        
        writer.log("ERROR", phase="fail", STOP=1)
        self.assertEqual(writer.stop, 1)

    def test_dir_creation_failure_handled(self):
        # Point to a path that should fail (e.g. into a file that exists)
        # Note: In some environments this might be tricky, but we just verify it doesn't exit.
        writer = OBSWriter("test_fail", repo_root=Path("/dev/null"))
        success = writer.create_dir()
        self.assertFalse(success)
        self.assertEqual(writer.stop, 1)

if __name__ == "__main__":
    unittest.main()
