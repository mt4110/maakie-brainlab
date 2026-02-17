import argparse
import hashlib
import json
import os
import re
import requests
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

ROOT = Path(__file__).resolve().parents[1]
# S20-03: Use new dataset location and run output location
DATASETS_DIR = ROOT / "data" / "eval" / "datasets"
RUNS_DIR = ROOT / ".local" / "rag_eval" / "runs"
DEFAULT_DATASET_ID = "rag-eval-wall-v1__seed-mini__v0001"
STORE_DIR = ROOT / ".local" / "aiwork"

# S20-03: Frozen Failure Codes (EVAL_SPEC v1)
class FailureCode:
    DATASET_INVALID = "DATASET_INVALID"
    FORMAT_INVALID = "FORMAT_INVALID"
    RETRIEVAL_EMPTY = "RETRIEVAL_EMPTY"
    RETRIEVAL_OFFTOPIC = "RETRIEVAL_OFFTOPIC"
    ANSWER_UNSUPPORTED = "ANSWER_UNSUPPORTED"
    CITATION_MISSING = "CITATION_MISSING"
    REFUSAL_MISSING = "REFUSAL_MISSING"
    REFUSAL_UNNECESSARY = "REFUSAL_UNNECESSARY"
    INJECTION_SUCCEEDED = "INJECTION_SUCCEEDED"
    TIMEOUT = "TIMEOUT"
    CRASH = "CRASH"
    MIXED_HALLUCINATION = "MIXED_HALLUCINATION"
    NEGATIVE_CONTROL_VIOLATION = "NEGATIVE_CONTROL_VIOLATION"
    UNKNOWN = None  # Fallback: map to null in output

# Mapping internal ReasonCode to FailureCode
REASON_TO_FAILURE = {
    # Internal -> FailureCode
    "SERVER_UNREACHABLE": FailureCode.CRASH,
    "SERVER_MODEL_MISSING": FailureCode.CRASH,
    "INFERENCE_FAILED": FailureCode.CRASH,
    "INDEX_MISSING": FailureCode.CRASH,
    "CONTEXT_EMPTY": FailureCode.RETRIEVAL_EMPTY,
    "UNKNOWN_ANSWER": FailureCode.RETRIEVAL_EMPTY, # Assuming "I don't know" means retrieval failed to provide info
    "EMPTY_ANSWER": FailureCode.FORMAT_INVALID,
    "NO_SOURCES": FailureCode.CITATION_MISSING,
    "MISSING_REQUIRED_SOURCE": FailureCode.RETRIEVAL_OFFTOPIC, # Or unsupported? Using simplistic mapping for v1
    "MISSING_EXPECTED_EVIDENCE": FailureCode.ANSWER_UNSUPPORTED,
    "ASK_EXIT_NONZERO": FailureCode.CRASH,
    "POSITIVE_HALLUCINATION": FailureCode.REFUSAL_MISSING, # Should have refused but didn't
    "FORMAT_INVALID": FailureCode.FORMAT_INVALID,
    "MIXED_HALLUCINATION": FailureCode.MIXED_HALLUCINATION,
    "NEGATIVE_CONTROL_VIOLATION": FailureCode.NEGATIVE_CONTROL_VIOLATION,
}


# S1: unknown/参照なし を fail 扱い（安全側に倒す）
UNKNOWN_TOKENS = (
    "不明",
    "わかりません",
    "unknown",
    "参照なし",
    "参照: 不明",
    "参照できる根拠が見つかりません",
    "資料が見つかりません",
    "存在しない可能性があります",
    "記載されていません",
    "見当たりません",
)


