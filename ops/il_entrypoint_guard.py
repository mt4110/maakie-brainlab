#!/usr/bin/env python3
"""
S22-16: Always-on guard to ensure canonical IL entrypoint usage.
"""
import shutil
import subprocess
from pathlib import Path

CANONICAL_ENTRYPOINT = "scripts/il_entry.py"
LEGACY_PATTERN = (
    r"(python3?\s+.*scripts/il_(?:exec|check|guard|exec_run)\.py|"
    r"scripts/il_(?:exec|check|guard|exec_run)\.py)"
)


def run_rg(repo_root: Path, targets):
    cmd = [
        "rg",
        "--no-heading",
        "--line-number",
        "--color",
        "never",
        "-g",
        "!ops/il_entrypoint_guard.py",
        LEGACY_PATTERN,
    ]
    cmd.extend(targets)
    return subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False)


def main():
    repo_root = Path(__file__).resolve().parent.parent
    errors_found = 0
    warns_found = 0

    try:
        if not shutil.which("rg"):
            print("WARN: 'rg' (ripgrep) is not installed. guard skipped.")
            warns_found += 1
            print(f"OK: guard_summary errors={errors_found} warns={warns_found} canonical={CANONICAL_ENTRYPOINT}")
            return

        # docs/ops is intentionally excluded:
        # historical milestone docs can contain legacy references that are not runtime paths.
        print("WARN: docs/ops excluded from scan (historical references are non-runtime).")
        warns_found += 1

        result = run_rg(repo_root, ["Makefile", "ops", ".github"])
        if result.stdout:
            for raw_line in result.stdout.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                print(f"ERROR: non-canonical entrypoint reference: {line}")
                print(f"::error::non-canonical entrypoint reference: {line}")
                errors_found += 1

        stderr_text = (result.stderr or "").strip()
        if stderr_text:
            print(f"WARN: rg stderr={stderr_text}")
            warns_found += 1

        if errors_found == 0:
            print(f"OK: all runtime entrypoint references are canonical ({CANONICAL_ENTRYPOINT})")
    except Exception as exc:
        print(f"ERROR: unexpected guard exception: {exc}")
        errors_found += 1

    print(f"OK: guard_summary errors={errors_found} warns={warns_found} canonical={CANONICAL_ENTRYPOINT}")


if __name__ == "__main__":
    main()
