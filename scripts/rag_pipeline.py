"""
S22-04: IL-planned RAG pipeline (stopless / observable / deterministic)

Five opcodes executed sequentially:
  COLLECT -> NORMALIZE -> INDEX -> SEARCH -> CITE

All artifacts go under a run-scoped obs_dir.
No sys.exit / assert / SystemExit.
Exceptions are captured as ERROR lines, never crash-control.
"""
import json
import hashlib
import os
from pathlib import Path
from typing import List, Dict, Any, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EXCERPT_MAX_CHARS = 200


# ---------------------------------------------------------------------------
# Helpers (no exceptions leak)
# ---------------------------------------------------------------------------

def _sha256_text(text: str) -> str:
    """Content-addressed hash for text."""
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_jsonl(path: Path, items: List[dict]) -> None:
    """Write list of dicts as JSONL (one JSON per line)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, sort_keys=True, ensure_ascii=False,
                               allow_nan=False, separators=(",", ":")) + "\n")


def _write_json(path: Path, obj: dict) -> None:
    """Write dict as JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True,
                  ensure_ascii=False, allow_nan=False)


def _write_text(path: Path, text: str) -> None:
    """Write text file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_result(obs_dir: Path, prefix: str, lines: List[str]) -> None:
    """Write result file for a step."""
    _write_text(obs_dir / f"{prefix}_result.txt", "\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# COLLECT
# ---------------------------------------------------------------------------

def step_collect(obs_dir: Path, source_paths: List[str],
                 repo_root: Path) -> tuple:
    """
    Ingest sources into content-addressed blobs + manifest.
    Returns (manifest_items, STOP).
    """
    log_lines: List[str] = []
    result_lines: List[str] = []
    manifest: List[dict] = []
    blobs_dir = obs_dir / "11_collect_blobs"

    _write_text(obs_dir / "10_header.txt", "COLLECT: ingest sources into blobs")

    for src_rel in sorted(source_paths):
        src_path = repo_root / src_rel
        if not src_path.exists():
            log_lines.append(f"ERROR: source not found: {src_rel}")
            result_lines.append(f"ERROR: source not found: {src_rel}")
            continue
        try:
            text = src_path.read_text(encoding="utf-8")
            doc_id = _sha256_text(text)
            size = len(text.encode("utf-8"))
            manifest.append({
                "doc_id": doc_id,
                "size": size,
                "src": src_rel,
            })
            blob_path = blobs_dir / (doc_id.replace(":", "_") + ".txt")
            _write_text(blob_path, text)
            log_lines.append(f"OK: collected {src_rel} -> {doc_id} ({size} bytes)")
        except Exception as e:
            log_lines.append(f"ERROR: collect failed src={src_rel} err={e}")
            result_lines.append(f"ERROR: collect failed src={src_rel}")

    # Stable sort by doc_id
    manifest.sort(key=lambda x: x["doc_id"])

    if manifest:
        _write_jsonl(obs_dir / "10_collect_manifest.jsonl", manifest)
        log_lines.append(f"OK: wrote manifest with {len(manifest)} docs")
        result_lines.append(f"OK: collected {len(manifest)} docs")
    else:
        log_lines.append("ERROR: no docs collected")
        result_lines.append("ERROR: no docs collected")

    _write_text(obs_dir / "10_run.log", "\n".join(log_lines) + "\n")
    _write_result(obs_dir, "10", result_lines if result_lines else
                  [f"OK: collected {len(manifest)} docs"])

    stop = 1 if not manifest else 0
    return manifest, stop


# ---------------------------------------------------------------------------
# NORMALIZE
# ---------------------------------------------------------------------------

def step_normalize(obs_dir: Path, manifest: List[dict]) -> tuple:
    """
    Canonicalize text: utf-8, LF newlines, strip trailing whitespace.
    Returns (norm_manifest, STOP).
    """
    log_lines: List[str] = []
    result_lines: List[str] = []
    norm_manifest: List[dict] = []
    norm_dir = obs_dir / "21_norm_text"

    _write_text(obs_dir / "20_header.txt",
                "NORMALIZE: utf-8 + newline canonicalization")

    blobs_dir = obs_dir / "11_collect_blobs"
    for item in manifest:
        doc_id = item["doc_id"]
        blob_file = blobs_dir / (doc_id.replace(":", "_") + ".txt")
        try:
            raw = blob_file.read_text(encoding="utf-8")
            # Normalize: CRLF -> LF, strip trailing whitespace per line
            lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
            normalized = "\n".join(line.rstrip() for line in lines)
            # Strip trailing newlines but keep one
            normalized = normalized.strip() + "\n"

            norm_path = norm_dir / (doc_id.replace(":", "_") + ".txt")
            _write_text(norm_path, normalized)

            norm_manifest.append({
                "doc_id": doc_id,
                "norm_size": len(normalized.encode("utf-8")),
                "src": item.get("src", ""),
            })
            log_lines.append(f"OK: normalized {doc_id}")
        except Exception as e:
            log_lines.append(f"ERROR: normalize failed doc_id={doc_id} err={e}")
            result_lines.append(f"ERROR: normalize failed doc_id={doc_id}")

    # Stable sort
    norm_manifest.sort(key=lambda x: x["doc_id"])

    if norm_manifest:
        _write_jsonl(obs_dir / "20_norm_manifest.jsonl", norm_manifest)
        log_lines.append(f"OK: normalized {len(norm_manifest)} docs")
        result_lines.append(f"OK: normalized {len(norm_manifest)} docs")
    else:
        log_lines.append("ERROR: no docs normalized")
        result_lines.append("ERROR: no docs normalized")

    _write_text(obs_dir / "20_run.log", "\n".join(log_lines) + "\n")
    _write_result(obs_dir, "20", result_lines if result_lines else
                  [f"OK: normalized {len(norm_manifest)} docs"])

    stop = 1 if not norm_manifest else 0
    return norm_manifest, stop


# ---------------------------------------------------------------------------
# INDEX (v0: lightweight inverted index)
# ---------------------------------------------------------------------------

def step_index(obs_dir: Path, norm_manifest: List[dict]) -> tuple:
    """
    Build deterministic inverted index from normalized texts.
    Returns (index_data, STOP).
    """
    log_lines: List[str] = []
    result_lines: List[str] = []
    norm_dir = obs_dir / "21_norm_text"

    _write_text(obs_dir / "30_header.txt",
                "INDEX: build lightweight inverted index (v0)")

    # Tokenizer: simple whitespace + lowercase
    inverted: Dict[str, List[str]] = {}
    doc_count = 0

    for item in norm_manifest:
        doc_id = item["doc_id"]
        norm_file = norm_dir / (doc_id.replace(":", "_") + ".txt")
        try:
            text = norm_file.read_text(encoding="utf-8").lower()
            # Simple tokenization: split on non-alphanumeric
            tokens = set()
            current = []
            for ch in text:
                if ch.isalnum():
                    current.append(ch)
                else:
                    if current:
                        tokens.add("".join(current))
                        current = []
            if current:
                tokens.add("".join(current))

            for token in sorted(tokens):
                if token not in inverted:
                    inverted[token] = []
                if doc_id not in inverted[token]:
                    inverted[token].append(doc_id)

            doc_count += 1
            log_lines.append(f"OK: indexed {doc_id} ({len(tokens)} tokens)")
        except Exception as e:
            log_lines.append(f"ERROR: index failed doc_id={doc_id} err={e}")
            result_lines.append(f"ERROR: index failed doc_id={doc_id}")

    # Deterministic: sort keys, sort doc_id lists
    index_data = {}
    for k in sorted(inverted.keys()):
        index_data[k] = sorted(inverted[k])

    meta = {
        "doc_count": doc_count,
        "token_count": len(index_data),
        "tokenizer": "whitespace_lowercase_v0",
        "version": "v0",
    }

    if doc_count > 0:
        _write_json(obs_dir / "30_index_meta.json", meta)
        _write_json(obs_dir / "31_index.json", index_data)
        log_lines.append(f"OK: index built ({len(index_data)} tokens, "
                         f"{doc_count} docs)")
        result_lines.append(f"OK: indexed {doc_count} docs, "
                            f"{len(index_data)} tokens")
    else:
        log_lines.append("ERROR: no docs indexed")
        result_lines.append("ERROR: no docs indexed")

    _write_text(obs_dir / "30_run.log", "\n".join(log_lines) + "\n")
    _write_result(obs_dir, "30", result_lines if result_lines else
                  [f"OK: indexed {doc_count} docs"])

    stop = 1 if doc_count == 0 else 0
    return index_data, stop


# ---------------------------------------------------------------------------
# SEARCH
# ---------------------------------------------------------------------------

def step_search(obs_dir: Path, index_data: dict,
                query_terms: List[str]) -> tuple:
    """
    Deterministic search with stable tie-break.
    Returns (search_results, STOP).
    """
    log_lines: List[str] = []
    result_lines: List[str] = []

    _write_text(obs_dir / "40_header.txt",
                "SEARCH: deterministic query with stable tie-break")

    query = {
        "terms": sorted(query_terms),
        "mode": "OR",
        "tie_break": "score_desc_docid_asc",
    }
    _write_json(obs_dir / "40_search_query.json", query)

    # Score: count of matching terms per doc
    scores: Dict[str, int] = {}
    for term in query_terms:
        term_lower = term.lower()
        doc_ids = index_data.get(term_lower, [])
        for did in doc_ids:
            scores[did] = scores.get(did, 0) + 1

    # Stable tie-break: score desc, doc_id asc
    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))

    results = []
    for rank, (doc_id, score) in enumerate(ranked):
        results.append({
            "doc_id": doc_id,
            "rank": rank,
            "score": score,
        })

    if results:
        _write_jsonl(obs_dir / "41_search_results.jsonl", results)
        log_lines.append(f"OK: search returned {len(results)} results")
        result_lines.append(f"OK: {len(results)} results for "
                            f"terms={query_terms}")
    else:
        log_lines.append(f"SKIP: no results for terms={query_terms}")
        result_lines.append(f"SKIP: no results for terms={query_terms}")

    _write_text(obs_dir / "40_run.log", "\n".join(log_lines) + "\n")
    _write_result(obs_dir, "40", result_lines if result_lines else
                  [f"OK: {len(results)} results"])

    # SEARCH with zero results is not an ERROR, just empty
    return results, 0


# ---------------------------------------------------------------------------
# CITE
# ---------------------------------------------------------------------------

def step_cite(obs_dir: Path, search_results: List[dict],
              norm_manifest: List[dict]) -> tuple:
    """
    Generate deterministic citations with fixed-length excerpts.
    Returns (citations, STOP).
    """
    log_lines: List[str] = []
    result_lines: List[str] = []
    norm_dir = obs_dir / "21_norm_text"

    _write_text(obs_dir / "50_header.txt",
                "CITE: deterministic excerpt extraction")

    # Build lookup from norm_manifest
    src_by_docid = {item["doc_id"]: item.get("src", "") for item in norm_manifest}

    citations = []
    for sr in search_results:
        doc_id = sr["doc_id"]
        norm_file = norm_dir / (doc_id.replace(":", "_") + ".txt")
        try:
            text = norm_file.read_text(encoding="utf-8")
            # Deterministic excerpt: first N chars
            excerpt = text[:EXCERPT_MAX_CHARS]
            citations.append({
                "doc_id": doc_id,
                "excerpt": excerpt,
                "offset": 0,
                "reason": f"search_rank={sr.get('rank', 0)} "
                          f"score={sr.get('score', 0)}",
                "src": src_by_docid.get(doc_id, ""),
            })
            log_lines.append(f"OK: cited {doc_id}")
        except Exception as e:
            log_lines.append(f"ERROR: cite failed doc_id={doc_id} err={e}")
            result_lines.append(f"ERROR: cite failed doc_id={doc_id}")

    if citations:
        _write_jsonl(obs_dir / "50_citations.jsonl", citations)
        # Human-readable markdown
        md_lines = ["# Citations\n\n"]
        md_lines.append(f"excerpt_max_chars={EXCERPT_MAX_CHARS}\n\n")
        for i, c in enumerate(citations, 1):
            md_lines.append(f"## {i}. {c['doc_id']}\n\n")
            md_lines.append(f"- src: {c['src']}\n")
            md_lines.append(f"- reason: {c['reason']}\n")
            md_lines.append(f"- offset: {c['offset']}\n\n")
            md_lines.append(f"```\n{c['excerpt']}\n```\n\n")
        _write_text(obs_dir / "51_citations.md", "".join(md_lines))
        log_lines.append(f"OK: generated {len(citations)} citations")
        result_lines.append(f"OK: {len(citations)} citations")
    else:
        log_lines.append("SKIP: no citations generated")
        result_lines.append("SKIP: no citations generated")

    _write_text(obs_dir / "50_run.log", "\n".join(log_lines) + "\n")
    _write_result(obs_dir, "50", result_lines if result_lines else
                  [f"OK: {len(citations)} citations"])

    return citations, 0


# ---------------------------------------------------------------------------
# MAIN: STOPLESS pipeline
# ---------------------------------------------------------------------------

def run_pipeline(obs_dir: Path, source_paths: List[str],
                 query_terms: List[str],
                 repo_root: Optional[Path] = None) -> int:
    """
    Run the full RAG pipeline: COLLECT -> NORMALIZE -> INDEX -> SEARCH -> CITE.
    Returns 0 on success, 1 on STOP.
    """
    if repo_root is None:
        repo_root = Path(".")

    obs_dir.mkdir(parents=True, exist_ok=True)
    STOP = 0

    # --- COLLECT ---
    if STOP == 0:
        print("OK: starting step=COLLECT")
        try:
            manifest, stop = step_collect(obs_dir, source_paths, repo_root)
            if stop:
                print("ERROR: step failed step=COLLECT "
                      "reason=missing_or_invalid_artifacts")
                STOP = 1
            else:
                print(f"OK: step succeeded step=COLLECT "
                      f"docs={len(manifest)}")
        except Exception as e:
            print(f"ERROR: exception captured step=COLLECT err={e}")
            STOP = 1
            manifest = []

    # --- NORMALIZE ---
    if STOP == 0:
        print("OK: starting step=NORMALIZE")
        try:
            norm_manifest, stop = step_normalize(obs_dir, manifest)
            if stop:
                print("ERROR: step failed step=NORMALIZE "
                      "reason=missing_or_invalid_artifacts")
                STOP = 1
            else:
                print(f"OK: step succeeded step=NORMALIZE "
                      f"docs={len(norm_manifest)}")
        except Exception as e:
            print(f"ERROR: exception captured step=NORMALIZE err={e}")
            STOP = 1
            norm_manifest = []
    else:
        print("SKIP: blocked by previous ERROR step=NORMALIZE")
        norm_manifest = []

    # --- INDEX ---
    if STOP == 0:
        print("OK: starting step=INDEX")
        try:
            index_data, stop = step_index(obs_dir, norm_manifest)
            if stop:
                print("ERROR: step failed step=INDEX "
                      "reason=missing_or_invalid_artifacts")
                STOP = 1
            else:
                print(f"OK: step succeeded step=INDEX "
                      f"tokens={len(index_data)}")
        except Exception as e:
            print(f"ERROR: exception captured step=INDEX err={e}")
            STOP = 1
            index_data = {}
    else:
        print("SKIP: blocked by previous ERROR step=INDEX")
        index_data = {}

    # --- SEARCH ---
    if STOP == 0:
        print("OK: starting step=SEARCH")
        try:
            search_results, stop = step_search(obs_dir, index_data,
                                               query_terms)
            if stop:
                print("ERROR: step failed step=SEARCH "
                      "reason=missing_or_invalid_artifacts")
                STOP = 1
            else:
                print(f"OK: step succeeded step=SEARCH "
                      f"results={len(search_results)}")
        except Exception as e:
            print(f"ERROR: exception captured step=SEARCH err={e}")
            STOP = 1
            search_results = []
    else:
        print("SKIP: blocked by previous ERROR step=SEARCH")
        search_results = []

    # --- CITE ---
    if STOP == 0:
        print("OK: starting step=CITE")
        try:
            citations, stop = step_cite(obs_dir, search_results,
                                        norm_manifest)
            if stop:
                print("ERROR: step failed step=CITE "
                      "reason=missing_or_invalid_artifacts")
                STOP = 1
            else:
                print(f"OK: step succeeded step=CITE "
                      f"citations={len(citations)}")
        except Exception as e:
            print(f"ERROR: exception captured step=CITE err={e}")
            STOP = 1
    else:
        print("SKIP: blocked by previous ERROR step=CITE")

    return STOP


# ---------------------------------------------------------------------------
# CLI entry (minimal, no argparse)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    # Usage: python3 scripts/rag_pipeline.py <obs_dir> [query_term1 query_term2 ...]
    # Sources are hardcoded as seed-mini for now
    obs = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        ".local/obs/s22-04_run")
    terms = sys.argv[2:] if len(sys.argv) > 2 else ["greek"]

    # Seed-mini: repo-relative paths to the fixture docs
    seed_mini = [
        "tests/fixtures/il_exec/retrieve_db.json",
    ]

    # Also collect any .md files in tests/fixtures/il_exec/ if they exist
    fixture_dir = Path("tests/fixtures/il_exec")
    if fixture_dir.exists():
        for f in sorted(fixture_dir.iterdir()):
            if f.suffix == ".md" and f.is_file():
                seed_mini.append(str(f))

    print(f"OK: obs_dir={obs}")
    print(f"OK: query_terms={terms}")
    print(f"OK: sources={seed_mini}")

    rc = run_pipeline(obs, seed_mini, terms, repo_root=Path("."))
    print(f"OK: pipeline finished STOP={rc}")