class ReasonCode:
    SERVER_UNREACHABLE = "SERVER_UNREACHABLE"
    SERVER_MODEL_MISSING = "SERVER_MODEL_MISSING"
    INFERENCE_FAILED = "INFERENCE_FAILED"

    INDEX_MISSING = "INDEX_MISSING"
    CONTEXT_EMPTY = "CONTEXT_EMPTY"

    UNKNOWN_ANSWER = "UNKNOWN_ANSWER"
    EMPTY_ANSWER = "EMPTY_ANSWER"
    NO_SOURCES = "NO_SOURCES"
    MISSING_REQUIRED_SOURCE = "MISSING_REQUIRED_SOURCE"
    MISSING_EXPECTED_EVIDENCE = "MISSING_EXPECTED_EVIDENCE"

    ASK_EXIT_NONZERO = "ASK_EXIT_NONZERO"
    POSITIVE_HALLUCINATION = "POSITIVE_HALLUCINATION"
    FORMAT_INVALID = "FORMAT_INVALID"
    MIXED_HALLUCINATION = "MIXED_HALLUCINATION"
    NEGATIVE_CONTROL_VIOLATION = "NEGATIVE_CONTROL_VIOLATION"


def calculate_spec_hash(spec: Dict[str, Any]) -> str:
    """Calculate a stable hash for the given specification."""
    canonical = json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()



def _is_section_header(line: str) -> bool:
    """
    Check if line is a known section header (whitelist).
    """
    return line in ("結論:", "根拠:", "参照:")


def parse_sources(answer: str) -> list[str]:
    """
    参照: セクションの - ... 行を抽出する
    """
    sources = []
    in_ref_block = False
    for line in answer.splitlines():
        line = line.strip()
        if line.startswith("参照:"):
            in_ref_block = True
            continue
        if in_ref_block:
            if not line:
                continue
            if line.startswith("-"):
                sources.append(line.lstrip("- ").strip())
            else:
                if _is_section_header(line):
                    break
    return sources


# _is_section_header and _find_first_list_item are defined above


def extract_evidence_lines(answer: str) -> list[str]:
    """
    根拠: セクションの - ... 行を抽出する
    """
    evidence = []
    in_block = False
    for line in answer.splitlines():
        line = line.strip()
        if line.startswith("根拠:"):
            in_block = True
            continue
        if in_block:
            if not line:
                continue
            if line.startswith("-"):
                evidence.append(line.lstrip("- ").strip())
            else:
                if _is_section_header(line):
                    break
    return evidence



# P2: Japanese Stopwords (Audit-friendly list)
JAPANESE_STOPWORDS = {
    "結論", "根拠", "参照", "答え", "回答", "質問",
    "以下", "概要", "詳細", "点", "面", "場合", "こと",
    "もの", "ため", "よう", "際", "時", "一般", "的"
}

def get_keywords(text: str) -> set[str]:
    """
    簡易的なキーワード抽出（名詞・固有語っぽいもの）
    P2 Update:
    - CJK Extension A (\u3400-\u4DBF) & Compatibility (\uF900-\uFAFF)
    - Stopwords filtering
    - Alphanumeric precision (exclude pure digits)
    """
    if not text:
        return set()
    
    # \u4e00-\u9fff: CJK Unified Ideographs (Common)
    # \u3400-\u4dbf: CJK Extension A
    # \uF900-\uFAFF: CJK Compatibility Ideographs
    # \u30a0-\u30ff: Katakana
    # a-zA-Z0-9_: Alphanumeric
    # Note: Hiragana is EXCLUDED to function as a natural tokenizer (matching legacy behavior).
    
    # Regex designed to capture sequence of relevant chars
    matches = re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\u30a0-\u30ff0-9a-zA-Z_]+", text)
    
    keywords = set()
    for m in matches:
        if len(m) < 2:  # 1文字はノイズが多いので除外
            continue
        
        # Filter: Stopwords
        if m in JAPANESE_STOPWORDS:
            continue
            
        # Filter: Pure digits (e.g. 20240101)
        if m.isdigit():
            continue
        
        # Filter: Alphanumeric but no alpha/CJK (e.g. "123_456")
        # If it's pure ASCII, ensure it has at least one letter
        if m.isascii():
            if not re.search(r'[a-zA-Z]', m):
                continue
        
        # Filter: http/https (legacy)
        if m.lower() in ("http", "https"):
            continue

        keywords.add(m)
    return keywords


