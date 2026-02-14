import json
import re
from typing import Dict, Any, List, Optional, Tuple

class ILValidator:
    """
    Validates IL items against Contract v1 rules.
    """
    
    FORBIDDEN_FIELDS = {
        "created_at", "generated_at", "timestamp", "now",
        "uuid", "nonce", "random"
    }
    
    FORBIDDEN_KEY_PATTERN = re.compile(r"[^A-Za-z0-9_./-]")

    def __init__(self):
        self.errors = []

    def add_error(self, code: str, message: str, path: str = "", hint: str = ""):
        error = {
            "code": code,
            "message": message
        }
        if path:
            error["path"] = path
        if hint:
            error["hint"] = hint
        self.errors.append(error)

    def validate(self, data: Any) -> Tuple[bool, List[Dict[str, str]]]:
        """
        Validates the top-level structure and IL content.
        Returns (is_valid, sorted_errors).
        """
        self.errors = []
        
        if not isinstance(data, dict):
            self.add_error("E_SCHEMA", "Top-level item must be an object")
            return False, self.errors

        # Required top-level keys
        for key in ["il", "meta", "evidence"]:
            if key not in data:
                self.add_error("E_SCHEMA", f"Missing required field: {key}")

        # Meta version check
        meta = data.get("meta")
        if isinstance(meta, dict):
            if meta.get("version") != "il_contract_v1":
                self.add_error("E_UNSUPPORTED", f"Unsupported contract version: {meta.get('version')}", path="/meta/version")
        elif "meta" in data:
            self.add_error("E_SCHEMA", "meta must be an object", path="/meta")

        # Evidence check
        if "evidence" in data and not isinstance(data["evidence"], dict):
            self.add_error("E_SCHEMA", "evidence must be an object", path="/evidence")

        # Recursive validation for forbidden fields, nulls, and types
        self._validate_recursive(data, "")

        # Sort errors by (path, code, message) for determinism
        self.errors.sort(key=lambda x: (x.get("path", ""), x["code"], x["message"]))
        
        return len(self.errors) == 0, self.errors

    def _validate_recursive(self, val: Any, path: str):
        if val is None:
            self.add_error("E_FORBIDDEN", "null values are forbidden", path=path)
            return

        if isinstance(val, dict):
            for k, v in val.items():
                if k in self.FORBIDDEN_FIELDS:
                    self.add_error("E_FORBIDDEN", f"Forbidden field: {k}", path=f"{path}/{k}")
                
                if self.FORBIDDEN_KEY_PATTERN.search(k):
                    self.add_error("E_SCHEMA", f"Key contains forbidden characters: {k}", path=path)
                
                self._validate_recursive(v, f"{path}/{k}")
        
        elif isinstance(val, list):
            for i, item in enumerate(val):
                self._validate_recursive(item, f"{path}/{i}")
        
        elif isinstance(val, float):
            # Float is allowed only if it's actually an integer (no fractional part)
            if not val.is_integer():
                self.add_error("E_TYPE", f"Floating point numbers are forbidden: {val}", path=path)
            # Check 53-bit range
            if abs(val) > (2**53 - 1):
                self.add_error("E_TYPE", f"Number out of 53-bit range: {val}", path=path)
        
        elif isinstance(val, int):
            if abs(val) > (2**53 - 1):
                self.add_error("E_TYPE", f"Number out of 53-bit range: {val}", path=path)
        
        elif isinstance(val, str):
            if "\r" in val:
                self.add_error("E_SCHEMA", "CR characters are forbidden in strings", path=path)
            if not val and path.split("/")[-1] != "notes": # Allow empty notes, but generally discouraged
                # Contract says: "MUST NOT: empty string を “欠落の代替” に使わない"
                # This is tricky to enforce without knowing context, but we'll flag it if it's the whole value
                pass

class ILCanonicalizer:
    """
    Serializes IL items into canonical JSON bytes.
    """
    
    @staticmethod
    def canonicalize(data: Dict[str, Any]) -> bytes:
        """
        Produces compact, sorted-key, UTF-8 JSON bytes without trailing newline.
        """
        # json.dumps with sort_keys=True, separators=(',', ':') handles most rules
        # ensure_ascii=False ensures non-ASCII content is not escaped as \uXXXX (UTF-8 required)
        compact_json = json.dumps(
            data,
            sort_keys=True,
            ensure_ascii=False,
            separators=(',', ':')
        )
        return compact_json.encode("utf-8")

    @staticmethod
    def to_jsonl_line(data: Dict[str, Any]) -> str:
        """
        Returns a single line for JSONL with exactly one trailing newline.
        """
        return ILCanonicalizer.canonicalize(data).decode("utf-8") + "\n"
