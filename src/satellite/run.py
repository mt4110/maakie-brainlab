import argparse
import json
from pathlib import Path

from satellite.collect import Collector
from satellite.digest import build_digest
from satellite.gate import run_gate
from satellite.index import build_index_for_source
from satellite.manifest_verify import verify_manifest
from satellite.normalize import Normalizer
from satellite.store import store_day


def run_pipeline(
    source_id: str,
    date_str: str,
    project_root: Path,
    *,
    chunk_size: int = 1200,
    overlap: int = 200,
) -> dict:
    Collector(source_id, date_str, project_root).run()

    manifest_check = verify_manifest(source_id, date_str, project_root)
    if not manifest_check.get("ok"):
        raw_errors = manifest_check.get("errors")
        errors = raw_errors if isinstance(raw_errors, list) else []
        preview = "; ".join(str(x) for x in errors[:3]) if errors else "unknown"
        error_count = int(manifest_check.get("error_count", len(errors)) or len(errors))
        raise RuntimeError(f"manifest verification failed: error_count={error_count} errors={preview}")

    Normalizer(source_id, date_str, project_root).run()
    gate = run_gate(source_id, date_str, project_root)
    store = store_day(source_id, date_str, project_root)
    digest = build_digest(source_id, date_str, project_root)
    index = build_index_for_source(source_id, date_str, project_root, chunk_size=chunk_size, overlap=overlap)

    return {
        "source_id": source_id,
        "date": date_str,
        "steps": {
            "manifest_verify": manifest_check,
            "gate": gate,
            "store": store,
            "digest": digest,
            "index": index,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run satellite pipeline end-to-end")
    parser.add_argument("source_id", help="Source ID")
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--chunk-size", type=int, default=1200)
    parser.add_argument("--overlap", type=int, default=200)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    out = run_pipeline(
        args.source_id,
        args.date,
        root,
        chunk_size=max(64, int(args.chunk_size)),
        overlap=max(0, int(args.overlap)),
    )
    print(json.dumps(out, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
