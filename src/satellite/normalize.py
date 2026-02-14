import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to path for il_validator
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from il_validator import ILValidator, ILCanonicalizer

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

class Normalizer:
    def __init__(self, source_id: str, date_str: str, project_root: Path):
        self.source_id = source_id
        self.date_str = date_str
        self.root = project_root
        self.validator = ILValidator()
        
        # Paths
        self.raw_dir = self.root / f"data/satellite/{source_id}/raw/{date_str}"
        self.norm_dir = self.root / f"data/satellite/{source_id}/norm"
        self.norm_dir.mkdir(parents=True, exist_ok=True)
        self.output_path = self.norm_dir / f"{date_str}.jsonl"

    def process_item(self, raw_path: Path) -> Optional[Dict[str, Any]]:
        try:
            with open(raw_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            print(f"{YELLOW}WARN: Failed to load {raw_path}: {e}{RESET}", file=sys.stderr)
            return None

        feed_entry = raw.get("feed_entry", {})
        canonical_url = feed_entry.get("link", "")
        
        if not canonical_url:
            print(f"{YELLOW}WARN: No link in {raw_path.name}, skipping.{RESET}", file=sys.stderr)
            return None

        # IL Schema Fields
        uid = hashlib.sha256(f"{self.source_id}|{canonical_url}".encode("utf-8")).hexdigest()
        fetched_at = raw.get("fetched_at")
        published_at = feed_entry.get("published")
        title = feed_entry.get("title", "")
        text = feed_entry.get("summary", "")
        lang = feed_entry.get("language")

        # Hashes
        raw_bytes = raw_path.read_bytes()
        raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        
        # Inner IL Object (Only include non-None optional fields)
        il_content = {
            "uid": uid,
            "source_id": self.source_id,
            "canonical_url": canonical_url,
            "raw_ref": str(raw_path.relative_to(self.root)),
            "raw_sha256": raw_sha256
        }
        if fetched_at: il_content["fetched_at"] = fetched_at
        if published_at: il_content["published_at"] = published_at
        if title: il_content["title"] = title
        if text: il_content["text"] = text
        if lang: il_content["lang"] = lang
        
        # Wrap in Contract v1 Structure
        full_item = {
            "il": il_content,
            "meta": {
                "version": "il_contract_v1",
                "generator": "satellite-normalize"
            },
            "evidence": {
                "hashes": {
                    "raw": raw_sha256
                }
            }
        }
        
        # Validate
        is_valid, errors = self.validator.validate(full_item)
        if not is_valid:
            print(f"{RED}ERROR: IL Validation failed for {raw_path.name}: {errors}{RESET}", file=sys.stderr)
            return None

        return full_item

    def run(self) -> None:
        if not self.raw_dir.exists():
            print(f"{RED}Error: Raw dir not found: {self.raw_dir}{RESET}", file=sys.stderr)
            sys.exit(1)

        files = sorted(self.raw_dir.glob("*.json"))
        if not files:
            print(f"{YELLOW}Warning: No raw files found in {self.raw_dir}{RESET}", file=sys.stderr)
        
        print(f"Normalizing {len(files)} raw items...")
        
        il_items = []
        for p in files:
            item = self.process_item(p)
            if item:
                il_items.append(item)

        # Sort by UID (Stable Output) - UID is inside il
        il_items.sort(key=lambda x: x["il"]["uid"])
        
        # Atomic Write with Canonical JSONL
        temp_path = self.output_path.with_suffix(".tmp")
        
        with open(temp_path, "w", encoding="utf-8") as f:
            for item in il_items:
                line = ILCanonicalizer.to_jsonl_line(item)
                f.write(line)
        
        temp_path.replace(self.output_path)
        print(f"{GREEN}Saved {len(il_items)} IL items to {self.output_path}{RESET}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source_id", help="Source ID")
    parser.add_argument("--date", help="YYYY-MM-DD", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    args = parser.parse_args()
    
    root = Path(__file__).resolve().parents[2]
    
    norm = Normalizer(args.source_id, args.date, root)
    norm.run()
