import datetime
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

class OBSWriter:
    """
    OBS Format v1 Utility.
    Handles line-based logging (OK/ERROR/SKIP) and observation directory management.
    Never uses sys.exit().
    """

    def __init__(self, name: str, repo_root: Path = Path(".")):
        self.name = name
        self.repo_root = repo_root
        # UTC naming: .local/obs/<name>_<YYYYMMDDTHHMMSSZ>
        now = datetime.datetime.now(datetime.timezone.utc)
        ts = now.strftime("%Y%m%dT%H%M%SZ")
        self.obs_dir = self.repo_root / ".local" / "obs" / f"{name}_{ts}"
        self.stop = 0

    def create_dir(self) -> bool:
        """Creates the obs_dir safely."""
        try:
            self.obs_dir.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            # Fallback log if dir creation fails
            self.log("ERROR", phase="boot", reason=f"mkdir_failed: {e}", STOP=1)
            self.stop = 1
            return False

    def log(self, level: str, **kwargs: Any):
        """
        Prints a standardized line log.
        Format: LEVEL: phase=... KEY=VALUE ...
        """
        if "STOP" in kwargs and kwargs["STOP"] == 1:
            self.stop = 1
        
        kv_pairs = []
        for k, v in kwargs.items():
            # If value has spaces, wrap in quotes
            val_str = str(v)
            if " " in val_str:
                val_str = f'"{val_str}"'
            kv_pairs.append(f"{k}={val_str}")
        
        line = f"{level}: {' '.join(kv_pairs)}"
        print(line, flush=True)

    def write_json(self, filename: str, data: Dict[str, Any]):
        """Writes data to obs_dir as JSON safely."""
        if not self.obs_dir.exists():
            return
        
        path = self.obs_dir / filename
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log("ERROR", phase="write_file", path=filename, reason=str(e))

def get_utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