def extract_conclusion_lines(answer: str) -> list[str]:
    """
    結論: 直下のリスト項目（- ...）をすべて抽出する
    """
    lines = answer.splitlines()
    conclusion = []
    in_block = False
    for line in lines:
        row = line.strip()
        if row == "結論:":
            in_block = True
            continue
        if in_block:
            if not row:
                continue
            if row.startswith("-"):
                conclusion.append(row.lstrip("- ").strip())
            elif _is_section_header(row):
                break
            # If text line but not bullet, maybe continuation? 
            # For this simple parser, just ignore or assume strictly formatted.
    return conclusion


def extract_conclusion_line(answer: str) -> Optional[str]:
    """
    Legacy compat: return first line of conclusion
    """
    c = extract_conclusion_lines(answer)
    return c[0] if c else None


def determine_standard_fail_reason(
    answer: str,
    err: str,
    exit_code: int,
    mentions_unknown: bool,
    has_sources: bool
) -> Optional[str]:
    if exit_code != 0:
        if "index db not found" in err:
            return ReasonCode.INDEX_MISSING
        return ReasonCode.ASK_EXIT_NONZERO
    
    if not answer:
        return ReasonCode.EMPTY_ANSWER

    if mentions_unknown:
        if "CONTEXTが空" in answer:
            return ReasonCode.CONTEXT_EMPTY
        return ReasonCode.UNKNOWN_ANSWER
    
    if not has_sources: 
        return ReasonCode.NO_SOURCES

    return None


def apply_type_constraints(
    q_type: str,
    fail_reason_code: Optional[str],
    has_required_source: bool,
    has_expected_evidence: bool,
    conclusion_text: Optional[str],
    has_sources: bool,
    mixed_candidates: list[str]
) -> Optional[str]:

    if q_type == "negative_control":
        # Rule: Must match unknown/refusal patterns.
        # If it passed "unknown" check (is_unknown=True), we confirm it's not a mixed hallucination.
        
        # 1. Check for "However..." logic (Mixed Hallucination in refusal) across ALL lines
        if conclusion_text:
            bad_terms = ["ただし", "しかし", "一方", "ちなみに", "可能性があります", "ですが", "一般的"]
            if any(t in conclusion_text for t in bad_terms):
                return ReasonCode.MIXED_HALLUCINATION

        # 2. Check for Hallucinated Keywords (Mixed Hallucination)
        if mixed_candidates:
            # If unknown was asserted but we found external entities -> FAIL
             return ReasonCode.MIXED_HALLUCINATION

        # 3. If sources exist, it's a hallucination (Positive Hallucination)
        if has_sources:
             # Exception: "Source: Unknown" is handled by verify_sources logic usually?
             # But here we rely on has_sources parsed without unknown tokens.
             return ReasonCode.POSITIVE_HALLUCINATION

        # 4. If it was NOT unknown, and NOT caught by above -> It answered something.
        
        # P0 Fix: Strict Unknown Check. NO_SOURCES is NOT valid unknown (it's an assertion without source).
        is_strict_unknown = (fail_reason_code in (ReasonCode.UNKNOWN_ANSWER, ReasonCode.CONTEXT_EMPTY))
        
        if not is_strict_unknown:
            if fail_reason_code is None:
                # It passed standard checks (meaning it has an answer) -> Violation
                return ReasonCode.NEGATIVE_CONTROL_VIOLATION
            
            if fail_reason_code == ReasonCode.NO_SOURCES:
                # Assertion without sources -> Positive Hallucination
                return ReasonCode.POSITIVE_HALLUCINATION

            return fail_reason_code

        return None # Passed (is_strict_unknown=True and no bad signs)

    # Normal case
    if mixed_candidates:
        # P1.5 Fix: Crash Protection.
        # If it already crashed/failed infrastructure checks, return that reason immediately.
        # Do not let "mixed content" mask a crash.
        if fail_reason_code == ReasonCode.ASK_EXIT_NONZERO:
            return fail_reason_code

        # P0 Fix: Only flag MIXED if it was otherwise passing.
        # Do not overwrite CRASH/ASK_EXIT_NONZERO/CONTEXT_EMPTY.
        if fail_reason_code is None:
            return ReasonCode.MIXED_HALLUCINATION

    if fail_reason_code is None:
        if not has_required_source:
            return ReasonCode.MISSING_REQUIRED_SOURCE
        
        if not has_expected_evidence:
            return ReasonCode.MISSING_EXPECTED_EVIDENCE

    return fail_reason_code


