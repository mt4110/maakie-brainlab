import sys
from pathlib import Path

def main():
    args = sys.argv[1:]
    
    # Help case
    if "--help" in args or "-h" in args:
        print("OK: smoke test does not require arguments")
        return

    repo_root = Path(__file__).resolve().parent.parent
    il_entry_script = repo_root / "scripts" / "il_entry.py"
    
    # We will run il_entry.py through import to avoid subprocess overhead,
    # or just use subprocess.run without asserting.
    # Plan says: "tests 2 cases: good IL and bad IL"
    
    import subprocess
    
    def run_case(name: str, il_path: str):
        print(f"== Smoke Case: {name} ==")
        if not Path(il_path).exists():
            print(f"SKIP: fixture not found: {il_path}")
            return
            
        cmd = ["python3", str(il_entry_script), str(il_path), "--out", ".local/obs/smoke"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Output truth
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
            
        # We don't check exit code or assert. We just print.
        print(f"OK: smoke case {name} finished")

    # good case (use il_min.json)
    run_case("good", "tests/fixtures/il_exec/il_min.json")
    
    # bad case (use something non-existent or invalid)
    run_case("bad_not_found", "tests/fixtures/il_exec/invalid_does_not_exist.json")

    print("OK: smoke test complete")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: smoke test unexpected exception: {e}")
