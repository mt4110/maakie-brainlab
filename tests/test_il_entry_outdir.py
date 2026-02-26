import shutil
import subprocess
import time
import unittest
from pathlib import Path


class TestIlEntryOutDir(unittest.TestCase):
    def test_out_dir_is_honored(self):
        repo_root = Path(__file__).resolve().parent.parent
        il_entry = repo_root / "scripts" / "il_entry.py"
        il_fixture = repo_root / "tests" / "fixtures" / "il_exec" / "il_min.json"
        db_fixture = repo_root / "tests" / "fixtures" / "il_exec" / "retrieve_db.json"

        out_rel = f".local/obs/test_il_entry_outdir_{int(time.time() * 1000)}"
        out_abs = (repo_root / out_rel).resolve()
        if out_abs.exists():
            shutil.rmtree(out_abs, ignore_errors=True)

        cmd = [
            "python3",
            str(il_entry),
            str(il_fixture),
            "--out",
            out_rel,
            "--fixture-db",
            str(db_fixture),
        ]
        cp = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

        output = (cp.stdout or "") + (cp.stderr or "")
        self.assertIn(f"obs_dir={out_abs}", output)
        self.assertIn("OK: phase=end STOP=0", output)
        self.assertTrue((out_abs / "il.exec.report.json").exists())
        self.assertTrue((out_abs / "canonical.il.json").exists())

        shutil.rmtree(out_abs, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
