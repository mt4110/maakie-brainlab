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
QUESTIONS = ROOT / "eval" / "questions.jsonl"
STORE_DIR = ROOT / ".local" / "aiwork"
# Evidence filename should be deterministic for SOT compliance
EVIDENCE_FILE = "eval_results.jsonl"

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


def calculate_spec_hash(spec: Dict[str, Any]) -> str:
    """Calculate a stable hash for the given specification."""
    canonical = json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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
                if re.match(r"^[^:\-]*:$", line):
                    break
    return sources


def _find_first_list_item(lines: list[str], start: int) -> Optional[str]:
    """Scan lines from start, return the first '- ...' item or None if a new section header is hit."""
    for j in range(start, len(lines)):
        after = lines[j].strip()
        if not after:
            continue
        if after.startswith("-"):
            return after.lstrip("- ").strip()
        if re.match(r"^[^:\-]*:$", after):
            return None
    return None


def extract_conclusion_line(answer: str) -> Optional[str]:
    """
    結論: 直下の最初のリスト項目（- ...）を抽出する
    """
    lines = answer.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "結論:":
            return _find_first_list_item(lines, i + 1)
    return None


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
    conclusion_line: Optional[str],
    has_sources: bool
) -> Optional[str]:
    if q_type == "negative_control":
        if conclusion_line:
            bad_terms = ["ただし", "しかし", "一方", "ちなみに", "可能性があります", "ですが", "一般的"]
            if any(t in conclusion_line for t in bad_terms):
                return ReasonCode.POSITIVE_HALLUCINATION

        is_unknown = (fail_reason_code == ReasonCode.UNKNOWN_ANSWER)
        
        if has_sources and not is_unknown:
            return ReasonCode.POSITIVE_HALLUCINATION

        if fail_reason_code in (
            ReasonCode.UNKNOWN_ANSWER,
            ReasonCode.CONTEXT_EMPTY,
            ReasonCode.NO_SOURCES
        ):
            return None
        
        if fail_reason_code is None:
            return ReasonCode.POSITIVE_HALLUCINATION
            
        return fail_reason_code

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
    conclusion_line = extract_conclusion_line(answer)

    format_invalid = (exit_code == 0 and bool(answer) and conclusion_line is None)

    target_text = conclusion_line or ""
    mentions_unknown = any(tok in target_text for tok in UNKNOWN_TOKENS)

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

    final_reason_code = apply_type_constraints(q_type, fail_reason_code, has_required_source, has_expected_evidence, conclusion_line, has_sources)
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
            "conclusion_line": conclusion_line,
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
        answer = "結論:\n- 参照できる根拠が見つかりません。\n\n参照:\n- なし"
        return 0, answer, ""
    
    expected_source = question_data.get("expected_source", "mock_source.md")
    expected_evidence = question_data.get("expected_evidence", [])
    
    evidence_str = ""
    if expected_evidence:
        # For multi_chunk or boundary, we might need multiple items
        evidence_str = "\n".join([f"- {e}" for e in expected_evidence])
    else:
        evidence_str = "- [MOCK] Evidence found."

    answer = f"結論:\n- [MOCK] Success for {spec_hash}\n{evidence_str}\n\n参照:\n- {expected_source}"
    return 0, answer, ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["record", "replay", "verify-only"], default="record")
    parser.add_argument("--provider", choices=["real", "mock"], default="real")
    args = parser.parse_args()

    mode = args.mode
    provider = args.provider

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
        sys.exit(pf["exit_code"])

    print(f"[eval] PRE-FLIGHT OK: provider={provider} model={model_id}")

    if not QUESTIONS.exists():
        raise SystemExit(f"questions not found: {QUESTIONS}")

    lines = [
        line.strip()
        for line in QUESTIONS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    failed = 0

    results_for_evidence = []

    for line in lines:
        q = json.loads(line)
        qid = q["id"]
        question = q["question"]
        q_type = q.get("type", "normal")

        # Define WorkSpec
        spec = {
            "purpose": "evaluation",
            "question_id": qid,
            "question": question,
            "model_id": model_id,
            "type": q_type,
            "provider": provider,
        }
        spec_hash = calculate_spec_hash(spec)
        run_dir = STORE_DIR / spec_hash
        spec_file = run_dir / "spec.json"
        result_file = run_dir / "result.json"

        answer, err, exit_code = "", "", 0

        if mode in ("replay", "verify-only"):
            if not result_file.exists():
                print(f"[eval] ERROR: Missing result for {qid} (hash={spec_hash}) in {mode} mode.")
                sys.exit(1)
            
            with result_file.open("r", encoding="utf-8") as rf:
                stored = json.load(rf)
                # Verify spec consistency
                if stored.get("spec_hash") != spec_hash:
                    print(f"[eval] ERROR: Spec hash mismatch for {qid}. Expected {spec_hash}, found {stored.get('spec_hash')}")
                    sys.exit(1)
                answer = stored["answer"]
                err = stored["stderr"]
                exit_code = stored["exit_code"]
        else:
            # record mode
            if provider == "mock":
                exit_code, answer, err = mock_ask(q, spec_hash)
            else:
                p = subprocess.run(
                    [sys.executable, str(ROOT / "src" / "ask.py"), question],
                    capture_output=True,
                    text=True,
                )
                answer, err, exit_code = (p.stdout or "").strip(), (p.stderr or "").strip(), p.returncode

            # Save artifacts
            if mode == "record":
                run_dir.mkdir(parents=True, exist_ok=True)
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
        res = analyze_result(q, answer, exit_code, err)
        if not res["passed"]:
            failed += 1

        rec = {
            "id": qid,
            "spec_hash": spec_hash,
            "mode": mode,
            "passed": res["passed"],
            "reason_code": res["reason_code"],
            "answer": answer if len(answer) < 500 else answer[:500] + "...", # truncate for evidence
            "details": res["details"]
        }
        results_for_evidence.append(rec)

        reason_str = res["reason_code"] if res["reason_code"] else "-"
        print(f"[eval] {qid} hash={spec_hash[:8]} pass={res['passed']} exit={exit_code} reason={reason_str}")

    # Save evidence
    with evidence_path.open("w", encoding="utf-8") as f:
        meta = {
            "meta": "summary",
            "mode": mode,
            "provider": provider,
            "model_id": model_id,
            "total": len(lines),
            "failed": failed,
            "timestamp": timestamp,
        }
        f.write(json.dumps(meta, ensure_ascii=False, sort_keys=True) + "\n")
        for r in results_for_evidence:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")

    print(f"[evidence] saved: {evidence_path}")
    
    if failed > 0:
        print(f"[eval] FAILED: {failed} questions failed.")
        sys.exit(1)
    print("[eval] ALL PASSED")


if __name__ == "__main__":
    main()
