#!/usr/bin/env python3
import json
import os
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

# S2: 参照妥当性チェック
REQUIRED_SOURCE_SUBSTR = "hello.md#chunk-0"
HELLO_MD = ROOT / "data" / "raw" / "hello.md"

# S1: unknown/参照なし を fail 扱い（安全側に倒す）
UNKNOWN_TOKENS = (
    "不明",
    "参照なし",
    "参照: 不明",
    "わかりません",
    "unknown",
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
    has_expected_evidence: bool
) -> Optional[str]:
    if q_type == "negative_control":
        # Pass if Unknown/NoSource/ContextEmpty
        if fail_reason_code in (
            ReasonCode.UNKNOWN_ANSWER,
            ReasonCode.CONTEXT_EMPTY,
            ReasonCode.NO_SOURCES
        ):
            return None
        if fail_reason_code is None:
            # Answered normally -> Hallucination
            return ReasonCode.POSITIVE_HALLUCINATION
        return fail_reason_code

    # Normal/Ref/Boundary
    if fail_reason_code is None:
        if not has_required_source:
            return ReasonCode.MISSING_REQUIRED_SOURCE
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

    # Basic Analysis
    mentions_unknown = any(tok in answer for tok in UNKNOWN_TOKENS)
    has_sources = ("参照:" in answer) or ("sources" in answer.lower())

    # Source Check
    has_required_source = True
    if expected_source:
        has_required_source = expected_source in answer

    # Evidence Check
    has_expected_evidence = True
    matched_evidence = None
    if expected_evidence and isinstance(expected_evidence, list):
        has_expected_evidence = False
        for cand in expected_evidence:
            if _norm(cand) in _norm(answer):
                has_expected_evidence = True
                matched_evidence = cand
                break

    # Determine Fail Reason
    fail_reason_code = determine_standard_fail_reason(
        answer, stderr, exit_code, mentions_unknown, has_sources
    )

    # Evaluate Constraints based on Type
    final_reason_code = apply_type_constraints(
        q_type, fail_reason_code, has_required_source, has_expected_evidence
    )

    passed = (final_reason_code is None)

    return {
        "passed": passed,
        "reason_code": final_reason_code,
        "details": {
            "has_sources": has_sources,
            "mentions_unknown": mentions_unknown,
            "has_required_source": has_required_source,
            "has_expected_evidence": has_expected_evidence,
            "matched_evidence": matched_evidence,
        }
    }


def _load_hello_evidence_candidates() -> list[str]:
    if not HELLO_MD.exists():
        return []
    txt = HELLO_MD.read_text(encoding="utf-8", errors="ignore")
    cands: list[str] = []
    for line in txt.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue  # 見出しは根拠検査に使わない
        if len(s) < 6:
            continue  # 短すぎる断片はノイズ
        cands.append(s[:80])
        if len(cands) >= 5:
            break
    return cands


HELLO_EVIDENCE = _load_hello_evidence_candidates()


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
