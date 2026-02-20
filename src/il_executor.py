"""
S22-02: IL Executor (P2 minimal)
- Deterministic step interpreter
- Always writes il.exec.report.json
- Writes il.exec.result.json only when overall_status == "OK"
- No sys.exit / assert / network I/O
"""
import json
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# JSON writer (safe)
# ---------------------------------------------------------------------------

def write_json(path: str, obj: dict) -> None:
    """Write dict as JSON to path. May raise on I/O failure."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, allow_nan=False)


# ---------------------------------------------------------------------------
# overall_status determination
# ---------------------------------------------------------------------------

def determine_overall_status(steps: List[dict]) -> str:
    """
    ERROR > OK > SKIP.
    - If ANY step has status ERROR -> "ERROR"
    - Else if ANY step has status OK -> "OK"
    - Else -> "SKIP"
    """
    has_ok = False
    for s in steps:
        st = s.get("status", "SKIP")
        if st == "ERROR":
            return "ERROR"
        if st == "OK":
            has_ok = True
    return "OK" if has_ok else "SKIP"


# ---------------------------------------------------------------------------
# Opcode handlers (deterministic, no exceptions)
# ---------------------------------------------------------------------------

def _handle_search_terms(il: dict, _ctx: dict) -> dict:
    """Validate explicit search_terms in IL. No derivation in P2."""
    terms = il.get("il", {}).get("search_terms")
    if terms is None:
        return {
            "status": "SKIP",
            "reason": "no search_terms in IL (derivation deferred to next PR)",
            "in_summary": "search_terms: missing",
            "out_summary": {},
        }
    if not isinstance(terms, list):
        return {
            "status": "ERROR",
            "reason": f"search_terms must be list, got {type(terms).__name__}",
            "in_summary": f"search_terms type: {type(terms).__name__}",
            "out_summary": {},
        }
    # Validate all elements are strings
    for i, t in enumerate(terms):
        if not isinstance(t, str):
            return {
                "status": "ERROR",
                "reason": f"search_terms[{i}] must be str, got {type(t).__name__}",
                "in_summary": {"terms_count": len(terms)},
                "out_summary": {},
            }
    # Sort and dedup for determinism
    unique_terms = sorted(set(terms))
    # Store in context for RETRIEVE
    _ctx["search_terms"] = unique_terms
    return {
        "status": "OK",
        "reason": f"validated {len(unique_terms)} unique terms",
        "in_summary": {"terms_count": len(terms), "terms_preview": unique_terms[:3]},
        "out_summary": {"terms": unique_terms},
    }


def _handle_retrieve(il: dict, ctx: dict) -> dict:
    """Retrieve docs from fixture DB using search_terms."""
    fixture_db = ctx.get("fixture_db")
    if fixture_db is None:
        return {
            "status": "SKIP",
            "reason": "no fixture DB provided",
            "in_summary": "fixture_db: missing",
            "out_summary": {},
        }

    terms = ctx.get("search_terms")
    if not terms:
        return {
            "status": "SKIP",
            "reason": "no search_terms available from prior step",
            "in_summary": "search_terms: empty",
            "out_summary": {},
        }

    index = fixture_db.get("index", {})
    docs_list = fixture_db.get("docs", [])
    docs_by_id = {d["doc_id"]: d for d in docs_list if "doc_id" in d}

    # Collect doc_ids from index
    matched_ids = set()
    for term in terms:
        ids = index.get(term, [])
        matched_ids.update(ids)

    if not matched_ids:
        return {
            "status": "SKIP",
            "reason": f"no docs found for terms: {terms}",
            "in_summary": {"terms": terms},
            "out_summary": {"retrieved_count": 0},
        }

    # Deterministic: sort by doc_id
    sorted_ids = sorted(matched_ids)
    retrieved = []
    for did in sorted_ids:
        doc = docs_by_id.get(did)
        if doc:
            retrieved.append(doc)

    ctx["retrieved"] = retrieved
    return {
        "status": "OK",
        "reason": f"retrieved {len(retrieved)} docs from fixture DB",
        "in_summary": {"terms": terms, "matched_ids": sorted_ids},
        "out_summary": {"retrieved_count": len(retrieved), "doc_ids": sorted_ids},
    }


def _handle_answer(_il: dict, _ctx: dict) -> dict:
    """P2: Always SKIP. LLM/non-deterministic answering is deferred."""
    return {
        "status": "SKIP",
        "reason": "P2: LLM/non-deterministic; answering is deferred",
        "in_summary": "N/A (P2)",
        "out_summary": {},
    }


def _handle_cite(_il: dict, ctx: dict) -> dict:
    """Generate deterministic cite_keys from retrieved docs."""
    retrieved = ctx.get("retrieved")
    if not retrieved:
        return {
            "status": "SKIP",
            "reason": "no retrieved docs to cite",
            "in_summary": "retrieved: empty",
            "out_summary": {},
        }

    cites = []
    for doc in retrieved:
        doc_id = doc.get("doc_id", "")
        source = doc.get("source", "")
        title = doc.get("title", "")
        cite_input = f"{doc_id}\n{source}"
        cite_key = hashlib.sha256(cite_input.encode("utf-8")).hexdigest()[:16]
        cites.append({
            "cite_key": cite_key,
            "doc_id": doc_id,
            "source": source,
            "title": title,
        })

    ctx["cites"] = cites
    return {
        "status": "OK",
        "reason": f"generated {len(cites)} cite keys",
        "in_summary": {"retrieved_count": len(retrieved)},
        "out_summary": {"cites_count": len(cites), "cite_keys": [c["cite_key"] for c in cites]},
    }


# Opcode dispatch table
_OPCODE_HANDLERS = {
    "SEARCH_TERMS": _handle_search_terms,
    "RETRIEVE": _handle_retrieve,
    "ANSWER": _handle_answer,
    "CITE": _handle_cite,
}


# ---------------------------------------------------------------------------
# Main executor
# ---------------------------------------------------------------------------

def execute_il(il: dict, out_dir: str, fixture_db_path: Optional[str] = None) -> dict:
    """
    Execute IL steps and produce report (always) and result (OK-only).

    Args:
        il: parsed IL JSON (top-level dict with il/meta/evidence)
        out_dir: directory for output artifacts
        fixture_db_path: optional path to retrieve_db.json

    Returns:
        report dict (also written to out_dir)
    """
    steps_result: List[dict] = []
    ctx: Dict[str, Any] = {}

    # Load fixture DB if provided
    if fixture_db_path:
        try:
            with open(fixture_db_path, "r", encoding="utf-8") as f:
                ctx["fixture_db"] = json.load(f)
        except Exception as e:
            # Not fatal: RETRIEVE will SKIP
            ctx["fixture_db_error"] = str(e)

    # Extract opcodes from IL
    il_body = il.get("il", {})
    opcodes = il_body.get("opcodes", [])

    # Guard: opcodes must be a list
    if not isinstance(opcodes, list):
        steps_result.append({
            "index": 0,
            "opcode": "OPCODES",
            "status": "ERROR",
            "reason": f"il.opcodes must be a list, got {type(opcodes).__name__}",
            "in_summary": {"type": type(opcodes).__name__},
            "out_summary": {},
        })
        report = {
            "schema": "IL_EXEC_REPORT_v1",
            "overall_status": "ERROR",
            "steps": steps_result,
        }
        report_path = str(Path(out_dir) / "il.exec.report.json")
        try:
            write_json(report_path, report)
        except Exception as e:
            print(f"ERROR: failed to write report: {e}")
        return report

    for i, op_def in enumerate(opcodes):
        # Guard: each opcode entry must be a dict
        if not isinstance(op_def, dict):
            steps_result.append({
                "index": i,
                "opcode": "UNKNOWN",
                "status": "ERROR",
                "reason": f"opcode entry must be an object, got {type(op_def).__name__}",
                "in_summary": {"type": type(op_def).__name__},
                "out_summary": {},
            })
            continue
        op_name = op_def.get("op", "UNKNOWN")
        handler = _OPCODE_HANDLERS.get(op_name)

        if handler is None:
            step = {
                "index": i,
                "opcode": op_name,
                "status": "SKIP",
                "reason": f"unknown opcode: {op_name}",
                "in_summary": {},
                "out_summary": {},
            }
        else:
            try:
                result = handler(il, ctx)
                step = {
                    "index": i,
                    "opcode": op_name,
                    "status": result.get("status", "ERROR"),
                    "reason": result.get("reason", "no reason"),
                    "in_summary": result.get("in_summary", {}),
                    "out_summary": result.get("out_summary", {}),
                }
            except Exception as e:
                step = {
                    "index": i,
                    "opcode": op_name,
                    "status": "ERROR",
                    "reason": f"handler exception: {type(e).__name__}: {e}",
                    "in_summary": {},
                    "out_summary": {},
                }
        steps_result.append(step)

    overall = determine_overall_status(steps_result)

    report = {
        "schema": "IL_EXEC_REPORT_v1",
        "overall_status": overall,
        "steps": steps_result,
    }

    # Always write report
    report_path = str(Path(out_dir) / "il.exec.report.json")
    try:
        write_json(report_path, report)
    except Exception as e:
        # Best-effort: report write failure is itself an error
        print(f"ERROR: failed to write report: {e}")

    # Write result only when OK
    if overall == "OK":
        result_obj = {
            "schema": "IL_EXEC_RESULT_v1",
            "answer": "",
            "cites": ctx.get("cites", []),
        }
        result_path = str(Path(out_dir) / "il.exec.result.json")
        try:
            write_json(result_path, result_obj)
        except Exception as e:
            print(f"ERROR: failed to write result: {e}")

    return report
