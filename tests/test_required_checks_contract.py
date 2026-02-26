import json
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "ops" / "ci" / "check_required_checks_contract.py"


class TestRequiredChecksContract(unittest.TestCase):
    def test_repo_contract_check_passes(self):
        cp = subprocess.run(
            ["python3", str(SCRIPT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            cwd=str(ROOT),
        )
        self.assertEqual(cp.returncode, 0, msg=f"stdout={cp.stdout}\nstderr={cp.stderr}")
        self.assertIn("OK: docs SOT matched", cp.stdout)
        self.assertIn("OK: ruleset SOT matched", cp.stdout)

    def test_detects_drift(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / ".github/workflows").mkdir(parents=True, exist_ok=True)

            (base / "docs.md").write_text(
                textwrap.dedent(
                    """
                    <!-- required_checks_sot:v1
                    test
                    -->
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            (base / "ruleset.json").write_text(
                json.dumps({"required_status_checks": ["test"]}, ensure_ascii=True) + "\n",
                encoding="utf-8",
            )
            (base / "contract.json").write_text(
                json.dumps(
                    {
                        "required_contexts": ["test", "verify-pack"],
                        "context_to_workflow_job": {
                            "test": {"workflow": ".github/workflows/test.yml", "job": "test"},
                            "verify-pack": {
                                "workflow": ".github/workflows/verify_pack.yml",
                                "job": "verify-pack",
                            },
                        },
                    },
                    ensure_ascii=True,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (base / ".github/workflows/test.yml").write_text(
                "name: Test\njobs:\n  test:\n    runs-on: ubuntu-latest\n",
                encoding="utf-8",
            )
            (base / ".github/workflows/verify_pack.yml").write_text(
                "name: Verify Pack\njobs:\n  verify-pack:\n    runs-on: ubuntu-latest\n",
                encoding="utf-8",
            )

            cp = subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "--repo-root",
                    str(base),
                    "--contract",
                    "contract.json",
                    "--docs",
                    "docs.md",
                    "--ruleset",
                    "ruleset.json",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                cwd=str(ROOT),
            )
            self.assertEqual(cp.returncode, 1, msg=f"stdout={cp.stdout}\nstderr={cp.stderr}")
            self.assertIn("ERROR: docs SOT drift", cp.stdout)


if __name__ == "__main__":
    unittest.main()
