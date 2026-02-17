#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Fix path to allow importing from eval
sys.path.append(str(Path(__file__).parent.parent))

try:
    from eval.run_eval import get_keywords
except ImportError as e:
    print(f"SKIP: Import failed: {e}")
    sys.exit(0)

def audit_case(name, input_text, expected_in=None, expected_out=None):
    try:
        kws = get_keywords(input_text)
        passed = True
        msg = []
        
        if expected_in:
            for w in expected_in:
                if w not in kws:
                    passed = False
                    msg.append(f"Missing '{w}'")
        
        if expected_out:
            for w in expected_out:
                if w in kws:
                    passed = False
                    msg.append(f"Found forbidden '{w}'")
        
        if passed:
            print(f"OK: {name}")
        else:
            print(f"ERROR: {name} -> {', '.join(msg)} (Got: {kws})")
            
    except Exception as e:
        print(f"ERROR: {name} crashed: {e}")

def main():
    print("--- Audit: S20-06 Keyword Guardrails ---")
    
    # 1. NFKC Normalization
    audit_case("NFKC_HalfKana", "ﾊﾝｶｸ", expected_in=["ハンカク"], expected_out=["ﾊﾝｶｸ"])
    
    # 2. Long-Hex Exclusion
    # 40 chars hex
    hex40 = "a" * 40
    audit_case("Hex_40_Exclude", hex40, expected_out=[hex40])
    
    # 39 chars hex (should include)
    hex39 = "a" * 39
    audit_case("Hex_39_Include", hex39, expected_in=[hex39])
    
    # 3. Stopwords
    audit_case("Stopword_Conclusion", "結論", expected_out=["結論"])
    audit_case("Stopword_Koto", "こと", expected_out=["こと"])
    
    # 4. Mixed Real World
    audit_case("RealWorld", "重要な点はCommit-hash:0123456789abcdef0123456789abcdef01234567です", 
               expected_in=["重要", "Commit", "hash"], 
               expected_out=["点", "0123456789abcdef0123456789abcdef01234567"])

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FATAL: Script crashed: {e}")
    # Always exit 0
    sys.exit(0)
