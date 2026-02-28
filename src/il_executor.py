"""
S22/S31: IL Executor
- Deterministic step interpreter
- Always writes il.exec.report.json
- Writes il.exec.result.json only when overall_status == "OK"
- No sys.exit / assert / network I/O
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parent.parent


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
# Args guards / budgets
# ---------------------------------------------------------------------------

OPCODE_ARGS_SPEC: Dict[str, Dict[str, type]] = {
    "SEARCH_TERMS": {"max_terms": int},
    "RETRIEVE": {"max_docs": int},
    "ANSWER": {"style": str, "max_sentences": int},
    "CITE": {"max_cites": int},
    "COLLECT": {
        "source": str,
        "max_docs": int,
        "path": str,
        "policy_filter": bool,
        "policy_max_chars": int,
        "policy_allow_langs_csv": str,
        "policy_hard_denylist_csv": str,
        "policy_soft_warnlist_csv": str,
    },
    "NORMALIZE": {"lowercase": bool},
    "INDEX": {"token_min_len": int},
    "SEARCH_RAG": {"max_docs": int},
    "CITE_RAG": {"max_cites": int},
    "SEARCH": {"max_docs": int},
}

DEFAULT_BUDGET = {
    "max_steps": 64,
    "max_retrieved_docs": 50,
    "max_cites": 50,
}

DEFAULT_COLLECT_POLICY_ALLOW_LANGS = ("ja", "en")
DEFAULT_COLLECT_POLICY_MAX_CHARS = 12000
DEFAULT_COLLECT_POLICY_HARD_DENYLIST = (
    "password",
    "passwd",
    "secret",
    "api_key",
    "access_token",
    "private_key",
    "authorization",
    "bearer",
)
DEFAULT_COLLECT_POLICY_SOFT_WARNLIST = (
    "credential",
    "cookie",
    "session",
    "internal_only",
)


def _safe_int(value: Any, default: int) -> int:
    try:
        if isinstance(value, bool):
            return default
        parsed = int(value)
    except Exception:
        return default
    return parsed


def _build_budget(il_body: Dict[str, Any], opcode_count: int) -> Dict[str, int]:
    raw = il_body.get("budget")
    budget = dict(DEFAULT_BUDGET)
    budget["max_steps"] = max(opcode_count, 1)
    if isinstance(raw, dict):
        budget["max_steps"] = max(1, _safe_int(raw.get("max_steps", budget["max_steps"]), budget["max_steps"]))
        budget["max_retrieved_docs"] = max(
            1,
            _safe_int(raw.get("max_retrieved_docs", budget["max_retrieved_docs"]), budget["max_retrieved_docs"]),
        )
        budget["max_cites"] = max(1, _safe_int(raw.get("max_cites", budget["max_cites"]), budget["max_cites"]))
    return budget


def _validate_opcode_args(op_name: str, args: Any) -> Tuple[bool, str]:
    if not isinstance(args, dict):
        return False, f"E_OPCODE_ARGS: args must be object for {op_name}, got {type(args).__name__}"

    spec = OPCODE_ARGS_SPEC.get(op_name)
    if spec is None:
        return True, ""

    for key in args.keys():
        if key not in spec:
            return False, f"E_OPCODE_ARGS: unexpected arg '{key}' for {op_name}"

    for key, expected_type in spec.items():
        if key not in args:
            continue
        value = args[key]
        if expected_type is int:
            if not isinstance(value, int) or isinstance(value, bool):
                return False, f"E_OPCODE_ARGS: {op_name}.args.{key} must be int"
            if value <= 0:
                return False, f"E_OPCODE_ARGS: {op_name}.args.{key} must be > 0"
        elif expected_type is str:
            if not isinstance(value, str) or not value.strip():
                return False, f"E_OPCODE_ARGS: {op_name}.args.{key} must be non-empty string"
        elif expected_type is bool:
            if not isinstance(value, bool):
                return False, f"E_OPCODE_ARGS: {op_name}.args.{key} must be bool"
    return True, ""


def _resolve_repo_relative_path(path_text: str) -> Tuple[Optional[Path], str]:
    raw = str(path_text or "").strip()
    if not raw:
        return None, "path is required"
    p = Path(raw)
    if p.is_absolute():
        return None, "absolute path is not allowed"
    if ".." in p.parts:
        return None, "path traversal is not allowed"
    resolved = (REPO_ROOT / p).resolve()
    try:
        resolved.relative_to(REPO_ROOT)
    except Exception:
        return None, "path must stay inside repository root"
    return resolved, ""


def _doc_text(doc: Dict[str, Any]) -> str:
    body = str(doc.get("content", "") or doc.get("text", "")).strip()
    title = str(doc.get("title", "")).strip()
    if title and body:
        return f"{title}\n{body}"
    return title or body


def _extract_snippet(doc: Dict[str, Any], terms: List[str], max_chars: int = 180) -> str:
    payload = re.sub(r"\s+", " ", _doc_text(doc)).strip()
    if not payload:
        return ""
    payload_lower = payload.lower()
    min_idx: Optional[int] = None
    for term in terms:
        t = str(term or "").strip().lower()
        if not t:
            continue
        idx = payload_lower.find(t)
        if idx >= 0 and (min_idx is None or idx < min_idx):
            min_idx = idx
    start = max(0, (min_idx or 0) - 40)
    return payload[start : start + max_chars].strip()


def _split_csv(value: str) -> List[str]:
    out: List[str] = []
    seen = set()
    for raw in str(value or "").split(","):
        token = raw.strip().lower()
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def _safe_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        token = value.strip().lower()
        if token in {"true", "1", "yes", "on"}:
            return True
        if token in {"false", "0", "no", "off"}:
            return False
    return default


def _detect_lang_tag(text: str) -> str:
    payload = str(text or "")
    if not payload.strip():
        return "und"
    ja_count = len(re.findall(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]", payload))
    en_count = len(re.findall(r"[A-Za-z]", payload))
    if ja_count == 0 and en_count == 0:
        return "und"
    if ja_count >= en_count and ja_count > 0:
        return "ja"
    if en_count > 0:
        return "en"
    return "und"


def _resolve_collect_policy(args: Dict[str, Any]) -> Dict[str, Any]:
    allow_langs = _split_csv(args.get("policy_allow_langs_csv", ",".join(DEFAULT_COLLECT_POLICY_ALLOW_LANGS)))
    if not allow_langs:
        allow_langs = list(DEFAULT_COLLECT_POLICY_ALLOW_LANGS)

    hard_denylist = _split_csv(
        args.get("policy_hard_denylist_csv", ",".join(DEFAULT_COLLECT_POLICY_HARD_DENYLIST))
    )
    soft_warnlist = _split_csv(
        args.get("policy_soft_warnlist_csv", ",".join(DEFAULT_COLLECT_POLICY_SOFT_WARNLIST))
    )
    max_chars = _safe_int(args.get("policy_max_chars", DEFAULT_COLLECT_POLICY_MAX_CHARS), DEFAULT_COLLECT_POLICY_MAX_CHARS)
    max_chars = max(1, max_chars)

    return {
        "allow_langs": allow_langs,
        "max_chars": max_chars,
        "hard_denylist": hard_denylist,
        "soft_warnlist": soft_warnlist,
    }


def _apply_collect_policy(docs: List[Dict[str, Any]], args: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    policy = _resolve_collect_policy(args)
    allow_langs = set(policy["allow_langs"])
    max_chars = int(policy["max_chars"])
    hard_denylist = list(policy["hard_denylist"])
    soft_warnlist = list(policy["soft_warnlist"])

    accepted: List[Dict[str, Any]] = []
    rejected_count_by_code: Dict[str, int] = {}
    soft_warn_hits: List[Dict[str, Any]] = []
    rejected_samples: List[Dict[str, Any]] = []

    for doc in docs:
        doc_id = str(doc.get("doc_id", ""))
        payload = _doc_text(doc)
        payload_lower = payload.lower()
        lang = _detect_lang_tag(payload)

        reasons: List[Tuple[str, str]] = []
        if len(payload) > max_chars:
            reasons.append(("E_RAG_POLICY_SIZE", f"chars={len(payload)} max_chars={max_chars}"))
        if allow_langs and lang not in allow_langs:
            reasons.append(("E_RAG_POLICY_LANG", f"lang={lang} allowed={sorted(allow_langs)}"))

        hard_hits: List[str] = []
        for token in hard_denylist:
            if token and token in payload_lower:
                hard_hits.append(token)
        if hard_hits:
            reasons.append(("E_RAG_POLICY_DENYLIST", f"matched={','.join(hard_hits[:3])}"))

        soft_hits = [token for token in soft_warnlist if token and token in payload_lower]
        if reasons:
            unique_codes = sorted({code for code, _ in reasons})
            for code in unique_codes:
                rejected_count_by_code[code] = rejected_count_by_code.get(code, 0) + 1
            rejected_samples.append(
                {
                    "doc_id": doc_id,
                    "lang": lang,
                    "codes": unique_codes,
                }
            )
            continue

        accepted_doc = dict(doc)
        accepted_doc["_policy"] = {"lang": lang, "soft_warn_hits": soft_hits}
        accepted.append(accepted_doc)
        if soft_hits:
            soft_warn_hits.append({"doc_id": doc_id, "hits": soft_hits[:5]})

    summary = {
        "policy_enabled": True,
        "allow_langs": sorted(allow_langs),
        "max_chars": max_chars,
        "hard_denylist_size": len(hard_denylist),
        "soft_warnlist_size": len(soft_warnlist),
        "accepted_count": len(accepted),
        "rejected_count": len(docs) - len(accepted),
        "warn_count": len(soft_warn_hits),
        "reject_reason_codes": sorted(rejected_count_by_code.keys()),
        "reject_reason_counts": dict(sorted(rejected_count_by_code.items(), key=lambda kv: kv[0])),
        "warn_samples": soft_warn_hits[:5],
        "rejected_samples": rejected_samples[:5],
    }
    return accepted, summary


def _load_docs_from_jsonl(path: Path) -> Tuple[List[Dict[str, Any]], str]:
    docs: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                raw = line.strip()
                if not raw:
                    continue
                try:
                    item = json.loads(raw)
                except Exception as exc:
                    return [], f"line {lineno}: invalid json ({exc})"
                if not isinstance(item, dict):
                    return [], f"line {lineno}: row must be object"
                doc_id = str(item.get("doc_id") or item.get("id") or f"{path.stem}_{lineno:04d}").strip()
                title = str(item.get("title") or "").strip()
                source = str(item.get("source") or f"{path.as_posix()}#L{lineno}").strip()
                text = str(
                    item.get("text")
                    or item.get("content")
                    or item.get("body")
                    or item.get("description")
                    or ""
                ).strip()
                docs.append(
                    {
                        "doc_id": doc_id,
                        "title": title,
                        "source": source,
                        "text": text,
                        "content": text,
                    }
                )
    except Exception as exc:
        return [], f"read failed: {exc}"
    return sorted(docs, key=lambda d: str(d.get("doc_id", ""))), ""


def _xml_find_text(node: ET.Element, tags: List[str]) -> str:
    for tag in tags:
        child = node.find(tag)
        if child is not None and child.text:
            text = child.text.strip()
            if text:
                return text
    return ""


def _load_docs_from_rss(path: Path) -> Tuple[List[Dict[str, Any]], str]:
    try:
        root = ET.parse(path).getroot()
    except Exception as exc:
        return [], f"rss parse failed: {exc}"

    ns_atom = "{http://www.w3.org/2005/Atom}"
    items = list(root.findall(".//item"))
    if not items:
        items = list(root.findall(f".//{ns_atom}entry"))

    docs: List[Dict[str, Any]] = []
    for idx, item in enumerate(items, 1):
        title = _xml_find_text(item, ["title", f"{ns_atom}title"])
        description = _xml_find_text(
            item,
            [
                "description",
                f"{ns_atom}summary",
                f"{ns_atom}content",
            ],
        )
        link = _xml_find_text(item, ["link", f"{ns_atom}link"])
        if not link:
            atom_link = item.find(f"{ns_atom}link")
            if atom_link is not None:
                link = str(atom_link.attrib.get("href", "")).strip()
        guid = _xml_find_text(item, ["guid", f"{ns_atom}id"])
        id_seed = guid or link or f"{title}:{idx}"
        doc_id = f"rss_{hashlib.sha256(id_seed.encode('utf-8')).hexdigest()[:12]}"
        source = link or f"{path.as_posix()}#item={idx}"
        docs.append(
            {
                "doc_id": doc_id,
                "title": title,
                "source": source,
                "text": description,
                "content": description,
            }
        )

    return sorted(docs, key=lambda d: str(d.get("doc_id", ""))), ""


# ---------------------------------------------------------------------------
# Opcode handlers (deterministic, no exceptions)
# ---------------------------------------------------------------------------

def _handle_search_terms(il: dict, ctx: dict, args: dict) -> dict:
    terms = il.get("il", {}).get("search_terms")
    if terms is None:
        return {
            "status": "SKIP",
            "reason": "E_SEARCH_TERMS_MISSING: no search_terms in IL",
            "in_summary": "search_terms: missing",
            "out_summary": {},
        }
    if not isinstance(terms, list):
        return {
            "status": "ERROR",
            "reason": f"E_SEARCH_TERMS_TYPE: search_terms must be list, got {type(terms).__name__}",
            "in_summary": f"search_terms type: {type(terms).__name__}",
            "out_summary": {},
        }
    for i, t in enumerate(terms):
        if not isinstance(t, str):
            return {
                "status": "ERROR",
                "reason": f"E_SEARCH_TERMS_ITEM_TYPE: search_terms[{i}] must be str, got {type(t).__name__}",
                "in_summary": {"terms_count": len(terms)},
                "out_summary": {},
            }

    unique_terms = sorted({x.strip().lower() for x in terms if isinstance(x, str) and x.strip()})
    max_terms = int(args.get("max_terms", len(unique_terms) or 1))
    unique_terms = unique_terms[: max(1, max_terms)]

    ctx["search_terms"] = unique_terms
    return {
        "status": "OK",
        "reason": f"validated {len(unique_terms)} unique terms",
        "in_summary": {"terms_count": len(terms), "terms_preview": unique_terms[:3]},
        "out_summary": {"terms": unique_terms},
    }


def _handle_retrieve(_il: dict, ctx: dict, args: dict) -> dict:
    if "fixture_db_error" in ctx:
        return {
            "status": "SKIP",
            "reason": f"E_RETRIEVE_FIXTURE_LOAD: {ctx.get('fixture_db_error', '')}",
            "in_summary": "fixture_db: load_error",
            "out_summary": {},
        }

    fixture_db = ctx.get("fixture_db")
    if fixture_db is None:
        return {
            "status": "SKIP",
            "reason": "E_RETRIEVE_NO_FIXTURE: no fixture DB provided",
            "in_summary": "fixture_db: missing",
            "out_summary": {},
        }

    terms = ctx.get("search_terms")
    if not terms:
        return {
            "status": "SKIP",
            "reason": "E_RETRIEVE_NO_TERMS: no search_terms available from prior step",
            "in_summary": "search_terms: empty",
            "out_summary": {},
        }

    index = fixture_db.get("index", {})
    docs_list = fixture_db.get("docs", [])
    if not isinstance(index, dict):
        return {
            "status": "ERROR",
            "reason": "E_RETRIEVE_INDEX_SCHEMA: fixture_db.index must be object",
            "in_summary": {"index_type": type(index).__name__},
            "out_summary": {},
        }
    if not isinstance(docs_list, list):
        return {
            "status": "ERROR",
            "reason": "E_RETRIEVE_DOCS_SCHEMA: fixture_db.docs must be list",
            "in_summary": {"docs_type": type(docs_list).__name__},
            "out_summary": {},
        }

    docs_by_id = {str(d.get("doc_id", "")): d for d in docs_list if isinstance(d, dict) and "doc_id" in d}

    matched_ids = set()
    normalized_terms = [str(t).strip().lower() for t in terms if str(t).strip()]
    for term in normalized_terms:
        ids = index.get(term, [])
        if isinstance(ids, list):
            matched_ids.update(str(x) for x in ids)

    # Fallback scanning (still deterministic) when index misses but docs are present.
    if not matched_ids and docs_by_id:
        for doc_id, doc in sorted(docs_by_id.items(), key=lambda kv: kv[0]):
            payload = _doc_text(doc).lower()
            if any(term in payload for term in normalized_terms):
                matched_ids.add(doc_id)

    if not matched_ids:
        ctx["retrieved"] = []
        return {
            "status": "SKIP",
            "reason": f"E_RETRIEVE_NO_HIT: no docs found for terms={terms}",
            "in_summary": {"terms": terms},
            "out_summary": {"retrieved_count": 0, "ranking_version": "v2"},
        }

    ranked_rows: List[Dict[str, Any]] = []
    missing = []
    for did in sorted(matched_ids):
        doc = docs_by_id.get(did)
        if not isinstance(doc, dict):
            missing.append(did)
            continue
        payload = _doc_text(doc).lower()
        hit_count = sum(1 for term in normalized_terms if term and term in payload)
        term_coverage = hit_count / max(len(normalized_terms), 1)
        length_penalty = min(len(payload), 4000) / 4000.0
        score = round((term_coverage * 10.0) - length_penalty, 6)
        ranked_rows.append(
            {
                "doc_id": did,
                "doc": doc,
                "score": score,
                "term_coverage": round(term_coverage, 6),
                "payload_len": len(payload),
            }
        )

    ranked_rows.sort(key=lambda row: (-float(row["score"]), str(row["doc_id"])))
    max_docs = min(int(args.get("max_docs", ctx["budget"]["max_retrieved_docs"])), ctx["budget"]["max_retrieved_docs"])
    ranked_rows = ranked_rows[: max(1, max_docs)]
    retrieved = [row["doc"] for row in ranked_rows]
    ctx["retrieved"] = retrieved

    if not retrieved:
        return {
            "status": "SKIP",
            "reason": "E_RETRIEVE_EMPTY_AFTER_FILTER: retrieved docs empty",
            "in_summary": {"matched_ids": sorted(matched_ids)},
            "out_summary": {"missing_doc_ids": missing, "ranking_version": "v2"},
        }

    return {
        "status": "OK",
        "reason": f"retrieved {len(retrieved)} docs from fixture DB",
        "in_summary": {"terms": terms, "matched_ids": sorted(matched_ids)},
        "out_summary": {
            "retrieved_count": len(retrieved),
            "doc_ids": [str(d.get("doc_id", "")) for d in retrieved],
            "missing_doc_ids": missing,
            "ranking_version": "v2",
            "score_preview": [
                {
                    "doc_id": str(row["doc_id"]),
                    "score": row["score"],
                    "term_coverage": row["term_coverage"],
                }
                for row in ranked_rows[:5]
            ],
        },
    }


def _handle_answer(_il: dict, ctx: dict, args: dict) -> dict:
    retrieved = ctx.get("retrieved") or []
    if not isinstance(retrieved, list) or not retrieved:
        return {
            "status": "SKIP",
            "reason": "E_ANSWER_NO_RETRIEVED: no retrieved docs",
            "in_summary": "retrieved: empty",
            "out_summary": {},
        }

    terms = ctx.get("search_terms") or []
    style = str(args.get("style", "brief")).strip().lower() or "brief"
    max_sentences = int(args.get("max_sentences", 2))
    max_sentences = min(max(1, max_sentences), 5)

    docs = sorted(retrieved, key=lambda d: str(d.get("doc_id", "")))
    docs_preview = [
        f"{str(d.get('doc_id', ''))}: {str(d.get('title', '')).strip() or '(untitled)'}" for d in docs[: max_sentences]
    ]
    terms_text = ", ".join(sorted({str(t) for t in terms if isinstance(t, str)}))

    if style == "bullets":
        answer = "\n".join([f"- {line}" for line in docs_preview])
    else:
        answer = f"Matched {len(docs)} documents for terms [{terms_text}]. Top docs: " + "; ".join(docs_preview)

    ctx["answer"] = answer
    return {
        "status": "OK",
        "reason": f"generated deterministic answer from {len(docs)} docs",
        "in_summary": {"retrieved_count": len(docs), "terms": terms},
        "out_summary": {"answer_chars": len(answer), "style": style},
    }


def _handle_cite(_il: dict, ctx: dict, args: dict) -> dict:
    retrieved = ctx.get("retrieved")
    if not retrieved:
        return {
            "status": "SKIP",
            "reason": "E_CITE_NO_RETRIEVED: no retrieved docs to cite",
            "in_summary": "retrieved: empty",
            "out_summary": {},
        }

    max_cites = int(args.get("max_cites", ctx["budget"]["max_cites"]))
    max_cites = min(max(1, max_cites), ctx["budget"]["max_cites"])

    cites = []
    terms = [str(t) for t in (ctx.get("search_terms") or []) if str(t).strip()]
    for doc in sorted(retrieved, key=lambda d: str(d.get("doc_id", "")))[:max_cites]:
        doc_id = str(doc.get("doc_id", ""))
        source = str(doc.get("source", ""))
        title = str(doc.get("title", ""))
        cite_input = f"{doc_id}\n{source}"
        cite_key = hashlib.sha256(cite_input.encode("utf-8")).hexdigest()[:16]
        snippet = _extract_snippet(doc, terms)
        snippet_sha256 = hashlib.sha256(snippet.encode("utf-8")).hexdigest() if snippet else ""
        cites.append(
            {
                "cite_key": cite_key,
                "doc_id": doc_id,
                "source": source,
                "title": title,
                "source_path": source,
                "snippet": snippet,
                "snippet_sha256": snippet_sha256,
            }
        )

    ctx["cites"] = cites
    return {
        "status": "OK",
        "reason": f"generated {len(cites)} cite keys",
        "in_summary": {"retrieved_count": len(retrieved)},
        "out_summary": {
            "cites_count": len(cites),
            "cite_keys": [c["cite_key"] for c in cites],
            "provenance_fields": ["source_path", "snippet", "snippet_sha256"],
        },
    }


def _tokenize(text: str, min_len: int = 2) -> List[str]:
    return [tok for tok in re.findall(r"[A-Za-z0-9_]{2,64}", (text or "").lower()) if len(tok) >= min_len]


def _handle_collect(_il: dict, ctx: dict, args: dict) -> dict:
    source = str(args.get("source", "fixture"))
    max_docs = int(args.get("max_docs", ctx["budget"]["max_retrieved_docs"]))
    max_docs = min(max(1, max_docs), ctx["budget"]["max_retrieved_docs"])

    fixture_db = ctx.get("fixture_db")
    policy_enabled = _safe_bool(args.get("policy_filter", True), True)

    def _apply_policy_and_finalize(loaded_docs: List[Dict[str, Any]], source_label: str, in_summary: Dict[str, Any]) -> dict:
        docs = list(loaded_docs)
        policy_summary: Dict[str, Any] = {
            "policy_enabled": False,
            "accepted_count": len(docs),
            "rejected_count": 0,
            "warn_count": 0,
            "reject_reason_codes": [],
            "reject_reason_counts": {},
            "warn_samples": [],
            "rejected_samples": [],
        }
        if policy_enabled:
            docs, policy_summary = _apply_collect_policy(docs, args)

        docs = docs[:max_docs]
        ctx["rag_docs_raw"] = docs

        reason = f"collected docs from {source_label}"
        if not docs:
            if policy_enabled and policy_summary.get("reject_reason_codes"):
                primary_code = str(policy_summary.get("reject_reason_codes", [])[0])
                reason = f"{primary_code}: no docs after policy filter"
            else:
                reason = f"E_RAG_COLLECT_EMPTY: no docs loaded from {source_label}"
        elif policy_enabled and int(policy_summary.get("rejected_count", 0)) > 0:
            reason = (
                f"collected docs from {source_label} "
                f"(policy accepted={policy_summary.get('accepted_count', 0)} "
                f"rejected={policy_summary.get('rejected_count', 0)})"
            )

        out_summary = {"collected_count": len(docs), "policy": policy_summary}
        return {
            "status": "OK" if docs else "SKIP",
            "reason": reason,
            "in_summary": in_summary,
            "out_summary": out_summary,
        }

    if source == "fixture":
        docs = []
        if isinstance(fixture_db, dict) and isinstance(fixture_db.get("docs"), list):
            docs = [d for d in fixture_db.get("docs", []) if isinstance(d, dict)]
        docs = sorted(docs, key=lambda d: str(d.get("doc_id", "")))
        return _apply_policy_and_finalize(docs, "fixture", {"source": source, "policy_filter": policy_enabled})

    if source in {"file_jsonl", "rss"}:
        raw_path = str(args.get("path", "")).strip()
        if not raw_path:
            return {
                "status": "ERROR",
                "reason": f"E_RAG_COLLECT_PATH: missing args.path for source={source}",
                "in_summary": {"source": source},
                "out_summary": {},
            }
        resolved_path, path_error = _resolve_repo_relative_path(raw_path)
        if resolved_path is None:
            return {
                "status": "ERROR",
                "reason": f"E_RAG_COLLECT_PATH: {path_error}",
                "in_summary": {"source": source, "path": raw_path},
                "out_summary": {},
            }
        if not resolved_path.exists() or not resolved_path.is_file():
            return {
                "status": "ERROR",
                "reason": f"E_RAG_COLLECT_PATH: file not found: {raw_path}",
                "in_summary": {"source": source, "path": raw_path},
                "out_summary": {},
            }

        if source == "file_jsonl":
            loaded_docs, parse_error = _load_docs_from_jsonl(resolved_path)
        else:
            loaded_docs, parse_error = _load_docs_from_rss(resolved_path)
        if parse_error:
            return {
                "status": "ERROR",
                "reason": f"E_RAG_COLLECT_PARSE: {parse_error}",
                "in_summary": {"source": source, "path": raw_path},
                "out_summary": {},
            }

        return _apply_policy_and_finalize(
            loaded_docs,
            source,
            {"source": source, "path": raw_path, "policy_filter": policy_enabled},
        )

    return {
        "status": "ERROR",
        "reason": f"E_RAG_COLLECT_SOURCE: unsupported source={source}",
        "in_summary": {"source": source},
        "out_summary": {},
    }


def _handle_normalize(_il: dict, ctx: dict, args: dict) -> dict:
    raw_docs = ctx.get("rag_docs_raw")
    if not isinstance(raw_docs, list) or not raw_docs:
        return {
            "status": "SKIP",
            "reason": "E_RAG_NORMALIZE_EMPTY: no collected docs",
            "in_summary": "rag_docs_raw: empty",
            "out_summary": {},
        }
    lowercase = bool(args.get("lowercase", True))
    normalized = []
    for doc in raw_docs:
        title = str(doc.get("title", "")).strip()
        content = str(doc.get("content", "") or doc.get("text", "")).strip()
        if lowercase:
            title = title.lower()
            content = content.lower()
        normalized.append(
            {
                "doc_id": str(doc.get("doc_id", "")),
                "title": title,
                "source": str(doc.get("source", "")),
                "content": content,
            }
        )
    ctx["rag_docs"] = sorted(normalized, key=lambda d: d["doc_id"])
    return {
        "status": "OK",
        "reason": f"normalized {len(normalized)} docs",
        "in_summary": {"collected_count": len(raw_docs)},
        "out_summary": {"normalized_count": len(normalized)},
    }


def _handle_index(_il: dict, ctx: dict, args: dict) -> dict:
    docs = ctx.get("rag_docs")
    if not isinstance(docs, list) or not docs:
        return {
            "status": "SKIP",
            "reason": "E_RAG_INDEX_EMPTY: no normalized docs",
            "in_summary": "rag_docs: empty",
            "out_summary": {},
        }
    token_min_len = int(args.get("token_min_len", 2))
    token_min_len = max(2, token_min_len)

    inverted: Dict[str, List[str]] = {}
    for doc in docs:
        doc_id = str(doc.get("doc_id", ""))
        payload = f"{doc.get('title', '')}\n{doc.get('content', '')}"
        tokens = sorted(set(_tokenize(payload, min_len=token_min_len)))
        for tok in tokens:
            inverted.setdefault(tok, []).append(doc_id)

    for key in list(inverted.keys()):
        inverted[key] = sorted(set(inverted[key]))
    ctx["rag_index"] = dict(sorted(inverted.items(), key=lambda kv: kv[0]))
    return {
        "status": "OK",
        "reason": f"indexed {len(docs)} docs",
        "in_summary": {"docs_count": len(docs)},
        "out_summary": {"token_count": len(inverted)},
    }


def _handle_search_rag(_il: dict, ctx: dict, args: dict) -> dict:
    index = ctx.get("rag_index")
    docs = ctx.get("rag_docs") or []
    if not isinstance(index, dict) or not index:
        return {
            "status": "SKIP",
            "reason": "E_RAG_SEARCH_NO_INDEX: missing rag index",
            "in_summary": "rag_index: empty",
            "out_summary": {},
        }

    terms = ctx.get("search_terms") or []
    if not terms:
        return {
            "status": "SKIP",
            "reason": "E_RAG_SEARCH_NO_TERMS: no search terms",
            "in_summary": "search_terms: empty",
            "out_summary": {},
        }

    max_docs = int(args.get("max_docs", ctx["budget"]["max_retrieved_docs"]))
    max_docs = min(max(1, max_docs), ctx["budget"]["max_retrieved_docs"])

    matched_ids = set()
    for term in terms:
        for tok, ids in index.items():
            if term in tok:
                matched_ids.update(ids)

    doc_map = {str(d.get("doc_id", "")): d for d in docs if isinstance(d, dict)}
    matched_docs = [doc_map[doc_id] for doc_id in sorted(matched_ids) if doc_id in doc_map][:max_docs]
    ctx["rag_retrieved"] = matched_docs

    if not matched_docs:
        return {
            "status": "SKIP",
            "reason": "E_RAG_SEARCH_NO_HIT: no matched docs",
            "in_summary": {"terms": terms},
            "out_summary": {"retrieved_count": 0},
        }

    return {
        "status": "OK",
        "reason": f"rag search matched {len(matched_docs)} docs",
        "in_summary": {"terms": terms},
        "out_summary": {"doc_ids": [str(d.get('doc_id', '')) for d in matched_docs]},
    }


def _handle_cite_rag(_il: dict, ctx: dict, args: dict) -> dict:
    docs = ctx.get("rag_retrieved")
    if not isinstance(docs, list) or not docs:
        return {
            "status": "SKIP",
            "reason": "E_RAG_CITE_NO_DOCS: no rag retrieved docs",
            "in_summary": "rag_retrieved: empty",
            "out_summary": {},
        }

    max_cites = int(args.get("max_cites", ctx["budget"]["max_cites"]))
    max_cites = min(max(1, max_cites), ctx["budget"]["max_cites"])

    cites = []
    terms = [str(t) for t in (ctx.get("search_terms") or []) if str(t).strip()]
    for doc in sorted(docs, key=lambda d: str(d.get("doc_id", "")))[:max_cites]:
        doc_id = str(doc.get("doc_id", ""))
        source = str(doc.get("source", ""))
        title = str(doc.get("title", ""))
        cite_input = f"rag\n{doc_id}\n{source}"
        cite_key = hashlib.sha256(cite_input.encode("utf-8")).hexdigest()[:16]
        snippet = _extract_snippet(doc, terms)
        snippet_sha256 = hashlib.sha256(snippet.encode("utf-8")).hexdigest() if snippet else ""
        cites.append(
            {
                "cite_key": cite_key,
                "doc_id": doc_id,
                "source": source,
                "title": title,
                "source_path": source,
                "snippet": snippet,
                "snippet_sha256": snippet_sha256,
            }
        )

    ctx["cites"] = cites
    return {
        "status": "OK",
        "reason": f"generated {len(cites)} rag cite keys",
        "in_summary": {"retrieved_count": len(docs)},
        "out_summary": {
            "cites_count": len(cites),
            "provenance_fields": ["source_path", "snippet", "snippet_sha256"],
        },
    }


# Opcode dispatch table
_OPCODE_HANDLERS = {
    "SEARCH_TERMS": _handle_search_terms,
    "RETRIEVE": _handle_retrieve,
    "ANSWER": _handle_answer,
    "CITE": _handle_cite,
    "COLLECT": _handle_collect,
    "NORMALIZE": _handle_normalize,
    "INDEX": _handle_index,
    "SEARCH_RAG": _handle_search_rag,
    "CITE_RAG": _handle_cite_rag,
    # Alias
    "SEARCH": _handle_search_rag,
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

    if fixture_db_path:
        try:
            with open(fixture_db_path, "r", encoding="utf-8") as f:
                ctx["fixture_db"] = json.load(f)
        except Exception as e:
            ctx["fixture_db_error"] = str(e)

    il_body = il.get("il", {}) if isinstance(il, dict) else {}
    opcodes = il_body.get("opcodes", [])

    if not isinstance(opcodes, list):
        steps_result.append(
            {
                "index": 0,
                "opcode": "OPCODES",
                "status": "ERROR",
                "reason": f"il.opcodes must be a list, got {type(opcodes).__name__}",
                "in_summary": {"type": type(opcodes).__name__},
                "out_summary": {},
            }
        )
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

    budget = _build_budget(il_body if isinstance(il_body, dict) else {}, len(opcodes))
    ctx["budget"] = budget
    if len(opcodes) > budget["max_steps"]:
        steps_result.append(
            {
                "index": 0,
                "opcode": "BUDGET",
                "status": "ERROR",
                "reason": f"E_BUDGET_MAX_STEPS: opcodes={len(opcodes)} exceeds max_steps={budget['max_steps']}",
                "in_summary": {"opcode_count": len(opcodes), "budget": budget},
                "out_summary": {},
            }
        )

    if not steps_result:
        for i, op_def in enumerate(opcodes):
            if not isinstance(op_def, dict):
                steps_result.append(
                    {
                        "index": i,
                        "opcode": "UNKNOWN",
                        "status": "ERROR",
                        "reason": f"opcode entry must be an object, got {type(op_def).__name__}",
                        "in_summary": {"type": type(op_def).__name__},
                        "out_summary": {},
                    }
                )
                continue

            op_name = str(op_def.get("op", "UNKNOWN"))
            args = op_def.get("args", {})
            valid_args, args_reason = _validate_opcode_args(op_name, args)
            if not valid_args:
                steps_result.append(
                    {
                        "index": i,
                        "opcode": op_name,
                        "status": "ERROR",
                        "reason": args_reason,
                        "in_summary": {"args": args},
                        "out_summary": {},
                    }
                )
                continue

            handler = _OPCODE_HANDLERS.get(op_name)
            if handler is None:
                steps_result.append(
                    {
                        "index": i,
                        "opcode": op_name,
                        "status": "SKIP",
                        "reason": f"unknown opcode: {op_name}",
                        "in_summary": {},
                        "out_summary": {},
                    }
                )
                continue

            try:
                result = handler(il, ctx, args)
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
        "budget": budget,
    }

    report_path = str(Path(out_dir) / "il.exec.report.json")
    try:
        write_json(report_path, report)
    except Exception as e:
        print(f"ERROR: failed to write report: {e}")

    if overall == "OK":
        result_obj = {
            "schema": "IL_EXEC_RESULT_v1",
            "answer": str(ctx.get("answer", "")),
            "cites": ctx.get("cites", []),
        }
        result_path = str(Path(out_dir) / "il.exec.result.json")
        try:
            write_json(result_path, result_obj)
        except Exception as e:
            print(f"ERROR: failed to write result: {e}")

    return report
