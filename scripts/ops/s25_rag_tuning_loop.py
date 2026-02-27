#!/usr/bin/env python3
"""
S25-08 RAG tuning loop.

Policy:
- SOT config: TOML
- Evidence: JSON/Markdown
- RAG search DB: SQLite
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import tomllib  # py3.11+
except Exception:  # pragma: no cover
    tomllib = None

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_CONFIG = "docs/ops/S25-08_RAG_TUNING.toml"
DEFAULT_OUT_DIR = "docs/evidence/s25-08"
DEFAULT_TIMEOUT_SEC = 120

REASON_CONFIG_INVALID = "CONFIG_INVALID"
REASON_DB_BACKEND_INVALID = "DB_BACKEND_INVALID"
REASON_BUILD_INDEX_FAILED = "BUILD_INDEX_FAILED"


def extract_terms(question: str) -> List[str]:
    q = question or ""
    terms: List[str] = []
    # File-like tokens first
    for m in re.finditer(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.[A-Za-z0-9]+", q):
        base = m.group(0).split(".", 1)[0]
        if len(base) >= 2:
            terms.append(base)
    # Alnum tokens
    for m in re.finditer(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}", q):
        terms.append(m.group(0))
    # Japanese tokens
    for m in re.finditer(r"[ぁ-んァ-ンー一-龯]{2,}", q):
        terms.append(m.group(0))
    uniq: List[str] = []
    seen = set()
    for t in terms:
        k = t.strip()
        if not k:
            continue
        if k in seen:
            continue
        seen.add(k)
        uniq.append(k)
        if len(uniq) >= 5:
            break
    return uniq


def to_fts_or_query(terms: List[str]) -> str:
    safe = [t.replace('"', '""') for t in terms if t.strip()]
    return " OR ".join(f'"{t}"' for t in safe)


def _read_toml(path: Path) -> Dict[str, Any]:
    if tomllib is None:
        raise RuntimeError("tomllib unavailable")
    return tomllib.loads(path.read_text(encoding="utf-8"))


def validate_config(cfg: Dict[str, Any]) -> Tuple[bool, str]:
    if str(cfg.get("schema_version") or "") != "s25-rag-tuning-v1":
        return False, "schema_version mismatch"
    loop = cfg.get("loop")
    storage = cfg.get("storage")
    profiles = cfg.get("profiles")
    evaluation = cfg.get("evaluation")
    docs = cfg.get("docs")
    cases = cfg.get("cases")
    if not isinstance(loop, dict) or not str(loop.get("id") or "").strip():
        return False, "loop.id missing"
    if not isinstance(storage, dict):
        return False, "storage missing"
    if str(storage.get("backend") or "") != "sqlite":
        return False, "storage.backend must be sqlite"
    if not isinstance(profiles, dict):
        return False, "profiles missing"
    for key in ("baseline", "candidate"):
        p = profiles.get(key)
        if not isinstance(p, dict):
            return False, f"profiles.{key} missing"
        for field in ("chunk_size", "overlap", "top_k"):
            try:
                int(p.get(field))
            except Exception:
                return False, f"profiles.{key}.{field} invalid"
    if not isinstance(evaluation, dict):
        return False, "evaluation missing"
    try:
        float(evaluation.get("min_hit_rate_delta"))
    except Exception:
        return False, "evaluation.min_hit_rate_delta invalid"
    if not isinstance(docs, list) or not docs:
        return False, "docs missing"
    if not isinstance(cases, list) or not cases:
        return False, "cases missing"
    return True, ""


def materialize_docs(run_dir: Path, docs: List[Dict[str, Any]]) -> Path:
    raw_dir = run_dir / "raw_docs"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for item in docs:
        rel = str(item.get("path") or "").strip()
        content = str(item.get("content") or "")
        if not rel:
            continue
        path = (raw_dir / rel).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return raw_dir


def build_sqlite_index(
    repo_root: Path,
    raw_dir: Path,
    index_dir: Path,
    db_name: str,
    chunk_size: int,
    overlap: int,
    timeout_sec: int,
) -> Tuple[int, str]:
    cmd = [
        "python3",
        str((repo_root / "src" / "build_index.py").resolve()),
        "--raw-dir",
        str(raw_dir),
        "--index-dir",
        str(index_dir),
        "--db-name",
        str(db_name),
        "--chunk-size",
        str(int(chunk_size)),
        "--overlap",
        str(int(overlap)),
    ]
    cp = subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=max(1, timeout_sec),
        check=False,
    )
    out = (cp.stdout or "") + (cp.stderr or "")
    return cp.returncode, out


def retrieve_sources_sqlite(db_path: Path, query: str, top_k: int) -> List[str]:
    terms = extract_terms(query)
    if not terms:
        return []
    fts_query = to_fts_or_query(terms)

    conn = sqlite3.connect(str(db_path))
    try:
        rows = []
        if fts_query:
            rows = conn.execute(
                "SELECT path, chunk_index, bm25(chunks_fts) AS score "
                "FROM chunks_fts WHERE chunks_fts MATCH ? "
                "ORDER BY score ASC LIMIT ?",
                (fts_query, int(top_k)),
            ).fetchall()
        if not rows:
            jp_terms = [t for t in terms if any("\u3040" <= ch <= "\u9fff" for ch in t)]
            if jp_terms:
                likes = [f"%{t}%" for t in jp_terms]
                where = " OR ".join(["text LIKE ?"] * len(likes))
                rows = conn.execute(
                    "SELECT path, chunk_index, 0.0 AS score FROM chunks "
                    f"WHERE {where} ORDER BY path ASC, chunk_index ASC LIMIT ?",
                    (*likes, int(top_k)),
                ).fetchall()
    finally:
        conn.close()

    out: List[str] = []
    for path, chunk_index, _score in rows:
        out.append(f"{path}#chunk-{chunk_index}")
    return out


def evaluate_profile(
    repo_root: Path,
    run_dir: Path,
    profile_name: str,
    profile: Dict[str, Any],
    cases: List[Dict[str, Any]],
    db_name: str,
    raw_dir: Path,
    timeout_sec: int,
) -> Dict[str, Any]:
    index_dir = run_dir / "indexes" / profile_name
    index_dir.mkdir(parents=True, exist_ok=True)
    db_path = index_dir / db_name

    rc, build_out = build_sqlite_index(
        repo_root=repo_root,
        raw_dir=raw_dir,
        index_dir=index_dir,
        db_name=db_name,
        chunk_size=int(profile["chunk_size"]),
        overlap=int(profile["overlap"]),
        timeout_sec=timeout_sec,
    )
    (run_dir / f"{profile_name}_build_index.log").write_text(build_out, encoding="utf-8")

    if rc != 0:
        return {
            "status": "FAIL",
            "reason_code": REASON_BUILD_INDEX_FAILED,
            "build_rc": rc,
            "build_log": str(run_dir / f"{profile_name}_build_index.log"),
            "metrics": {},
            "cases": [],
        }

    rows: List[Dict[str, Any]] = []
    latencies: List[float] = []
    hits = 0
    total = 0
    for case in cases:
        cid = str(case.get("id") or "")
        q = str(case.get("query") or "")
        expected = str(case.get("expected_source") or "").strip()
        t0 = time.perf_counter()
        sources = retrieve_sources_sqlite(db_path=db_path, query=q, top_k=int(profile["top_k"]))
        t1 = time.perf_counter()
        latency_ms = (t1 - t0) * 1000.0
        latencies.append(latency_ms)

        matched = False
        if expected:
            total += 1
            for src in sources:
                path_part = src.split("#chunk-", 1)[0]
                if path_part.endswith(expected) or expected in path_part:
                    matched = True
                    break
            if matched:
                hits += 1

        rows.append(
            {
                "id": cid,
                "query": q,
                "expected_source": expected,
                "retrieved_sources": sources,
                "matched": matched,
                "latency_ms": round(latency_ms, 3),
            }
        )

    avg_latency = (sum(latencies) / len(latencies)) if latencies else 0.0
    hit_rate = (hits / total) if total > 0 else 0.0
    return {
        "status": "PASS",
        "reason_code": "",
        "build_rc": 0,
        "build_log": str(run_dir / f"{profile_name}_build_index.log"),
        "metrics": {
            "cases_total": len(cases),
            "cases_with_expected_source": total,
            "hit_cases": hits,
            "hit_rate": hit_rate,
            "avg_latency_ms": avg_latency,
            "chunk_size": int(profile["chunk_size"]),
            "overlap": int(profile["overlap"]),
            "top_k": int(profile["top_k"]),
            "db_path": str(db_path),
        },
        "cases": rows,
    }


def compare_profiles(
    baseline: Dict[str, Any], candidate: Dict[str, Any], min_hit_rate_delta: float
) -> Dict[str, Any]:
    b = baseline.get("metrics", {})
    c = candidate.get("metrics", {})
    b_hit = float(b.get("hit_rate", 0.0))
    c_hit = float(c.get("hit_rate", 0.0))
    b_lat = float(b.get("avg_latency_ms", 0.0))
    c_lat = float(c.get("avg_latency_ms", 0.0))
    delta_hit = c_hit - b_hit
    delta_latency_ms = c_lat - b_lat
    status = "PASS" if delta_hit >= float(min_hit_rate_delta) else "FAIL"
    return {
        "status": status,
        "delta_hit_rate": delta_hit,
        "delta_latency_ms": delta_latency_ms,
        "min_hit_rate_delta": float(min_hit_rate_delta),
    }


def build_markdown(payload: Dict[str, Any]) -> str:
    comp = payload["comparison"]
    lines: List[str] = []
    lines.append("# S25-08 RAG Tuning Loop (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload['captured_at_utc']}`")
    lines.append(f"- Branch: `{payload['git']['branch']}`")
    lines.append(f"- HeadSHA: `{payload['git']['head']}`")
    lines.append(f"- Config: `{payload['config_path']}`")
    lines.append("")
    lines.append("## Comparison")
    lines.append("")
    lines.append(f"- Status: `{comp['status']}`")
    lines.append(f"- delta_hit_rate: `{round(comp['delta_hit_rate'], 4)}`")
    lines.append(f"- delta_latency_ms: `{round(comp['delta_latency_ms'], 3)}`")
    lines.append(f"- min_hit_rate_delta: `{comp['min_hit_rate_delta']}`")
    lines.append("")
    lines.append("## Baseline Metrics")
    lines.append("")
    b = payload["profiles"]["baseline"]["metrics"]
    lines.append(f"- hit_rate: `{round(float(b.get('hit_rate', 0.0)), 4)}`")
    lines.append(f"- avg_latency_ms: `{round(float(b.get('avg_latency_ms', 0.0)), 3)}`")
    lines.append(f"- chunk_size/overlap/top_k: `{b.get('chunk_size')}/{b.get('overlap')}/{b.get('top_k')}`")
    lines.append("")
    lines.append("## Candidate Metrics")
    lines.append("")
    c = payload["profiles"]["candidate"]["metrics"]
    lines.append(f"- hit_rate: `{round(float(c.get('hit_rate', 0.0)), 4)}`")
    lines.append(f"- avg_latency_ms: `{round(float(c.get('avg_latency_ms', 0.0)), 3)}`")
    lines.append(f"- chunk_size/overlap/top_k: `{c.get('chunk_size')}/{c.get('overlap')}/{c.get('top_k')}`")
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S25-08 RAG Tuning Loop")
    lines.append(f"- status: {comp['status']}")
    lines.append(f"- baseline_hit_rate: {round(float(b.get('hit_rate', 0.0)), 4)}")
    lines.append(f"- candidate_hit_rate: {round(float(c.get('hit_rate', 0.0)), 4)}")
    lines.append(f"- delta_hit_rate: {round(comp['delta_hit_rate'], 4)}")
    lines.append(f"- delta_latency_ms: {round(comp['delta_latency_ms'], 3)}")
    lines.append(f"- artifact: docs/evidence/s25-08/{payload['artifact_names']['json']}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    parser.add_argument("--timeout-sec", type=int, default=DEFAULT_TIMEOUT_SEC)
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="rag-tuning", obs_root=args.obs_root)

    config_path = (repo_root / args.config).resolve()
    if not config_path.exists():
        emit("ERROR", f"config missing path={config_path}", events)
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"stop": 1, "reason_code": REASON_CONFIG_INVALID})
        return
    cfg = _read_toml(config_path)
    ok, why = validate_config(cfg)
    if not ok:
        emit("ERROR", f"config invalid reason={why}", events)
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"stop": 1, "reason_code": REASON_CONFIG_INVALID})
        return
    emit("OK", f"config={config_path}", events)

    storage = dict(cfg.get("storage", {}))
    if str(storage.get("backend", "")) != "sqlite":
        emit("ERROR", f"unsupported backend={storage.get('backend')}", events)
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"stop": 1, "reason_code": REASON_DB_BACKEND_INVALID})
        return

    docs = list(cfg.get("docs", []))
    cases = list(cfg.get("cases", []))
    raw_dir = materialize_docs(run_dir, docs)
    emit("OK", f"raw_docs_materialized={raw_dir}", events)
    emit("OK", f"cases_loaded={len(cases)}", events)

    profiles = dict(cfg.get("profiles", {}))
    db_name = str(storage.get("db_name", "index.sqlite3"))

    baseline = evaluate_profile(
        repo_root=repo_root,
        run_dir=run_dir,
        profile_name="baseline",
        profile=dict(profiles["baseline"]),
        cases=cases,
        db_name=db_name,
        raw_dir=raw_dir,
        timeout_sec=int(args.timeout_sec),
    )
    emit("OK", f"baseline_status={baseline['status']}", events)

    candidate = evaluate_profile(
        repo_root=repo_root,
        run_dir=run_dir,
        profile_name="candidate",
        profile=dict(profiles["candidate"]),
        cases=cases,
        db_name=db_name,
        raw_dir=raw_dir,
        timeout_sec=int(args.timeout_sec),
    )
    emit("OK", f"candidate_status={candidate['status']}", events)

    errors: List[str] = []
    if baseline["status"] != "PASS":
        errors.append("baseline profile failed")
    if candidate["status"] != "PASS":
        errors.append("candidate profile failed")

    min_delta = float(cfg.get("evaluation", {}).get("min_hit_rate_delta", 0.0))
    comp = compare_profiles(baseline, candidate, min_hit_rate_delta=min_delta)
    if comp["status"] != "PASS":
        errors.append("comparison failed: delta_hit_rate below threshold")

    for err in errors:
        emit("ERROR", err, events)

    status = "PASS" if not errors else "FAIL"
    payload: Dict[str, Any] = {
        "schema_version": "s25-rag-tuning-loop-v1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "config_path": str(config_path),
        "config_snapshot": cfg,
        "profiles": {
            "baseline": baseline,
            "candidate": candidate,
        },
        "comparison": comp,
        "summary": {
            "status": status,
            "errors": errors,
        },
        "artifact_names": {
            "json": "rag_tuning_latest.json",
            "md": "rag_tuning_latest.md",
            "run_dir": str(run_dir),
        },
        "stop": 0 if status == "PASS" else 1,
    }

    out_json = out_dir / "rag_tuning_latest.json"
    out_md = out_dir / "rag_tuning_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"rag_tuning_json={out_json}", events)
    emit("OK", f"rag_tuning_md={out_md}", events)
    emit("OK", f"obs_run_dir={run_dir}", events)
    if status == "PASS":
        emit("OK", "rag_tuning completed", events)
    else:
        emit("WARN", "rag_tuning completed with failures", events)

    events_path = write_events(run_dir, events)
    write_summary(
        run_dir,
        meta,
        events,
        extra={
            "rag_tuning_json": str(out_json),
            "rag_tuning_md": str(out_md),
            "status": status,
        },
    )
    print(f"OK: obs_events={events_path}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: unhandled exception err={exc}", flush=True)