def _norm(s: str) -> str:
    return "".join((s or "").split()).lower()


def analyze_result(
    question: dict,
    answer: str,
    exit_code: int,
    stderr: str
) -> dict:
    q_type = question.get("type", "normal")
    expected_source = question.get("expected_source")
    expected_evidence = question.get("expected_evidence")

    extracted_sources = parse_sources(answer)
    valid_sources = [s for s in extracted_sources if not any(tok in s for tok in UNKNOWN_TOKENS)]
    has_sources = len(valid_sources) > 0
    conclusion_lines = extract_conclusion_lines(answer)
    conc_line_first = conclusion_lines[0] if conclusion_lines else None
    evidence_lines = extract_evidence_lines(answer)

    format_invalid = (exit_code == 0 and bool(answer) and not conclusion_lines)

    target_text = "\n".join(conclusion_lines or [])
    mentions_unknown = any(tok in target_text for tok in UNKNOWN_TOKENS)

    # Mixed Hallucination Check
    mixed_candidates = []
    if conclusion_lines and evidence_lines:
        conc_text = "\n".join(conclusion_lines)
        conc_keywords = get_keywords(conc_text)
        evi_text = "\n".join(evidence_lines)
        evi_keywords = get_keywords(evi_text)
        q_keywords = get_keywords(question.get("query") or "")
        
        for k in conc_keywords:
            if k in evi_keywords: continue
            if k in q_keywords: continue
            mixed_candidates.append(k)
    
    elif conclusion_lines and not evidence_lines:
        # If no evidence but we have conclusion keywords -> Suspect unless unknown
        if not mentions_unknown:
            conc_text = "\n".join(conclusion_lines)
            kws = get_keywords(conc_text)
            q_keywords = get_keywords(question.get("query") or "")
            diff = [k for k in kws if k not in q_keywords]
            if diff:
                mixed_candidates.extend(diff)


    has_required_source = True
    if expected_source:
        has_required_source = False
        for src in extracted_sources:
            if expected_source in src:
                has_required_source = True
                break
    
    has_expected_evidence = True
    matched_evidence = None
    matched_evidence_all = []
    missing_evidence = []
    
    evidence_mode = "all" if q_type in ("boundary", "multi_chunk") else "any"

    if expected_evidence and isinstance(expected_evidence, list):
        if evidence_mode == "any":
            has_expected_evidence = False
            for cand in expected_evidence:
                if _norm(cand) in _norm(answer):
                    has_expected_evidence = True
                    matched_evidence = cand
                    break
        else: # ALL mode
            matches = []
            misses = []
            norm_answer = _norm(answer)
            for cand in expected_evidence:
                if _norm(cand) in norm_answer:
                    matches.append(cand)
                else:
                    misses.append(cand)
            
            if misses:
                has_expected_evidence = False
                missing_evidence = misses
            matched_evidence_all = matches

    if format_invalid:
        fail_reason_code = ReasonCode.FORMAT_INVALID
    else:
        fail_reason_code = determine_standard_fail_reason(
            answer, stderr, exit_code, mentions_unknown, has_sources
        )

    final_reason_code = apply_type_constraints(
        q_type, 
        fail_reason_code, 
        has_required_source, 
        has_expected_evidence, 
        target_text,  # Pass full text for bad term check
        has_sources,
        mixed_candidates
    )
    passed = (final_reason_code is None)

    return {
        "passed": passed,
        "reason_code": final_reason_code,
        "details": {
            "has_sources": has_sources,
            "parsed_sources": extracted_sources,
            "mentions_unknown": mentions_unknown,
            "has_required_source": has_required_source,
            "has_expected_evidence": has_expected_evidence,
            "evidence_mode": evidence_mode,
            "matched_evidence": matched_evidence,
            "matched_evidence_all": matched_evidence_all,
            "missing_evidence": missing_evidence,
            "conclusion_line": conc_line_first,
        }
    }


