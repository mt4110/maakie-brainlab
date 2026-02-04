#!/usr/bin/env python3
import argparse
import os
import re
import sqlite3
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]

def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")

def build_unknown() -> str:
    return "\n".join([
        "結論:",
        "- 不明（参照できる根拠が見つかりませんでした）",
        "",
        "根拠:",
        "- 不明（CONTEXTが空）",
        "",
        "参照:",
        "- 不明（参照なし）",
        "",
        "不確実性:",
        "- 質問に答えるための資料が data/raw/ に存在しない可能性があります",
    ])

def extract_terms(question: str) -> list[str]:
    # 1) hello.md のような “ファイルっぽい” token を優先
    files = re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*\.[A-Za-z0-9]+", question)
    terms: list[str] = []
    for f in files:
        base = f.split(".", 1)[0]
        if len(base) >= 2:
            terms.append(base)

    # 2) 英数字ワード（長め優先）
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{1,}", question)
    for w in words:
        if w.lower() in {"http", "https"}:
            continue
        if len(w) >= 3:
            terms.append(w)

    # 重複除去（順序保持）
    seen = set()
    out = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:5]  # 取りすぎると逆に外す

def to_fts_or_query(terms: list[str]) -> str:
    # FTS5 の構文エラー回避：各termを "..." で囲い OR 連結
    # ダブルクォートは二重化でエスケープ
    safe = [t.replace('"', '""') for t in terms if t.strip()]
    return " OR ".join(f'"{t}"' for t in safe)

def chat_openai_compat(base_url: str, model: str, messages, temperature: float = 0.2) -> str:
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {"model": model, "messages": messages, "temperature": temperature}
    headers = {"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY', 'dummy')}"}
    r = requests.post(url, json=payload, headers=headers, timeout=180)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--index-dir", default="index")
    ap.add_argument("--db-name", default="index.sqlite3")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--temperature", type=float, default=0.2)
    args = ap.parse_args()

    db_path = ROOT / args.index_dir / args.db_name
    if not db_path.exists():
        raise SystemExit(f"[ask] index db not found: {db_path}. run build_index first.")

    system_prompt = load_text(ROOT / "prompts" / "system.md")
    rag_format = load_text(ROOT / "prompts" / "rag.md")

    terms = extract_terms(args.question)
    q = to_fts_or_query(terms)

    conn = sqlite3.connect(str(db_path))
    try:
        rows = []
        if q:
            rows = conn.execute(
                "SELECT path, chunk_index, text, bm25(chunks_fts) AS score "
                "FROM chunks_fts WHERE chunks_fts MATCH ? "
                "ORDER BY score ASC LIMIT ?",
                (q, args.top_k),
            ).fetchall()

        # フォールバック：FTSで拾えなければ先頭チャンクを返す（小規模スタートの安全弁）
        if not rows:
            rows = conn.execute(
                "SELECT path, chunk_index, text, 0.0 AS score "
                "FROM chunks ORDER BY path ASC, chunk_index ASC LIMIT ?",
                (args.top_k,),
            ).fetchall()
    finally:
        conn.close()

    if not rows:
        print(build_unknown())
        return

    sources = []
    context_parts = []
    for path, chunk_index, text, score in rows:
        src = f"{path}#chunk-{chunk_index}"
        sources.append(src)
        context_parts.append(f"[{src} score={score:.3f}]\n{text}\n")

    context = "\n---\n".join(context_parts)

    user_prompt = (
        "CONTEXT:\n"
        f"{context}\n\n"
        "INSTRUCTION:\n"
        "- CONTEXT に基づいて回答してください。CONTEXT外は推測禁止。\n"
        "- 出力フォーマットは必ず以下に従ってください。\n\n"
        f"{rag_format}\n\n"
        f"QUESTION:\n{args.question}\n"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    base_url = os.getenv("OPENAI_API_BASE", "http://127.0.0.1:8080/v1")
    model = os.getenv("LOCAL_GGUF_MODEL", "Qwen2.5-7B-Instruct-Q4_K_M.gguf")

    out = chat_openai_compat(base_url, model, messages, temperature=args.temperature)

    if ("参照:" not in out) and ("sources" not in out.lower()):
        out = out.rstrip() + "\n\n参照:\n" + "\n".join(f"- {s}" for s in sources) + "\n"

    print(out)

if __name__ == "__main__":
    main()
