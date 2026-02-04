#!/usr/bin/env python3
import argparse
import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    path: str
    chunk_index: int
    start: int
    end: int
    text: str
    sha256: str

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def read_text_file(path: Path) -> str:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")
    return text.replace("\r\n", "\n").replace("\r", "\n")

def chunk_text(text: str, chunk_size: int, overlap: int) -> List[Tuple[int, int, str]]:
    paras = [p for p in text.split("\n\n") if p.strip() != ""]
    chunks: List[Tuple[int, int, str]] = []
    cursor = 0
    buf = ""
    buf_start = 0

    def flush_buf(end_pos: int) -> None:
        nonlocal buf, buf_start
        t = buf.strip()
        if t:
            chunks.append((buf_start, end_pos, t))
        buf = ""

    for p in paras:
        pos = text.find(p, cursor)
        if pos == -1:
            pos = cursor
        cursor = pos + len(p)

        if not buf:
            buf_start = pos

        candidate = (buf + ("\n\n" if buf else "") + p)
        if len(candidate) <= chunk_size:
            buf = candidate
            continue

        if not buf:
            # 段落が長すぎる → 固定幅
            start = pos
            s = p
            i = 0
            step = (chunk_size - overlap) if chunk_size > overlap else chunk_size
            while i < len(s):
                part = s[i:i + chunk_size]
                part_start = start + i
                part_end = part_start + len(part)
                chunks.append((part_start, part_end, part.strip()))
                i += step
            buf = ""
            continue

        flush_buf(pos)

        if overlap > 0 and chunks:
            prev = chunks[-1][2]
            carry = prev[-overlap:] if len(prev) > overlap else prev
            buf = carry + "\n\n" + p
            buf_start = max(0, pos - len(carry))
        else:
            buf = p
            buf_start = pos

    if buf:
        flush_buf(min(len(text), buf_start + len(buf)))

    return [(s, e, t) for (s, e, t) in chunks if t.strip()]

def iter_documents(raw_dir: Path) -> Iterable[Path]:
    for p in sorted(raw_dir.rglob("*")):
        if p.is_file() and p.suffix.lower() in {".md", ".txt"}:
            yield p

def open_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS chunks (
      chunk_id    TEXT PRIMARY KEY,
      path        TEXT NOT NULL,
      chunk_index INTEGER NOT NULL,
      start       INTEGER NOT NULL,
      end         INTEGER NOT NULL,
      text        TEXT NOT NULL,
      text_sha256 TEXT NOT NULL
    );
    """)

    # FTS5（全文検索）
    conn.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
    USING fts5(chunk_id UNINDEXED, path UNINDEXED, chunk_index UNINDEXED, text);
    """)
    return conn

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--index-dir", default="index")
    ap.add_argument("--db-name", default="index.sqlite3")
    ap.add_argument("--chunk-size", type=int, default=1200)
    ap.add_argument("--overlap", type=int, default=200)
    args = ap.parse_args()

    raw_dir = Path(args.raw_dir)
    index_dir = Path(args.index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)
    db_path = index_dir / args.db_name
    meta_path = index_dir / "meta.json"

    # 小規模スタートの最強安定: 毎回フル再構築
    if db_path.exists():
        db_path.unlink()

    conn = open_db(db_path)

    docs = list(iter_documents(raw_dir))
    all_chunks: List[Chunk] = []

    for doc_path in docs:
        text = read_text_file(doc_path)
        parts = chunk_text(text, args.chunk_size, args.overlap)
        for i, (s, e, t) in enumerate(parts):
            cid = f"{doc_path.as_posix()}#chunk-{i}"
            all_chunks.append(Chunk(
                chunk_id=cid,
                path=doc_path.as_posix(),
                chunk_index=i,
                start=s,
                end=e,
                text=t,
                sha256=sha256_text(t),
            ))

    for c in all_chunks:
        conn.execute(
            "INSERT INTO chunks(chunk_id,path,chunk_index,start,end,text,text_sha256) VALUES (?,?,?,?,?,?,?)",
            (c.chunk_id, c.path, c.chunk_index, c.start, c.end, c.text, c.sha256),
        )
        conn.execute(
            "INSERT INTO chunks_fts(chunk_id,path,chunk_index,text) VALUES (?,?,?,?)",
            (c.chunk_id, c.path, c.chunk_index, c.text),
        )

    conn.commit()
    conn.close()

    meta = {
        "raw_dir": str(raw_dir),
        "db": str(db_path),
        "chunk_size": args.chunk_size,
        "overlap": args.overlap,
        "doc_count": len(docs),
        "chunk_count": len(all_chunks),
        "retrieval": "sqlite_fts5",
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[build_index] OK docs={len(docs)} chunks={len(all_chunks)} db={db_path}")

if __name__ == "__main__":
    main()
