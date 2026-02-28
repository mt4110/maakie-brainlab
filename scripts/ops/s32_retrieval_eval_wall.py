#!/usr/bin/env python3
"""
S32-05: Retrieval eval wall v1.

Evaluate retrieval/citation quality from deterministic case records.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple


DEFAULT_OUT_DIR = "docs/evidence/s32-05"
DEFAULT_CASES_JSONL = "tests/fixtures/s32_05/retrieval_eval_cases.jsonl"


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _as_str_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out


def _to_repo_rel(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except Exception:
        return str(path)


def load_cases_jsonl(path: Path) -> Tuple[List[Dict[str, Any]], str]:
    if not path.exists():
        return [], f"cases file not found: {path}"

    rows: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                raw = line.strip()
                if not raw:
                    continue
                try:
                    obj = json.loads(raw)
                except Exception as exc:
                    return [], f"invalid json line {lineno}: {exc}"
                if not isinstance(obj, dict):
                    return [], f"line {lineno}: row must be object"
                rows.append(obj)
    except Exception as exc:
        return [], str(exc)
    return rows, ""


def _normalize_case(row: Dict[str, Any]) -> Dict[str, Any]:
    case_id = str(row.get("case_id") or row.get("id") or "").strip() or "unknown"
    expected = _as_str_list(row.get("expected_doc_ids"))
    retrieved = _as_str_list(row.get("retrieved_doc_ids"))
    cited = _as_str_list(row.get("cited_doc_ids"))
    policy_rejected_count = _to_int(row.get("policy_rejected_count", 0), 0)

    return {
        "case_id": case_id,
        "expected_doc_ids": expected,
        "retrieved_doc_ids": retrieved,
        "cited_doc_ids": cited,
        "policy_rejected_count": max(0, policy_rejected_count),
    }


def evaluate_cases(
    rows: List[Dict[str, Any]],
    *,
    k: int,
    min_hit_rate: float,
    min_citation_coverage: float,
    max_no_hit_rate: float,
    max_policy_reject_rate: float,
) -> Dict[str, Any]:
    norm = [_normalize_case(row) for row in rows]
    total_cases = len(norm)

    k = max(1, int(k))
    hit_checked = 0
    hit_success = 0
    no_hit_count = 0
    citation_case_count = 0
    citation_coverage_sum = 0.0
    total_retrieved_docs = 0
    total_policy_rejected = 0

    for row in norm:
        expected = row["expected_doc_ids"]
        retrieved = row["retrieved_doc_ids"]
        cited = row["cited_doc_ids"]

        retrieved_topk = retrieved[:k]
        retrieved_set = set(retrieved)
        cited_set = set(cited)

        if expected:
            hit_checked += 1
            if any(doc_id in set(retrieved_topk) for doc_id in expected):
                hit_success += 1

        if not retrieved:
            no_hit_count += 1
        else:
            citation_case_count += 1
            overlap = len(retrieved_set.intersection(cited_set))
            citation_coverage_sum += overlap / max(len(retrieved_set), 1)

        total_retrieved_docs += len(retrieved)
        total_policy_rejected += int(row["policy_rejected_count"])

    hit_rate_at_k = (hit_success / hit_checked) if hit_checked > 0 else 0.0
    no_hit_rate = (no_hit_count / total_cases) if total_cases > 0 else 1.0
    citation_coverage = (citation_coverage_sum / citation_case_count) if citation_case_count > 0 else 0.0
    policy_reject_rate = total_policy_rejected / max(total_retrieved_docs + total_policy_rejected, 1)

    checks: List[Dict[str, Any]] = []
    checks.append(
        {
            "id": "RET-01",
            "metric": "hit_rate_at_k",
            "observed": round(hit_rate_at_k, 6),
            "target": f">= {min_hit_rate:.3f}",
            "status": "PASS" if hit_rate_at_k >= min_hit_rate else "WARN",
        }
    )
    checks.append(
        {
            "id": "RET-02",
            "metric": "citation_coverage",
            "observed": round(citation_coverage, 6),
            "target": f">= {min_citation_coverage:.3f}",
            "status": "PASS" if citation_coverage >= min_citation_coverage else "WARN",
        }
    )
    checks.append(
        {
            "id": "RET-03",
            "metric": "no_hit_rate",
            "observed": round(no_hit_rate, 6),
            "target": f"<= {max_no_hit_rate:.3f}",
            "status": "PASS" if no_hit_rate <= max_no_hit_rate else "WARN",
        }
    )
    checks.append(
        {
            "id": "RET-04",
            "metric": "policy_reject_rate",
            "observed": round(policy_reject_rate, 6),
            "target": f"<= {max_policy_reject_rate:.3f}",
            "status": "PASS" if policy_reject_rate <= max_policy_reject_rate else "WARN",
        }
    )

    warn_count = sum(1 for c in checks if c["status"] != "PASS")
    status = "PASS"
    if total_cases == 0:
        status = "WARN"
    elif hit_rate_at_k < 0.5 or no_hit_rate > 0.5:
        status = "ERROR"
    elif warn_count > 0:
        status = "WARN"

    return {
        "summary": {
            "status": status,
            "total_cases": total_cases,
            "hit_checked_cases": hit_checked,
            "metrics": {
                "hit_rate_at_k": round(hit_rate_at_k, 6),
                "citation_coverage": round(citation_coverage, 6),
                "no_hit_rate": round(no_hit_rate, 6),
                "policy_reject_rate": round(policy_reject_rate, 6),
            },
            "thresholds": {
                "k": k,
                "min_hit_rate": min_hit_rate,
                "min_citation_coverage": min_citation_coverage,
                "max_no_hit_rate": max_no_hit_rate,
                "max_policy_reject_rate": max_policy_reject_rate,
            },
        },
        "checks": checks,
    }


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = dict(payload.get("summary", {}))
    metrics = dict(summary.get("metrics", {}))
    checks = list(payload.get("checks", []))

    lines = [
        "# S32-05 Retrieval Eval Wall v1",
        "",
        f"- status: `{summary.get('status', '')}`",
        f"- total_cases: `{summary.get('total_cases', 0)}`",
        "",
        "## Metrics",
        "",
        f"- hit_rate_at_k: `{metrics.get('hit_rate_at_k', 0.0)}`",
        f"- citation_coverage: `{metrics.get('citation_coverage', 0.0)}`",
        f"- no_hit_rate: `{metrics.get('no_hit_rate', 0.0)}`",
        f"- policy_reject_rate: `{metrics.get('policy_reject_rate', 0.0)}`",
        "",
        "## Checks",
        "",
    ]
    for row in checks:
        lines.append(
            "- [{status}] {id} {metric} observed={obs} target={target}".format(
                status=row.get("status", "WARN"),
                id=row.get("id", ""),
                metric=row.get("metric", ""),
                obs=row.get("observed", ""),
                target=row.get("target", ""),
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases-jsonl", default=DEFAULT_CASES_JSONL)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--min-hit-rate", type=float, default=0.80)
    parser.add_argument("--min-citation-coverage", type=float, default=0.50)
    parser.add_argument("--max-no-hit-rate", type=float, default=0.20)
    parser.add_argument("--max-policy-reject-rate", type=float, default=0.60)
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[2]
    cases_path = (repo_root / args.cases_jsonl).resolve()
    out_dir = (repo_root / args.out_dir).resolve()

    rows, err = load_cases_jsonl(cases_path)
    if err:
        payload = {
            "schema": "S32_RETRIEVAL_EVAL_WALL_V1",
            "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "summary": {
                "status": "WARN",
                "total_cases": 0,
                "metrics": {
                    "hit_rate_at_k": 0.0,
                    "citation_coverage": 0.0,
                    "no_hit_rate": 1.0,
                    "policy_reject_rate": 0.0,
                },
                "thresholds": {
                    "k": max(1, int(args.k)),
                    "min_hit_rate": args.min_hit_rate,
                    "min_citation_coverage": args.min_citation_coverage,
                    "max_no_hit_rate": args.max_no_hit_rate,
                    "max_policy_reject_rate": args.max_policy_reject_rate,
                },
                "error": err,
            },
            "checks": [],
            "inputs": {
                "cases_jsonl": _to_repo_rel(cases_path, repo_root),
            },
        }
    else:
        eval_payload = evaluate_cases(
            rows,
            k=args.k,
            min_hit_rate=args.min_hit_rate,
            min_citation_coverage=args.min_citation_coverage,
            max_no_hit_rate=args.max_no_hit_rate,
            max_policy_reject_rate=args.max_policy_reject_rate,
        )
        payload = {
            "schema": "S32_RETRIEVAL_EVAL_WALL_V1",
            "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            **eval_payload,
            "inputs": {
                "cases_jsonl": _to_repo_rel(cases_path, repo_root),
            },
        }

    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "retrieval_eval_wall_latest.json"
    md_path = out_dir / "retrieval_eval_wall_latest.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(build_markdown(payload), encoding="utf-8")

    status = str(dict(payload.get("summary", {})).get("status", "WARN"))
    print(f"OK: s32_retrieval_eval_wall status={status} out={out_dir}")
    return 0 if status in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
