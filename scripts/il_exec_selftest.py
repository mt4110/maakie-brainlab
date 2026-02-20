#!/usr/bin/env python3
"""
S22-02: IL executor selftest (P2)
- Runs executor on fixture input
- Checks report/result existence and content
- Prints OK/ERROR/SKIP per check
- Never exits / never raises
"""
import json
import sys
from pathlib import Path


def log(msg: str):
    print(msg)


def main():
    checks_passed = 0
    checks_failed = 0
    checks_skipped = 0

    out_dir = ".local/selftest_out"

    try:
        # 0. Setup
        fixture_il = Path("tests/fixtures/il_exec/il_min.json")
        fixture_db = Path("tests/fixtures/il_exec/retrieve_db.json")

        if not fixture_il.exists():
            log(f"ERROR: fixture not found: {fixture_il}")
            checks_failed += 1
            return
        if not fixture_db.exists():
            log(f"ERROR: fixture not found: {fixture_db}")
            checks_failed += 1
            return

        # Clean output dir
        out_path = Path(out_dir)
        try:
            if out_path.exists():
                for f in out_path.iterdir():
                    try:
                        f.unlink()
                    except Exception:
                        pass
            out_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            log(f"ERROR: cannot prepare out_dir: {e}")
            checks_failed += 1
            return

        # 1. Import executor
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
            from il_executor import execute_il
        except Exception as e:
            log(f"ERROR: cannot import il_executor: {e}")
            checks_failed += 1
            return

        log("OK: imported il_executor")
        checks_passed += 1

        # 2. Read IL fixture
        try:
            with open(fixture_il, "r", encoding="utf-8") as f:
                il_data = json.load(f)
        except Exception as e:
            log(f"ERROR: cannot read fixture: {e}")
            checks_failed += 1
            return

        log("OK: read IL fixture")
        checks_passed += 1

        # 3. Execute
        try:
            report = execute_il(il_data, out_dir, str(fixture_db))
        except Exception as e:
            log(f"ERROR: execute_il raised exception: {e}")
            checks_failed += 1
            return

        log("OK: execute_il completed without exception")
        checks_passed += 1

        # 4. Check report file exists
        report_path = out_path / "il.exec.report.json"
        if report_path.exists():
            log(f"OK: report file exists: {report_path}")
            checks_passed += 1
        else:
            log(f"ERROR: report file missing: {report_path}")
            checks_failed += 1
            return

        # 5. Validate report content
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                report_data = json.load(f)

            schema = report_data.get("schema")
            if schema == "IL_EXEC_REPORT_v1":
                log("OK: report schema is IL_EXEC_REPORT_v1")
                checks_passed += 1
            else:
                log(f"ERROR: unexpected report schema: {schema}")
                checks_failed += 1

            overall = report_data.get("overall_status")
            if overall in ("OK", "ERROR", "SKIP"):
                log(f"OK: overall_status={overall}")
                checks_passed += 1
            else:
                log(f"ERROR: unexpected overall_status: {overall}")
                checks_failed += 1

            steps = report_data.get("steps", [])
            if len(steps) == 4:
                log(f"OK: steps count={len(steps)}")
                checks_passed += 1
            else:
                log(f"ERROR: expected 4 steps, got {len(steps)}")
                checks_failed += 1

            # Check each step has required fields
            step_ok = True
            for s in steps:
                for key in ("index", "opcode", "status", "reason"):
                    if key not in s:
                        log(f"ERROR: step missing field '{key}': {s}")
                        step_ok = False
                        checks_failed += 1
                        break
                if s.get("reason", "") == "":
                    log(f"ERROR: step has empty reason: {s}")
                    step_ok = False
                    checks_failed += 1
            if step_ok:
                log("OK: all steps have required fields with non-empty reasons")
                checks_passed += 1

        except Exception as e:
            log(f"ERROR: report validation failed: {e}")
            checks_failed += 1

        # 6. Check result file
        result_path = out_path / "il.exec.result.json"
        overall = report_data.get("overall_status", "UNKNOWN")

        if overall == "OK":
            if result_path.exists():
                log("OK: result file exists (overall_status=OK)")
                checks_passed += 1
                # Validate result content
                try:
                    with open(result_path, "r", encoding="utf-8") as f:
                        result_data = json.load(f)
                    if result_data.get("schema") == "IL_EXEC_RESULT_v1":
                        log("OK: result schema is IL_EXEC_RESULT_v1")
                        checks_passed += 1
                    else:
                        log(f"ERROR: unexpected result schema: {result_data.get('schema')}")
                        checks_failed += 1
                    if "cites" in result_data:
                        log(f"OK: result has cites (count={len(result_data['cites'])})")
                        checks_passed += 1
                    else:
                        log("ERROR: result missing cites")
                        checks_failed += 1
                except Exception as e:
                    log(f"ERROR: result validation failed: {e}")
                    checks_failed += 1
            else:
                log("ERROR: result file missing but overall_status=OK")
                checks_failed += 1
        else:
            if not result_path.exists():
                log(f"OK: result file correctly absent (overall_status={overall})")
                checks_passed += 1
            else:
                log(f"ERROR: result file exists but overall_status={overall}")
                checks_failed += 1

    except Exception as e:
        log(f"ERROR: unhandled exception in selftest: {type(e).__name__}: {e}")
        checks_failed += 1

    # Summary
    total = checks_passed + checks_failed + checks_skipped
    log(f"--- selftest summary: {checks_passed}/{total} passed, {checks_failed} failed, {checks_skipped} skipped ---")
    if checks_failed > 0:
        log(f"ERROR: selftest has {checks_failed} failure(s)")
    else:
        log(f"OK: selftest all {checks_passed} checks passed")


if __name__ == "__main__":
    main()
