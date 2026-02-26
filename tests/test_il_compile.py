import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestILCompile(unittest.TestCase):
    def test_compile_success_and_il_entry_bridge(self):
        repo_root = Path(__file__).resolve().parent.parent
        compile_script = repo_root / "scripts" / "il_compile.py"
        il_entry_script = repo_root / "scripts" / "il_entry.py"
        fixture_db = repo_root / "tests" / "fixtures" / "il_exec" / "retrieve_db.json"

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            req_path = tmp_path / "request.good.json"
            compile_out = tmp_path / "compile_out"
            exec_out = tmp_path / "exec_out"

            req_payload = {
                "schema": "IL_COMPILE_REQUEST_v1",
                "request_text": "Please search alpha and beta from greek docs",
                "context": {"keywords": ["alpha", "beta"]},
                "constraints": {
                    "allowed_opcodes": ["SEARCH_TERMS", "RETRIEVE", "ANSWER", "CITE"],
                    "forbidden_keys": [],
                    "max_steps": 4,
                },
                "artifact_pointers": [{"path": "tests/fixtures/il_exec/retrieve_db.json"}],
                "determinism": {"temperature": 0.0, "top_p": 1.0, "seed": 7, "stream": False},
            }
            req_path.write_text(json.dumps(req_payload, ensure_ascii=False, indent=2), encoding="utf-8")

            cp = subprocess.run(
                [
                    "python3",
                    str(compile_script),
                    "--request",
                    str(req_path),
                    "--out",
                    str(compile_out),
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            compile_output = (cp.stdout or "") + (cp.stderr or "")
            self.assertIn("OK: phase=end STOP=0", compile_output)
            self.assertTrue((compile_out / "il.compile.report.json").exists())
            self.assertTrue((compile_out / "il.compiled.json").exists())
            self.assertTrue((compile_out / "il.compiled.canonical.json").exists())

            report = json.loads((compile_out / "il.compile.report.json").read_text(encoding="utf-8"))
            self.assertEqual(report.get("status"), "OK")
            self.assertEqual(report.get("error_count"), 0)

            compiled_path = compile_out / "il.compiled.json"
            ep = subprocess.run(
                [
                    "python3",
                    str(il_entry_script),
                    str(compiled_path),
                    "--out",
                    str(exec_out),
                    "--fixture-db",
                    str(fixture_db),
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            entry_output = (ep.stdout or "") + (ep.stderr or "")
            self.assertIn("OK: phase=end STOP=0", entry_output)
            self.assertTrue((exec_out / "il.exec.report.json").exists())

    def test_compile_failure_writes_structured_errors(self):
        repo_root = Path(__file__).resolve().parent.parent
        compile_script = repo_root / "scripts" / "il_compile.py"

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            req_path = tmp_path / "request.bad.json"
            out_dir = tmp_path / "compile_out"

            bad_payload = {
                "schema": "IL_COMPILE_REQUEST_v1",
                "request_text": "alpha",
                "context": {},
                "constraints": {"allowed_opcodes": ["SEARCH_TERMS"], "forbidden_keys": [], "max_steps": 1},
                "artifact_pointers": [],
                "determinism": {"temperature": 0.7, "top_p": 1.0, "seed": 7, "stream": False},
            }
            req_path.write_text(json.dumps(bad_payload, ensure_ascii=False, indent=2), encoding="utf-8")

            cp = subprocess.run(
                [
                    "python3",
                    str(compile_script),
                    "--request",
                    str(req_path),
                    "--out",
                    str(out_dir),
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            output = (cp.stdout or "") + (cp.stderr or "")
            self.assertIn("OK: phase=end STOP=1", output)
            self.assertTrue((out_dir / "il.compile.report.json").exists())
            self.assertTrue((out_dir / "il.compile.error.json").exists())
            self.assertFalse((out_dir / "il.compiled.json").exists())

            report = json.loads((out_dir / "il.compile.report.json").read_text(encoding="utf-8"))
            self.assertEqual(report.get("status"), "ERROR")
            self.assertGreater(report.get("error_count", 0), 0)

            err_doc = json.loads((out_dir / "il.compile.error.json").read_text(encoding="utf-8"))
            codes = [e.get("code") for e in err_doc.get("errors", [])]
            self.assertIn("E_NONDETERMINISTIC", codes)


if __name__ == "__main__":
    unittest.main()
