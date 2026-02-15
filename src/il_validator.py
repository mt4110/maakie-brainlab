import json
import re
from typing import Dict, Any, List, Optional, Tuple

class ILValidator:
    """
    Validates IL items against Contract v1 rules [HARDCORE].
    """
    
    FORBIDDEN_FIELDS = {
        "created_at", "generated_at", "timestamp", "now",
        "uuid", "nonce", "random"
    }
    
    FORBIDDEN_KEY_PATTERN = re.compile(r"[^A-Za-z0-9_./-]")

    # Normalized error codes per Contract v1
    # E_SCHEMA | E_FORBIDDEN | E_AMBIGUOUS | E_MISSING_ARTIFACT | E_NONDETERMINISTIC | E_UNSUPPORTED
    
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

        # Check for reserved key "errors" at top level
        if "errors" in data:
            self.add_error("E_SCHEMA", "Reserved key 'errors' found in input", path="/errors")

        # Required top-level keys
        for key in ["il", "meta", "evidence"]:
            if key not in data:
                self.add_error("E_SCHEMA", f"Missing required field: {key}")

        # Check for unexpected top-level keys [Contract v1 additionalProperties:false]
        allowed_top_level_keys = {"il", "meta", "evidence", "errors"}
        unexpected_keys = set(data.keys()) - allowed_top_level_keys
        for key in sorted(unexpected_keys):
            self.add_error("E_SCHEMA", f"Unexpected top-level field: {key}", path=f"/{key}")

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

        # il shape check [MUST-3]
        if "il" in data and not isinstance(data["il"], dict):
            self.add_error("E_SCHEMA", "il must be an object", path="/il")

        # Recursive validation for forbidden fields, nulls, and types
        self._validate_recursive(data, "")

        # Sort errors by (path, code, message) for determinism
        self.errors.sort(key=lambda x: (x.get("path", ""), x["code"], x["message"]))
        
        return len(self.errors) == 0, self.errors

    def _validate_recursive(self, val: Any, path: str):
        if val is None:
            # null is forbidden [MUST-3.3] -> E_FORBIDDEN
            self.add_error("E_FORBIDDEN", "null values are forbidden", path=path)
            return

        if isinstance(val, dict):
            for k, v in val.items():
                if k == "errors":
                    if path != "": # validate() already reports for top-level /errors
                        self.add_error("E_SCHEMA", f"Reserved key 'errors' found in input: {k}", path=f"{path}/{k}")
                    continue # Do not recurse into client-provided errors

                if k in self.FORBIDDEN_FIELDS:
                    self.add_error("E_FORBIDDEN", f"Forbidden field: {k}", path=f"{path}/{k}")
                
                if self.FORBIDDEN_KEY_PATTERN.search(k):
                    self.add_error("E_SCHEMA", f"Key contains forbidden characters: {k}", path=f"{path}/{k}")
                
                self._validate_recursive(v, f"{path}/{k}")
        
        elif isinstance(val, list):
            for i, item in enumerate(val):
                self._validate_recursive(item, f"{path}/{i}")
        
        elif isinstance(val, bool):
            # bool is forbidden to be treated as int [HARDCORE+] -> E_SCHEMA
            self.add_error("E_SCHEMA", "bool values are forbidden (must use int or string)", path=path)
            
        elif isinstance(val, float):
            # float is strictly forbidden [HARDCORE+] -> E_SCHEMA
            self.add_error("E_SCHEMA", "float values are forbidden (strict integer only)", path=path)
        
        elif type(val) is int:
            # Check 53-bit range
            if abs(val) > (2**53 - 1):
                self.add_error("E_SCHEMA", f"Number out of 53-bit range: {val}", path=path)
        
        elif isinstance(val, str):
            if "\r" in val:
                self.add_error("E_SCHEMA", "CR characters are forbidden in strings", path=path)

class ILCanonicalizer:
    """
    Serializes IL items into canonical JSON bytes [HARDCORE].
    """
    
    @staticmethod
    def canonicalize(data: Dict[str, Any]) -> bytes:
        """
        Produces compact, sorted-key, UTF-8 JSON bytes without trailing newline.
        Enforces allow_nan=False for absolute safety.
        """
        compact_json = json.dumps(
            data,
            sort_keys=True,
            ensure_ascii=False,
            separators=(',', ':'),
            allow_nan=False
        )
        return compact_json.encode("utf-8")

    @staticmethod
    def to_jsonl_line(data: Dict[str, Any]) -> str:
        """
        Returns a single line for JSONL with exactly one trailing newline.
        """
        return ILCanonicalizer.canonicalize(data).decode("utf-8") + "\n"