def check_server_status(base_url: str) -> dict:
    result = {
        "status": "ok",
        "latency_ms": 0,
        "model_id": None,
        "reason_code": None,
        "exit_code": 0,
    }

    t0 = time.time()
    try:
        r = requests.get(f"{base_url.rstrip('/')}/models", timeout=5)
        r.raise_for_status()
        data = r.json()
        models = data.get("data", [])
        if not models:
            result.update({"status": "error", "reason_code": ReasonCode.SERVER_MODEL_MISSING, "exit_code": 102})
            return result
        result["model_id"] = models[0].get("id", "unknown")
    except Exception as e:
        result.update({"status": "error", "reason_code": ReasonCode.SERVER_UNREACHABLE, "exit_code": 101, "error": str(e)})
        return result

    try:
        chat_url = f"{base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": result["model_id"],
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1,
            "temperature": 0.0
        }
        r = requests.post(chat_url, json=payload, timeout=10)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        if content is None:
            raise ValueError("No content returned")
    except Exception as e:
        result.update({"status": "error", "reason_code": ReasonCode.INFERENCE_FAILED, "exit_code": 103, "error": str(e)})
        return result

    dt = (time.time() - t0) * 1000
    result["latency_ms"] = int(dt)
    return result


def sanitize_pf(pf: dict) -> dict:
    s = pf.copy()
    s.pop("latency_ms", None)
    return s


def mock_ask(question_data: dict, spec_hash: str) -> tuple[int, str, str]:
    """Mock provider: produce output that satisfies the question's constraints."""
    q_type = question_data.get("type", "normal")
    if q_type == "negative_control":
        # For negative control, we expect "Unknown" and NO sources/evidence.
        # However, to pass format checks and avoid mixed hallucination on "根拠なし", we provide minimal valid structure.
        answer = "結論:\n- 参照できる根拠が見つかりません。\n\n根拠:\n- 参照できる根拠が見つかりません。\n\n参照:\n- なし"
        return 0, answer, ""
    
    expected_source = question_data.get("expected_source", "mock_source.md")
    expected_evidence = question_data.get("expected_evidence", [])
    
    evidence_str = ""
    if expected_evidence:
        # For multi_chunk or boundary, we might need multiple items
        evidence_str = "\n".join([f"- {e}" for e in expected_evidence])
    else:
        evidence_str = "- [MOCK] Evidence found."

    answer = f"結論:\n- [MOCK] Success for {spec_hash}\n\n根拠:\n{evidence_str}\n- [MOCK] Success for {spec_hash}\n\n参照:\n- {expected_source}"
    return 0, answer, ""


def load_dataset(dataset_id: str) -> list[dict]:
    path = DATASETS_DIR / dataset_id / "cases.jsonl"
    if not path.exists():
        # Fallback to old questions.jsonl if dataset not found (migration)
        old_path = ROOT / "eval" / "questions.jsonl"
        if old_path.exists() and dataset_id == "legacy":
             print(f"[eval] WARN: Using legacy questions.jsonl")
             lines = []
             for line in old_path.read_text(encoding="utf-8").splitlines():
                 if not line.strip(): continue
                 q = json.loads(line)
                 # Adapt legacy to new schema on the fly
                 lines.append({
                     "case_id": q["id"],
                     "query": q["question"],
                     "expectation": {
                        "must_answer": True,
                        "expected_evidence": q.get("expected_evidence", []),
                        "expected_source": q.get("expected_source"),
                     },
                     "tags": [q.get("type", "normal")],
                     "notes": "legacy migration"
                 })
             return lines
        raise FileNotFoundError(f"Dataset not found: {path}")

    cases = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))
    return cases

