import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict


def build_index_for_source(source_id: str, date_str: str, project_root: Path, chunk_size: int = 1200, overlap: int = 200) -> Dict[str, Any]:
    digest_dir = project_root / f"data/satellite/{source_id}/digest"
    digest_md = digest_dir / f"{date_str}.md"
    digest_json = digest_dir / f"{date_str}.json"
    if not digest_md.exists() or not digest_json.exists():
        raise FileNotFoundError(f"digest outputs not found for {source_id} {date_str}")

    index_dir = project_root / f"data/satellite/{source_id}/index"
    index_dir.mkdir(parents=True, exist_ok=True)
    summary_path = index_dir / f"{date_str}.json"

    cmd = [
        sys.executable,
        str((project_root / "src" / "build_index.py").resolve()),
        "--raw-dir",
        str(digest_dir),
        "--index-dir",
        str(index_dir),
        "--db-name",
        "index.sqlite3",
        "--chunk-size",
        str(int(chunk_size)),
        "--overlap",
        str(int(overlap)),
    ]
    cp = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if cp.returncode != 0:
        raise RuntimeError((cp.stderr or cp.stdout or "build_index failed").strip())

    meta_path = index_dir / "meta.json"
    meta: Dict[str, Any] = {}
    if meta_path.exists():
        try:
            obj = json.loads(meta_path.read_text(encoding="utf-8"))
            if isinstance(obj, dict):
                meta = obj
        except Exception:
            meta = {}

    payload = {
        "source_id": source_id,
        "date": date_str,
        "inputs": {
            "digest_md": str(digest_md.relative_to(project_root)),
            "digest_json": str(digest_json.relative_to(project_root)),
        },
        "index": {
            "db": str((index_dir / "index.sqlite3").relative_to(project_root)),
            "meta_json": str(meta_path.relative_to(project_root)) if meta_path.exists() else "",
            "doc_count": int(meta.get("doc_count", 0) or 0),
            "chunk_count": int(meta.get("chunk_count", 0) or 0),
            "retrieval": str(meta.get("retrieval") or ""),
        },
        "command": {
            "returncode": int(cp.returncode),
            "stdout": (cp.stdout or "").strip(),
            "stderr": (cp.stderr or "").strip(),
        },
    }

    summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build satellite digest index")
    parser.add_argument("source_id", help="Source ID")
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--chunk-size", type=int, default=1200)
    parser.add_argument("--overlap", type=int, default=200)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    summary = build_index_for_source(
        args.source_id,
        args.date,
        root,
        chunk_size=max(64, int(args.chunk_size)),
        overlap=max(0, int(args.overlap)),
    )
    print(json.dumps(summary.get("index", {}), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
