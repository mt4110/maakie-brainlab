import argparse
import hashlib
import json
import feedparser
import subprocess
import sys
import urllib.request
import urllib.error
try:

    import tomllib
except ImportError:
    import tomli as tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from satellite.manifest import generate_run_id, save_manifest, compute_config_sha

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def compute_raw_uid(source_id: str, url: str) -> str:
    """
    Compute deterministic raw_uid for an item.
    Uses source_id and URL.
    """
    payload = f"{source_id}|{url}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def detect_code_version(project_root: Path) -> str:
    """
    Return a stable code version string.
    Prefer git short SHA; fallback to fixed dev label when git context is unavailable.
    """
    default = "v1-dev"
    try:
        rev = subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "--short=12", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if rev.returncode != 0:
            return default
        head = (rev.stdout or "").strip()
        if not head:
            return default

        dirty = subprocess.run(
            ["git", "-C", str(project_root), "diff-index", "--quiet", "HEAD", "--"],
            capture_output=True,
            text=True,
            check=False,
        )
        if dirty.returncode == 0:
            return head
        if dirty.returncode == 1:
            return f"{head}-dirty"
        return default
    except Exception:
        return default

class Collector:
    def __init__(self, source_id: str, date_str: str, project_root: Path):
        self.source_id = source_id
        self.date_str = date_str
        self.root = project_root
        self.source_config_path = self.root / f"satellite/sources/{source_id}.toml"
        
        if not self.source_config_path.exists():
            raise FileNotFoundError(f"Config not found: {self.source_config_path}")
        
        with open(self.source_config_path, "rb") as f:
            self.config = tomllib.load(f)
            
        self.output_dir = self.root / f"data/satellite/{source_id}/raw/{date_str}"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.root / f"data/satellite/{source_id}/manifests/{date_str}.manifest.json"

    def fetch_feed(self, url: str) -> bytes:
        # Wrapper for easy mocking with hard timeout
        # Prevents indefinite hangs in agent runs
        timeout = self.config.get("timeout_sec", 10)
        try:
            timeout_sec = float(timeout)
        except (ValueError, TypeError):
            timeout_sec = 10.0
        if timeout_sec <= 0:
            timeout_sec = 10.0

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "satellite"},
            )
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                return resp.read()
        except Exception:
            # Re-raise to be caught by run() which expects exceptions on failure
            raise


    def run(self) -> None:
        url = self.config.get("url")
        if not url:
            print(f"{RED}Error: No URL in config{RESET}", file=sys.stderr)
            sys.exit(1)
            
        print(f"Fetching {url}...")
        raw_bytes = self.fetch_feed(url)
            
        feed = feedparser.parse(raw_bytes)
        
        if hasattr(feed, "bozo") and feed.bozo:
            print(f"{YELLOW}PARSE_WARN: Feed parsing error: {feed.bozo_exception}{RESET}", file=sys.stderr)

        artifacts = []
        
        print(f"Found {len(feed.entries)} entries.")
        
        for entry in feed.entries:
            link = getattr(entry, "link", "")
            if not link:
                continue

            raw_uid = compute_raw_uid(self.source_id, link)
            
            # Use raw_uid as filename for "preservation"
            filename = f"{raw_uid}.json"
            target_path = self.output_dir / filename
            
            # Prepare minimal raw data + meta
            raw_data = {
                "source_id": self.source_id,
                "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                # Sanitize feed_entry to minimal fields to avoid JSON serialization issues with complex objects
                "feed_entry": {
                    k: getattr(entry, k) 
                    for k in ["link", "title", "summary", "published", "updated", "id"] 
                    if hasattr(entry, k)
                }
            }
            
            # Atomic Write
            # Write to tmp, then move.
            temp_path = target_path.with_suffix(".tmp")
            try:
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(raw_data, f, ensure_ascii=False, indent=2, sort_keys=True)
                
                # Rename is atomic on POSIX
                temp_path.replace(target_path)
            except Exception as e:
                print(f"{RED}WRITE_FAILED: {target_path} - {e}{RESET}", file=sys.stderr)
                if temp_path.exists():
                    temp_path.unlink()
                continue
            
            # Calculate SHA256 for manifest
            file_sha = hashlib.sha256(target_path.read_bytes()).hexdigest()
            artifacts.append({
                "path": str(target_path.relative_to(self.root)),
                "sha256": file_sha,
                "bytes": target_path.stat().st_size
            })

        # Generate Manifest
        try:
            config_sha = compute_config_sha(self.source_id, self.root)
            
            code_version = detect_code_version(self.root)
            
            run_id = generate_run_id(self.date_str, self.source_id, config_sha, code_version)
            
            manifest_data = {
                "run_id": run_id,
                "date": self.date_str,
                "source_id": self.source_id,
                "config_sha": config_sha,
                "code_version": code_version,
                "artifacts": artifacts
            }
            
            save_manifest(self.manifest_path, manifest_data)
            print(f"{GREEN}Saved {len(artifacts)} items. Manifest: {self.manifest_path}{RESET}")
        except Exception as e:
            print(f"{RED}MANIFEST_FAILED: {e}{RESET}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source_id", help="Source ID (e.g. example_tech_blog)")
    parser.add_argument("--date", help="YYYY-MM-DD", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    args = parser.parse_args()
    
    root = Path(__file__).resolve().parents[2] # src/satellite/collect.py -> root
    
    col = Collector(args.source_id, args.date, root)
    col.run()