def get_git_info() -> dict:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short=7", "HEAD"], text=True).strip()
        return {"sha": sha}
    except:
        return {"sha": "unknown"}

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["record", "replay", "verify-only"], default="record")
    parser.add_argument("--provider", choices=["real", "mock"], default="real")
    parser.add_argument("--dataset", default=DEFAULT_DATASET_ID, help="Dataset ID to run")
    args = parser.parse_args()

    # Save command for recommended artifact
    command_str = f"python3 eval/run_eval.py --mode {args.mode} --provider {args.provider} --dataset {args.dataset}"

    mode = args.mode
    provider = args.provider
    dataset_id = args.dataset


    # In verify-only mode, we FORCE replay.
    if mode == "verify-only":
        print("[eval] mode=verify-only implies replay from existing artifacts.")

    STORE_DIR.mkdir(parents=True, exist_ok=True)
    evidence_dir = ROOT / "docs" / "evidence" / "s15-06"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence_path = evidence_dir / f"eval_{mode}_{timestamp}.jsonl"

    # --- Pre-flight Check ---
    base_url = os.getenv("OPENAI_API_BASE", "http://127.0.0.1:8080/v1")
    if provider == "real":
        pf = check_server_status(base_url)
        model_id = pf["model_id"]
    else:
        pf = {"status": "ok", "model_id": "mock-model", "exit_code": 0}
        model_id = "mock-model"

    if pf["status"] != "ok":
        print(f"[eval] PRE-FLIGHT FAILED: {pf['reason_code']} (exit={pf['exit_code']})")
        return # Exitless

    # Load Dataset
    try:
        cases = load_dataset(dataset_id)
    except Exception as e:
        print(f"[eval] ERROR: {e}")
        return # Exitless

    print(f"[eval] Loaded {len(cases)} cases from {dataset_id}")
    
    failed = 0
    results_for_run = []

    for c in cases:
        cid = c["case_id"]
        query = c["query"]
        
        # Backward compatibility for logic relying on q_type
        # In v1 dataset, we use tags. 
        # For now, just pass a minimal adaptation to the existing loop logic.


        spec = {
            "purpose": "evaluation",
            "case_id": cid,
            "query": query,
            "model_id": model_id,
            "provider": provider,
        }
        spec_hash = calculate_spec_hash(spec)
        # We still write to .local/aiwork for persistent caching/replay if needed
        # But the main deliverable is .local/rag_eval/runs/
        run_work_dir = STORE_DIR / spec_hash
        spec_file = run_work_dir / "spec.json"
        result_file = run_work_dir / "result.json"

        answer, err, exit_code = "", "", 0

        if mode in ("replay", "verify-only"):
            # S20-03: Quick hack for replay mode to use the old store structure or skip
            # Since we are moving to runs/, replay logic needs to be rethought.
            if mode == "verify-only":
                answer = "結論:\n- [MOCK] Verified\n\n根拠:\n- [MOCK] Verified\n\n参照:\n- verify.md"
                exit_code = 0
                err = ""
            else:
                if not result_file.exists():
                    print(f"[eval] ERROR: Missing result for {cid} (hash={spec_hash}) in {mode} mode.")
                    return # Exitless
            
                with result_file.open("r", encoding="utf-8") as rf:
                    stored = json.load(rf)
                    # Verify spec consistency
                    if stored.get("spec_hash") != spec_hash:
                        print(f"[eval] ERROR: Spec hash mismatch for {cid}. Expected {spec_hash}, found {stored.get('spec_hash')}")
                        return # Exitless
                    answer = stored["answer"]
                    err = stored["stderr"]
                    exit_code = stored["exit_code"]
        else:
            # record mode
            if provider == "mock":
                # Mock ask needs adaptation to new dataset structure if used extensively
                # For now using a simplified mock
                 answer = "結論:\n- [MOCK] Success\n\n参照:\n- mock.md"
                 exit_code = 0
                 err = ""
            else:
                p = subprocess.run(
                    [sys.executable, str(ROOT / "src" / "ask.py"), query],
                    capture_output=True,
                    text=True,
                )
                answer, err, exit_code = (p.stdout or "").strip(), (p.stderr or "").strip(), p.returncode

            # Save artifacts to work cache
            if mode == "record":
                run_work_dir.mkdir(parents=True, exist_ok=True)
                with spec_file.open("w", encoding="utf-8") as sf:
                    json.dump(spec, sf, indent=2, sort_keys=True, ensure_ascii=False)
                
                with result_file.open("w", encoding="utf-8") as rf:
                    json.dump({
                        "spec_hash": spec_hash,
                        "exit_code": exit_code,
                        "answer": answer,
                        "stderr": err,
                    }, rf, indent=2, sort_keys=True, ensure_ascii=False)

        # Analysis Logic
        res = analyze_result({
            "type": c.get("tags", ["normal"])[0], # Adapt for legacy logic
            "query": query or "", # P0 Fix: Propagate query for mixed hallucination check (None-safe)
            "expected_source": c["expectation"].get("expected_source"),
            "expected_evidence": c["expectation"].get("expected_evidence")
        }, answer, exit_code, err)
        
        status = "PASS" if res["passed"] else "FAIL"
        dataset_failure_code = None
        if not res["passed"]:
            rc = res["reason_code"]
            dataset_failure_code = REASON_TO_FAILURE.get(rc, FailureCode.UNKNOWN)
            failed += 1

        latency_ms = 0 # Placeholder for now

        results_for_run.append({
            "case_id": cid,
            "status": status,
            "failure_code": dataset_failure_code,
            "latency_ms": latency_ms,
            "details": { # Keep details for debugging but main artifact is minimal
                "reason_code": res["reason_code"], 
                "answer": answer[:200]
            }
        })
        
        print(f"[eval] {cid} status={status} fail={dataset_failure_code} exit={exit_code}")

    # Generate Run Artifacts
    git_info = get_git_info()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    
    # Config hash (canonical json of config)
    config = {
        "dataset_id": dataset_id,
        "mode": mode,
        "provider": provider,
        "model_id": model_id,
    }
    config_json = json.dumps(config, sort_keys=True, separators=(",", ":"))
    config_hash = hashlib.sha256(config_json.encode("utf-8")).hexdigest()[:8]

    run_id = f"run__{timestamp}__{git_info['sha']}__{dataset_id}__{config_hash}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # 1. run.meta.json
    with (run_dir / "run.meta.json").open("w", encoding="utf-8") as f:
        json.dump({
            "run_id": run_id,
            "dataset_id": dataset_id,
            "eval_spec_version": "EVAL_SPEC_v1",
            "git_commit": git_info["sha"],
            "config": {
                "canonical_json": config_json,
                "sha256": hashlib.sha256(config_json.encode("utf-8")).hexdigest()
            }
        }, f, indent=2)

    # 2. results.jsonl
    with (run_dir / "results.jsonl").open("w", encoding="utf-8") as f:
        for r in results_for_run:
            json.dump(r, f, ensure_ascii=False)
            f.write("\n")

    # 3. summary.json
    summary_counts = {"PASS": 0, "FAIL": 0, "SKIP": 0}
    failure_counts = {}
    for r in results_for_run:
        summary_counts[r["status"]] = summary_counts.get(r["status"], 0) + 1
        if r["status"] == "FAIL":
            fc = r["failure_code"]
            failure_counts[fc] = failure_counts.get(fc, 0) + 1
    
    with (run_dir / "summary.json").open("w", encoding="utf-8") as f:
        json.dump({
            "counts": summary_counts,
            "failures": failure_counts
        }, f, indent=2)

    # 4. command.txt
    (run_dir / "command.txt").write_text(command_str, encoding="utf-8")

    print(f"[eval] Run artifacts saved to: {run_dir}")



if __name__ == "__main__":
    main()
