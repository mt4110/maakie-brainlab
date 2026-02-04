#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
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


def _norm(s: str) -> str:
    # 空白/改行/タブを潰して比較を安定化
    return "".join((s or "").split()).lower()


def _load_hello_snippet() -> Optional[str]:
    if not HELLO_MD.exists():
        return None
    txt = HELLO_MD.read_text(encoding="utf-8", errors="ignore")
    for line in txt.splitlines():
        s = line.strip()
        if s:
            return s[:60]
    s = txt.strip()
    return s[:60] if s else None


HELLO_SNIPPET = _load_hello_snippet()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    out_path = OUT_DIR / f"{ts}.jsonl"

    if not QUESTIONS.exists():
        raise SystemExit(f"questions not found: {QUESTIONS}")

    lines = [l.strip() for l in QUESTIONS.read_text(encoding="utf-8").splitlines() if l.strip()]
    results = []
    failed = 0

    for line in lines:
        q = json.loads(line)
        qid = q["id"]
        question = q["question"]

        # ask.py をCLIとして叩く（依存関係が増えない・壊れにくい）
        p = subprocess.run(
            [sys.executable, str(ROOT / "src" / "ask.py"), question],
            capture_output=True,
            text=True,
        )

        answer = (p.stdout or "").strip()
        err = (p.stderr or "").strip()

        has_sources = ("参照:" in answer) or ("sources" in answer.lower())
        mentions_unknown = any(tok in answer for tok in UNKNOWN_TOKENS)

        # S2: 参照の妥当性
        has_required_source = REQUIRED_SOURCE_SUBSTR in answer
        hello_snippet = HELLO_SNIPPET
        hello_snippet_present = False
        if hello_snippet:
            hello_snippet_present = _norm(hello_snippet) in _norm(answer)

        fail_reasons: list[str] = []
        if p.returncode != 0:
            fail_reasons.append("ask_exit_nonzero")
        if not answer:
            fail_reasons.append("empty_answer")
        if mentions_unknown:
            fail_reasons.append("mentions_unknown")
        if not has_sources:
            fail_reasons.append("no_sources")
        if not has_required_source:
            fail_reasons.append("missing_required_source")
        if hello_snippet is None:
            fail_reasons.append("hello_md_missing")
        elif not hello_snippet_present:
            fail_reasons.append("missing_hello_evidence")

        passed = len(fail_reasons) == 0
        if not passed:
            failed += 1

        rec = {
            "id": qid,
            "question": question,
            "exit_code": p.returncode,
            "has_sources": has_sources,
            "mentions_unknown": mentions_unknown,
            "has_required_source": has_required_source,
            "hello_snippet": hello_snippet,
            "hello_snippet_present": hello_snippet_present,
            "passed": passed,
            "fail_reasons": fail_reasons,
            "answer": answer,
            "stderr": err,
        }
        results.append(rec)
        out_path.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in results) + "\n",
            encoding="utf-8",
        )

        reasons = ",".join(fail_reasons) if fail_reasons else "-"
        print(f"[eval] {qid} pass={passed} exit={p.returncode} sources={has_sources} reasons={reasons}")

    print(f"[eval] saved: {out_path}")
    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
