#!/usr/bin/env python3
import json
import os
import re
import requests
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "eval" / "questions.jsonl"
OUT_DIR = ROOT / "eval" / "results"

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
                # 参照ブロック終了（空行以外の非リスト行が出たら終わりとみなす実装もあるが、
                # ここでは簡易に「見出しが来るまで」あるいは「最後まで」拾うならこれでもよいが、
                # 仕様上 "参照:" の次はリストが続くと仮定。
                # 安全のため、明らかに別のセクション見出しっぽいものが来たら抜ける
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
    
    # has_sources check is now strict based on parsed sources check in caller usually, 
    # but here we rely on the passed flag which is derived from strict parsing
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
        # Strong Check 1: 結論行のヒューリスティック (Mixed Hallucination)
        # "Unknown but..." logic is suspicious
        if conclusion_line:
            # 逃げ口上っぽい接続詞
            bad_terms = ["ただし", "しかし", "一方", "ちなみに", "可能性があります", "ですが", "一般的"]
            if any(t in conclusion_line for t in bad_terms):
                return ReasonCode.POSITIVE_HALLUCINATION

        # Strong Check 2: Sourcesがあるなら Hallucination... BUT ONLY IF ANSWER IS NOT UNKNOWN
        # (If LLM says "Unknown" validly, it might still cite sources it checked. That is OK.)
        # mentions_unknown check is based on strict conclusion line if available.
        # So logic is: If it HAS sources AND does NOT mention unknown -> It's a hallucination (answer with support).
        
        # Note: apply_type_constraints args don't include mentions_unknown directly?
        # Standard workflow: determine_standard_fail_reason uses mentions_unknown to set UNKNOWN_ANSWER.
        # So we can check if fail_reason_code == UNKNOWN_ANSWER.
        
        is_unknown = (fail_reason_code == ReasonCode.UNKNOWN_ANSWER)
        
        if has_sources and not is_unknown:
            return ReasonCode.POSITIVE_HALLUCINATION

        # Pass if Unknown/NoSource/ContextEmpty
        if fail_reason_code in (
            ReasonCode.UNKNOWN_ANSWER,
            ReasonCode.CONTEXT_EMPTY,
            ReasonCode.NO_SOURCES
        ):
            return None
        
        # Answered normally (fail_reason_code is None) -> Hallucination
        if fail_reason_code is None:
            return ReasonCode.POSITIVE_HALLUCINATION
            
        return fail_reason_code

    # Normal/Ref/Boundary/MultiChunk
    if fail_reason_code is None:
        if not has_required_source:
            return ReasonCode.MISSING_REQUIRED_SOURCE
        
        # Evidence Check Logic
        if not has_expected_evidence:
            return ReasonCode.MISSING_EXPECTED_EVIDENCE

    return fail_reason_code


def _norm(s: str) -> str:
    # 空白/改行/タブを潰して比較を安定化
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

    # 1. Parse Structure
    extracted_sources = parse_sources(answer)
    # S1: "不明" などのダミー参照は sources としてカウントしない
    valid_sources = [s for s in extracted_sources if not any(tok in s for tok in UNKNOWN_TOKENS)]
    has_sources = len(valid_sources) > 0
    conclusion_line = extract_conclusion_line(answer)

    # 2. Unknown Check (Strict: only in Conclusion)
    # 結論行が取れない場合は FORMAT_INVALID とする（空でない場合）
    format_invalid = (exit_code == 0 and bool(answer) and conclusion_line is None)

    target_text = conclusion_line or ""
    mentions_unknown = any(tok in target_text for tok in UNKNOWN_TOKENS)

    # 3. Source Check (Strict)
    has_required_source = True
    if expected_source:
        has_required_source = False
        # expected_source が extracted_sources のいずれかに含まれるか
        # suffix match logic (e.g. "hello.md" matches "hello.md#chunk-0")
        for src in extracted_sources:
            if expected_source in src:
                has_required_source = True
                break

    # 4. Evidence Check (Mode: ANY vs ALL)
    has_expected_evidence = True
    matched_evidence = None  # for ANY mode compatibility
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

    # 5. Determine Fail Reason
    if format_invalid:
        fail_reason_code = ReasonCode.FORMAT_INVALID
    else:
        fail_reason_code = determine_standard_fail_reason(
            answer, stderr, exit_code, mentions_unknown, has_sources
        )

    # 6. Evaluate Constraints based on Type
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
    """
    SERVER_UNREACHABLE (101)
    SERVER_MODEL_MISSING (102)
    INFERENCE_FAILED (103)
    """
    result = {
        "status": "ok",
        "latency_ms": 0,
        "model_id": None,
        "reason_code": None,
        "exit_code": 0,
    }

    # 1. Connectivity & Models check
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

    # 2. Minimal Inference check
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


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    out_path = OUT_DIR / f"{ts}.jsonl"

    # --- Pre-flight Check ---
    base_url = os.getenv("OPENAI_API_BASE", "http://127.0.0.1:8080/v1")
    pf = check_server_status(base_url)

    with out_path.open("w", encoding="utf-8") as f:
        meta = {
            "meta": "pre_flight",
            "timestamp": ts,
            "pre_flight": pf,
        }
        f.write(json.dumps(meta, ensure_ascii=False) + "\n")

    if pf["status"] != "ok":
        print(f"[eval] PRE-FLIGHT FAILED: {pf['reason_code']} (exit={pf['exit_code']})")
        if "error" in pf:
            print(f"       Error: {pf['error']}")
        sys.exit(pf["exit_code"])

    print(f"[eval] PRE-FLIGHT OK: latency={pf['latency_ms']}ms model={pf['model_id']}")

    if not QUESTIONS.exists():
        raise SystemExit(f"questions not found: {QUESTIONS}")

    lines = [
        line.strip()
        for line in QUESTIONS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    failed = 0

    for line in lines:
        q = json.loads(line)
        qid = q["id"]
        question = q["question"]
        q_type = q.get("type", "normal")

        p = subprocess.run(
            [sys.executable, str(ROOT / "src" / "ask.py"), question],
            capture_output=True,
            text=True,
        )

        answer = (p.stdout or "").strip()
        err = (p.stderr or "").strip()

        # Analysis Logic Extracted
        res = analyze_result(q, answer, p.returncode, err)

        if not res["passed"]:
            failed += 1

        rec = {
            "id": qid,
            "question": question,
            "type": q_type,
            "exit_code": p.returncode,
            "passed": res["passed"],
            "reason_code": res["reason_code"],
            "answer": answer,
            "stderr": err,
            "details": res["details"]
        }

        with out_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        reason_str = res["reason_code"] if res["reason_code"] else "-"
        print(f"[eval] {qid} type={q_type} pass={res['passed']} exit={p.returncode} reason={reason_str}")

    print(f"[eval] saved: {out_path}")
    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
