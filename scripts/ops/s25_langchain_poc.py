#!/usr/bin/env python3
"""
S25-09 LangChain PoC runner.

Goal:
- Connect retrieval output to a minimal LangChain Core flow.
- Keep a deterministic rollback path without LangChain.
- Emit JSON/Markdown evidence for PR body.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Tuple

try:
    import tomllib  # py3.11+
except Exception:  # pragma: no cover
    tomllib = None

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_CONFIG = "docs/ops/S25-09_LANGCHAIN_POC.toml"
DEFAULT_OUT_DIR = "docs/evidence/s25-09"
DEFAULT_TIMEOUT_SEC = 120

MODE_ALL = "all"
MODE_POC_ONLY = "poc-only"
MODE_ROLLBACK_ONLY = "rollback-only"

REASON_CONFIG_INVALID = "CONFIG_INVALID"
REASON_BUILD_INDEX_FAILED = "BUILD_INDEX_FAILED"
REASON_NO_RETRIEVAL = "NO_RETRIEVAL"
REASON_LANGCHAIN_UNAVAILABLE = "LANGCHAIN_UNAVAILABLE"
REASON_LANGCHAIN_FAILED = "LANGCHAIN_FAILED"
REASON_ROLLBACK_FAILED = "ROLLBACK_FAILED"


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def to_repo_rel(repo_root: Path, value: str | Path) -> str:
    p = Path(value).resolve()
    root = repo_root.resolve()
    try:
        rel = p.relative_to(root)
    except ValueError:
        return ""
    rel_posix = rel.as_posix()
    if ".." in Path(rel_posix).parts:
        return ""
    return rel_posix


def is_safe_rel_path(value: str) -> bool:
    p = Path(value.strip())
    if p.is_absolute():
        return False
    return ".." not in p.parts


def normalize_rel_path(value: str) -> str:
    return PurePosixPath((value or "").replace("\\", "/")).as_posix().lstrip("./")


def source_matches_expected(expected_source: str, source_path: str) -> bool:
    expected = normalize_rel_path(expected_source)
    if not expected:
        return False
    got = normalize_rel_path(source_path)
    return got == expected or got.endswith(f"/{expected}")


def normalize_source_ref_for_payload(repo_root: Path, source_ref: str) -> str:
    source = str(source_ref or "")
    path_part, sep, tail = source.partition("#chunk-")
    rel = to_repo_rel(repo_root, path_part) if path_part else ""
    path_out = rel or normalize_rel_path(path_part)
    if not sep:
        return path_out
    return f"{path_out}#chunk-{tail}"


def normalize_rows_for_payload(repo_root: Path, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows:
        path = str(row.get("path") or "")
        source = str(row.get("source") or "")
        rel_path = to_repo_rel(repo_root, path) if path else ""
        rel_source = normalize_source_ref_for_payload(repo_root, source)
        out.append(
            {
                **row,
                "path": rel_path or normalize_rel_path(path),
                "source": rel_source,
            }
        )
    return out


def extract_terms(question: str) -> List[str]:
    q = question or ""
    terms: List[str] = []
    for m in re.finditer(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.[A-Za-z0-9]+", q):
        base = m.group(0).split(".", 1)[0]
        if len(base) >= 2:
            terms.append(base)
    for m in re.finditer(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}", q):
        terms.append(m.group(0))
    for m in re.finditer(r"[ぁ-んァ-ンー一-龯]{2,}", q):
        terms.append(m.group(0))

    uniq: List[str] = []
    seen = set()
    for term in terms:
        key = term.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        uniq.append(key)
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
    if str(cfg.get("schema_version") or "") != "s25-langchain-poc-v1":
        return False, "schema_version mismatch"

    poc = cfg.get("poc")
    index = cfg.get("index")
    smoke = cfg.get("smoke")
    docs = cfg.get("docs")

    if not isinstance(poc, dict) or not str(poc.get("id") or "").strip():
        return False, "poc.id missing"
    try:
        top_k = int(poc.get("top_k", 3))
        if top_k <= 0:
            return False, "poc.top_k must be > 0"
    except Exception:
        return False, "poc.top_k invalid"

    if not isinstance(index, dict):
        return False, "index missing"
    if not str(index.get("db_name") or "").strip():
        return False, "index.db_name missing"
    for key in ("chunk_size", "overlap"):
        try:
            int(index.get(key))
        except Exception:
            return False, f"index.{key} invalid"

    if not isinstance(smoke, dict):
        return False, "smoke missing"
    if not str(smoke.get("question") or "").strip():
        return False, "smoke.question missing"

    if not isinstance(docs, list) or not docs:
        return False, "docs missing"
    for idx, item in enumerate(docs, start=1):
        if not isinstance(item, dict):
            return False, f"docs[{idx}] invalid"
        rel = str(item.get("path") or "").strip()
        if not rel:
            return False, f"docs[{idx}].path missing"
        if not is_safe_rel_path(rel):
            return False, f"docs[{idx}].path unsafe"

    return True, ""


def materialize_docs(run_dir: Path, docs: List[Dict[str, Any]]) -> Path:
    raw_dir = run_dir / "raw_docs"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_root = raw_dir.resolve()
    for item in docs:
        rel = str(item.get("path") or "").strip()
        content = str(item.get("content") or "")
        if not rel:
            continue
        if not is_safe_rel_path(rel):
            raise ValueError(f"unsafe docs.path: {rel}")
        path = (raw_dir / rel).resolve()
        if path != raw_root and raw_root not in path.parents:
            raise ValueError(f"docs.path escapes raw_dir: {rel}")
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
        sys.executable,
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
    try:
        cp = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=max(1, timeout_sec),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        out = _to_text(exc.stdout) + _to_text(exc.stderr)
        return 124, out + f"\nERROR: timeout after {max(1, timeout_sec)}s\n"
    out = (cp.stdout or "") + (cp.stderr or "")
    return cp.returncode, out


def retrieve_rows_sqlite(db_path: Path, question: str, top_k: int) -> List[Dict[str, Any]]:
    terms = extract_terms(question)
    if not terms:
        return []

    fts_query = to_fts_or_query(terms)
    conn = sqlite3.connect(str(db_path))
    rows: List[Tuple[Any, ...]] = []
    try:
        if fts_query:
            rows = conn.execute(
                "SELECT path, chunk_index, text, bm25(chunks_fts) AS score "
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
                    "SELECT path, chunk_index, text, 0.0 AS score FROM chunks "
                    f"WHERE {where} ORDER BY path ASC, chunk_index ASC LIMIT ?",
                    (*likes, int(top_k)),
                ).fetchall()
    finally:
        conn.close()

    out: List[Dict[str, Any]] = []
    for path, chunk_index, text, score in rows:
        out.append(
            {
                "source": f"{path}#chunk-{chunk_index}",
                "path": str(path),
                "chunk_index": int(chunk_index),
                "text": str(text),
                "score": float(score),
            }
        )
    return out


def source_matches(rows: List[Dict[str, Any]], expected_source: str) -> bool:
    target = (expected_source or "").strip()
    if not target:
        return True
    for row in rows:
        path = str(row.get("path") or "")
        if source_matches_expected(target, path):
            return True
    return False


def _first_non_empty_line(text: str) -> str:
    for line in str(text or "").splitlines():
        item = line.strip()
        if item:
            return item
    return ""


def build_structured_answer(mode: str, rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "\n".join(
            [
                "結論:",
                "- 不明（参照できる根拠が見つかりませんでした）",
                "",
                "根拠:",
                "- CONTEXT が空です",
                "",
                "参照:",
                "- 不明（参照なし）",
                "",
                "不確実性:",
                "- 資料不足のため回答信頼度は低いです",
            ]
        )

    head = _first_non_empty_line(rows[0].get("text", ""))
    if len(head) > 120:
        head = head[:120] + "..."
    sources = [str(row.get("source") or "") for row in rows if str(row.get("source") or "").strip()]

    lines: List[str] = []
    lines.append("結論:")
    lines.append(f"- [{mode}] {head or 'retrieved context found'}")
    lines.append("")
    lines.append("根拠:")
    lines.append(f"- retrieved_chunks={len(rows)}")
    lines.append("- 上位チャンクの先頭行を結論候補として採用")
    lines.append("")
    lines.append("参照:")
    for src in sources:
        lines.append(f"- {src}")
    lines.append("")
    lines.append("不確実性:")
    lines.append("- 回答は取得チャンク内の情報のみに制限")
    return "\n".join(lines)


def run_langchain_poc(question: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    try:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.runnables import RunnableLambda
    except Exception as exc:
        return {
            "status": "SKIP",
            "reason_code": REASON_LANGCHAIN_UNAVAILABLE,
            "backend": "none",
            "error": str(exc),
            "answer": build_structured_answer("langchain-skip", rows),
        }

    try:
        context = "\n\n---\n\n".join(
            f"[{row['source']} score={row['score']:.3f}]\n{row['text']}" for row in rows
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "You are a deterministic RAG formatter. Use only provided context."),
                (
                    "human",
                    "CONTEXT:\n{context}\n\nQUESTION:\n{question}\n\n"
                    "SOURCES:\n{sources}\n"
                    "Return concise Japanese answer with citation blocks.",
                ),
            ]
        )

        def synthesize(prompt_value: Any) -> str:
            _ = prompt_value
            return build_structured_answer("langchain-core", rows)

        chain = prompt | RunnableLambda(synthesize)
        answer = str(
            chain.invoke(
                {
                    "context": context,
                    "question": question,
                    "sources": "\n".join(str(r.get("source") or "") for r in rows),
                }
            )
        )
        return {
            "status": "PASS",
            "reason_code": "",
            "backend": "langchain-core",
            "error": "",
            "answer": answer,
        }
    except Exception as exc:
        return {
            "status": "FAIL",
            "reason_code": REASON_LANGCHAIN_FAILED,
            "backend": "langchain-core",
            "error": str(exc),
            "answer": "",
        }


def run_rollback(question: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    _ = question
    try:
        return {
            "status": "PASS",
            "reason_code": "",
            "backend": "rollback-native",
            "error": "",
            "answer": build_structured_answer("rollback", rows),
        }
    except Exception as exc:
        return {
            "status": "FAIL",
            "reason_code": REASON_ROLLBACK_FAILED,
            "backend": "rollback-native",
            "error": str(exc),
            "answer": "",
        }


def evaluate_smoke(flow: Dict[str, Any], rows: List[Dict[str, Any]], expected_source: str) -> Dict[str, Any]:
    matched = source_matches(rows, expected_source)
    state = str(flow.get("status") or "FAIL")
    status = state
    if state == "PASS" and not matched:
        status = "FAIL"
    return {
        "status": status,
        "backend": flow.get("backend", ""),
        "reason_code": flow.get("reason_code", ""),
        "matched_expected_source": matched,
        "expected_source": expected_source,
        "answer": flow.get("answer", ""),
        "error": flow.get("error", ""),
    }


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    poc = payload.get("smoke", {}).get("poc", {})
    rollback = payload.get("smoke", {}).get("rollback", {})

    lines: List[str] = []
    lines.append("# S25-09 LangChain PoC (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload.get('captured_at_utc', '')}`")
    lines.append(f"- Branch: `{payload.get('git', {}).get('branch', '')}`")
    lines.append(f"- HeadSHA: `{payload.get('git', {}).get('head', '')}`")
    lines.append(f"- Config: `{payload.get('config_path', '')}`")
    lines.append("")
    lines.append("## Smoke Results")
    lines.append("")
    lines.append(f"- overall_status: `{summary.get('status', '')}`")
    lines.append(f"- poc_smoke: `{poc.get('status', 'SKIP')}` ({poc.get('backend', '')})")
    lines.append(f"- rollback_smoke: `{rollback.get('status', 'SKIP')}` ({rollback.get('backend', '')})")
    lines.append(f"- retrieval_rows: `{payload.get('retrieval', {}).get('rows', 0)}`")
    lines.append("")
    lines.append("## Rollback")
    lines.append("")
    lines.append(f"- command: `{payload.get('rollback', {}).get('command', '')}`")
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S25-09 LangChain PoC")
    lines.append(f"- status: {summary.get('status', '')}")
    lines.append(f"- poc_smoke: {poc.get('status', 'SKIP')} ({poc.get('backend', '')})")
    lines.append(f"- rollback_smoke: {rollback.get('status', 'SKIP')} ({rollback.get('backend', '')})")
    lines.append(f"- retrieval_rows: {payload.get('retrieval', {}).get('rows', 0)}")
    lines.append(f"- rollback: {payload.get('rollback', {}).get('command', '')}")
    lines.append(f"- artifact: docs/evidence/s25-09/{payload.get('artifact_names', {}).get('json', '')}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    parser.add_argument("--timeout-sec", type=int, default=DEFAULT_TIMEOUT_SEC)
    parser.add_argument(
        "--mode",
        choices=[MODE_ALL, MODE_POC_ONLY, MODE_ROLLBACK_ONLY],
        default=MODE_ALL,
    )
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="langchain-poc", obs_root=args.obs_root)

    config_path = (repo_root / args.config).resolve()
    if not config_path.exists():
        emit("ERROR", f"config missing path={config_path}", events)
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"stop": 1, "reason_code": REASON_CONFIG_INVALID})
        return 1

    cfg = _read_toml(config_path)
    ok, why = validate_config(cfg)
    if not ok:
        emit("ERROR", f"config invalid reason={why}", events)
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"stop": 1, "reason_code": REASON_CONFIG_INVALID})
        return 1
    emit("OK", f"config={config_path}", events)

    docs = list(cfg.get("docs", []))
    poc_cfg = dict(cfg.get("poc", {}))
    index_cfg = dict(cfg.get("index", {}))
    smoke_cfg = dict(cfg.get("smoke", {}))

    try:
        raw_dir = materialize_docs(run_dir, docs)
    except Exception as exc:
        emit("ERROR", f"materialize_docs failed err={exc}", events)
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"stop": 1, "reason_code": REASON_CONFIG_INVALID})
        return 1
    emit("OK", f"raw_docs_materialized={raw_dir}", events)

    index_dir = run_dir / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    db_name = str(index_cfg.get("db_name", "index.sqlite3"))
    db_path = index_dir / db_name

    rc, build_out = build_sqlite_index(
        repo_root=repo_root,
        raw_dir=raw_dir,
        index_dir=index_dir,
        db_name=db_name,
        chunk_size=int(index_cfg.get("chunk_size", 800)),
        overlap=int(index_cfg.get("overlap", 100)),
        timeout_sec=int(args.timeout_sec),
    )
    (run_dir / "build_index.log").write_text(build_out, encoding="utf-8")
    if rc != 0:
        emit("ERROR", "build_index failed", events)
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"stop": 1, "reason_code": REASON_BUILD_INDEX_FAILED})
        return 1
    emit("OK", f"db_path={db_path}", events)

    question = str(smoke_cfg.get("question") or "")
    expected_source = str(smoke_cfg.get("expected_source") or "").strip()
    top_k = int(poc_cfg.get("top_k", 3))

    rows = retrieve_rows_sqlite(db_path=db_path, question=question, top_k=top_k)
    rows = normalize_rows_for_payload(repo_root, rows)
    emit("OK", f"retrieval_rows={len(rows)}", events)

    errors: List[str] = []
    warnings: List[str] = []
    reason_code = ""
    if not rows:
        reason_code = REASON_NO_RETRIEVAL
        errors.append("retrieval empty")

    poc_eval: Dict[str, Any] = {"status": "SKIP", "backend": "skipped", "reason_code": "", "answer": "", "error": "", "matched_expected_source": False}
    rollback_eval: Dict[str, Any] = {"status": "SKIP", "backend": "skipped", "reason_code": "", "answer": "", "error": "", "matched_expected_source": False}

    if args.mode in (MODE_ALL, MODE_POC_ONLY):
        poc_flow = run_langchain_poc(question=question, rows=rows)
        poc_eval = evaluate_smoke(poc_flow, rows=rows, expected_source=expected_source)
        emit("OK" if poc_eval["status"] == "PASS" else "WARN", f"poc_smoke={poc_eval['status']} backend={poc_eval['backend']}", events)
        if poc_eval["status"] == "FAIL":
            reason_code = reason_code or str(poc_eval.get("reason_code") or REASON_LANGCHAIN_FAILED)
            errors.append("poc smoke failed")
        elif poc_eval["status"] == "SKIP":
            warnings.append("poc smoke skipped (langchain unavailable)")

    if args.mode in (MODE_ALL, MODE_ROLLBACK_ONLY):
        rollback_flow = run_rollback(question=question, rows=rows)
        rollback_eval = evaluate_smoke(rollback_flow, rows=rows, expected_source=expected_source)
        emit(
            "OK" if rollback_eval["status"] == "PASS" else "WARN",
            f"rollback_smoke={rollback_eval['status']} backend={rollback_eval['backend']}",
            events,
        )
        if rollback_eval["status"] != "PASS":
            reason_code = reason_code or str(rollback_eval.get("reason_code") or REASON_ROLLBACK_FAILED)
            errors.append("rollback smoke failed")

    for err in errors:
        emit("ERROR", err, events)
    for warn in warnings:
        emit("WARN", warn, events)

    status = "PASS" if not errors else "FAIL"
    rollback_command = "python3 scripts/ops/s25_langchain_poc.py --mode rollback-only"
    payload: Dict[str, Any] = {
        "schema_version": "s25-langchain-poc-loop-v1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "config_path": to_repo_rel(repo_root, config_path),
        "config_snapshot": cfg,
        "mode": args.mode,
        "retrieval": {
            "rows": len(rows),
            "db_path": to_repo_rel(repo_root, db_path),
            "question": question,
            "expected_source": expected_source,
            "top_k": top_k,
            "sources": [str(r.get("source") or "") for r in rows],
        },
        "smoke": {
            "poc": poc_eval,
            "rollback": rollback_eval,
        },
        "rollback": {
            "command": rollback_command,
            "doc": "docs/ops/S25-09_LANGCHAIN_POC.md",
        },
        "summary": {
            "status": status,
            "reason_code": reason_code,
            "errors": errors,
            "warnings": warnings,
        },
        "artifact_names": {
            "json": "langchain_poc_latest.json",
            "md": "langchain_poc_latest.md",
            "run_dir": to_repo_rel(repo_root, run_dir),
        },
        "stop": 0 if status == "PASS" else 1,
    }

    out_json = out_dir / "langchain_poc_latest.json"
    out_md = out_dir / "langchain_poc_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"langchain_poc_json={out_json}", events)
    emit("OK", f"langchain_poc_md={out_md}", events)
    emit("OK", f"obs_run_dir={run_dir}", events)
    if status == "PASS":
        emit("OK", "langchain_poc completed", events)
    else:
        emit("WARN", "langchain_poc completed with failures", events)

    events_path = write_events(run_dir, events)
    write_summary(
        run_dir,
        meta,
        events,
        extra={
            "langchain_poc_json": to_repo_rel(repo_root, out_json),
            "langchain_poc_md": to_repo_rel(repo_root, out_md),
            "status": status,
        },
    )
    print(f"OK: obs_events={events_path}", flush=True)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: unhandled exception err={exc}", flush=True)
        raise SystemExit(1)
