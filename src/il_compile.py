import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from src.il_validator import ILCanonicalizer, ILValidator


PROMPT_TEMPLATE_ID = "il_compile_prompt_v1"
DEFAULT_MODEL = "rule_based_v1"
DEFAULT_DETERMINISM = {
    "temperature": 0.0,
    "top_p": 1.0,
    "seed": 7,
    "stream": False,
}
DEFAULT_OPCODES = ["SEARCH_TERMS", "RETRIEVE", "ANSWER", "CITE"]
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "what",
    "when",
    "where",
    "who",
    "why",
    "with",
}
_WIN_ABS_RE = re.compile(r"^[A-Za-z]:[\\/]")
_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{1,31}")


def _make_error(
    code: str,
    message: str,
    path: str = "",
    hint: str = "",
    retriable: bool = False,
) -> Dict[str, Any]:
    err: Dict[str, Any] = {
        "code": code,
        "message": message,
        "retriable": retriable,
    }
    if path:
        err["path"] = path
    if hint:
        err["hint"] = hint
    return err


def _validate_artifact_path(path: Any) -> Optional[str]:
    if not isinstance(path, str) or not path.strip():
        return "path must be a non-empty string"
    if path.startswith("/") or _WIN_ABS_RE.match(path):
        return "absolute path is forbidden"
    if "://" in path or path.startswith("file:"):
        return "URI form is forbidden"
    parts = path.split("/")
    if ".." in parts:
        return "path traversal '..' is forbidden"
    return None


def _normalize_artifact_pointers(raw: Any) -> Tuple[List[Dict[str, str]], List[Dict[str, Any]]]:
    pointers: List[Dict[str, str]] = []
    errors: List[Dict[str, Any]] = []
    if raw is None:
        return pointers, errors
    if not isinstance(raw, list):
        errors.append(
            _make_error(
                "E_SCHEMA",
                "artifact_pointers must be an array",
                path="/artifact_pointers",
                hint="provide [] or an array of objects",
            )
        )
        return pointers, errors

    for i, item in enumerate(raw):
        path_base = f"/artifact_pointers/{i}"
        if not isinstance(item, dict):
            errors.append(
                _make_error(
                    "E_SCHEMA",
                    "artifact pointer must be an object",
                    path=path_base,
                    hint="use {'path':'relative/path'}",
                )
            )
            continue
        if "path" not in item:
            errors.append(_make_error("E_SCHEMA", "missing path", path=f"{path_base}/path"))
            continue
        path = item.get("path")
        path_err = _validate_artifact_path(path)
        if path_err:
            errors.append(
                _make_error(
                    "E_SCHEMA",
                    path_err,
                    path=f"{path_base}/path",
                )
            )
            continue

        pointer: Dict[str, str] = {"path": str(path)}
        sha256 = item.get("sha256")
        if sha256 is not None:
            if not isinstance(sha256, str) or not sha256.strip():
                errors.append(
                    _make_error(
                        "E_SCHEMA",
                        "sha256 must be a non-empty string",
                        path=f"{path_base}/sha256",
                    )
                )
                continue
            pointer["sha256"] = sha256
        pointers.append(pointer)

    pointers.sort(key=lambda x: x["path"])
    return pointers, errors


def _normalize_determinism(raw: Any, seed_override: Optional[int]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    det: Dict[str, Any] = dict(DEFAULT_DETERMINISM)
    errors: List[Dict[str, Any]] = []
    if raw is not None:
        if not isinstance(raw, dict):
            errors.append(
                _make_error(
                    "E_SCHEMA",
                    "determinism must be an object",
                    path="/determinism",
                )
            )
        else:
            for key in raw.keys():
                if key not in {"temperature", "top_p", "seed", "stream"}:
                    errors.append(
                        _make_error(
                            "E_SCHEMA",
                            f"unexpected determinism key: {key}",
                            path=f"/determinism/{key}",
                        )
                    )
            if "temperature" in raw:
                val = raw["temperature"]
                if not isinstance(val, (int, float)) or isinstance(val, bool):
                    errors.append(
                        _make_error(
                            "E_SCHEMA",
                            "temperature must be numeric",
                            path="/determinism/temperature",
                        )
                    )
                else:
                    det["temperature"] = float(val)
            if "top_p" in raw:
                val = raw["top_p"]
                if not isinstance(val, (int, float)) or isinstance(val, bool):
                    errors.append(
                        _make_error(
                            "E_SCHEMA",
                            "top_p must be numeric",
                            path="/determinism/top_p",
                        )
                    )
                else:
                    det["top_p"] = float(val)
            if "seed" in raw:
                val = raw["seed"]
                if not isinstance(val, int) or isinstance(val, bool):
                    errors.append(
                        _make_error(
                            "E_SCHEMA",
                            "seed must be integer",
                            path="/determinism/seed",
                        )
                    )
                else:
                    det["seed"] = val
            if "stream" in raw:
                val = raw["stream"]
                if not isinstance(val, bool):
                    errors.append(
                        _make_error(
                            "E_SCHEMA",
                            "stream must be boolean",
                            path="/determinism/stream",
                        )
                    )
                else:
                    det["stream"] = val

    if seed_override is not None:
        det["seed"] = seed_override

    # Contract v1: decoding knobs are pinned; violations are fail-closed.
    if det["temperature"] != 0.0:
        errors.append(
            _make_error(
                "E_NONDETERMINISTIC",
                "temperature must be 0.0",
                path="/determinism/temperature",
                hint="set temperature=0.0",
            )
        )
    if det["top_p"] != 1.0:
        errors.append(
            _make_error(
                "E_NONDETERMINISTIC",
                "top_p must be 1.0",
                path="/determinism/top_p",
                hint="set top_p=1.0",
            )
        )
    if det["stream"] is not False:
        errors.append(
            _make_error(
                "E_NONDETERMINISTIC",
                "stream must be false",
                path="/determinism/stream",
                hint="set stream=false",
            )
        )
    return det, errors


def normalize_compile_request(
    raw_request: Any,
    seed_override: Optional[int] = None,
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    errors: List[Dict[str, Any]] = []
    if not isinstance(raw_request, dict):
        return None, [_make_error("E_SCHEMA", "request must be an object", path="/")]

    allowed_keys = {
        "schema",
        "request_text",
        "context",
        "constraints",
        "artifact_pointers",
        "determinism",
    }
    for key in sorted(raw_request.keys()):
        if key not in allowed_keys:
            errors.append(
                _make_error(
                    "E_SCHEMA",
                    f"unexpected top-level field: {key}",
                    path=f"/{key}",
                )
            )

    if raw_request.get("schema") != "IL_COMPILE_REQUEST_v1":
        errors.append(
            _make_error(
                "E_SCHEMA",
                "schema must be IL_COMPILE_REQUEST_v1",
                path="/schema",
            )
        )

    request_text = raw_request.get("request_text")
    if not isinstance(request_text, str) or not request_text.strip():
        errors.append(
            _make_error(
                "E_SCHEMA",
                "request_text must be a non-empty string",
                path="/request_text",
            )
        )
    request_text = (request_text or "").strip()

    context = raw_request.get("context", {})
    if not isinstance(context, dict):
        errors.append(_make_error("E_SCHEMA", "context must be an object", path="/context"))
        context = {}

    constraints = raw_request.get("constraints", {})
    if constraints is None:
        constraints = {}
    if not isinstance(constraints, dict):
        errors.append(
            _make_error(
                "E_SCHEMA",
                "constraints must be an object",
                path="/constraints",
            )
        )
        constraints = {}

    allowed_opcodes: List[str] = []
    if "allowed_opcodes" in constraints:
        raw_ops = constraints.get("allowed_opcodes")
        if not isinstance(raw_ops, list):
            errors.append(
                _make_error(
                    "E_SCHEMA",
                    "allowed_opcodes must be an array",
                    path="/constraints/allowed_opcodes",
                )
            )
        else:
            for i, op in enumerate(raw_ops):
                if not isinstance(op, str) or not op.strip():
                    errors.append(
                        _make_error(
                            "E_SCHEMA",
                            "opcode must be non-empty string",
                            path=f"/constraints/allowed_opcodes/{i}",
                        )
                    )
                    continue
                allowed_opcodes.append(op.strip().upper())

    forbidden_keys: List[str] = []
    if "forbidden_keys" in constraints:
        raw_forbidden = constraints.get("forbidden_keys")
        if not isinstance(raw_forbidden, list):
            errors.append(
                _make_error(
                    "E_SCHEMA",
                    "forbidden_keys must be an array",
                    path="/constraints/forbidden_keys",
                )
            )
        else:
            for i, key in enumerate(raw_forbidden):
                if not isinstance(key, str) or not key.strip():
                    errors.append(
                        _make_error(
                            "E_SCHEMA",
                            "forbidden key must be non-empty string",
                            path=f"/constraints/forbidden_keys/{i}",
                        )
                    )
                    continue
                forbidden_keys.append(key.strip())

    max_steps = constraints.get("max_steps", len(DEFAULT_OPCODES))
    if not isinstance(max_steps, int) or isinstance(max_steps, bool) or max_steps <= 0:
        errors.append(
            _make_error(
                "E_SCHEMA",
                "max_steps must be positive integer",
                path="/constraints/max_steps",
            )
        )
        max_steps = len(DEFAULT_OPCODES)

    artifact_pointers, pointer_errors = _normalize_artifact_pointers(raw_request.get("artifact_pointers"))
    errors.extend(pointer_errors)

    determinism, det_errors = _normalize_determinism(raw_request.get("determinism"), seed_override)
    errors.extend(det_errors)

    normalized = {
        "schema": "IL_COMPILE_REQUEST_v1",
        "request_text": request_text,
        "context": context,
        "constraints": {
            "allowed_opcodes": allowed_opcodes,
            "forbidden_keys": forbidden_keys,
            "max_steps": max_steps,
        },
        "artifact_pointers": artifact_pointers,
        "determinism": determinism,
    }
    if errors:
        return None, errors
    return normalized, []


def _normalize_keyword(keyword: str) -> Optional[str]:
    token = keyword.strip().lower()
    if not token:
        return None
    if token in STOP_WORDS:
        return None
    if len(token) < 2:
        return None
    return token


def extract_search_terms(normalized_request: Dict[str, Any], max_terms: int = 8) -> List[str]:
    request_text = normalized_request.get("request_text", "")
    context = normalized_request.get("context", {})

    candidates: List[str] = []
    for token in _TOKEN_RE.findall(request_text.lower()):
        normalized = _normalize_keyword(token)
        if normalized:
            candidates.append(normalized)

    raw_keywords = context.get("keywords", [])
    if isinstance(raw_keywords, list):
        for kw in raw_keywords:
            if isinstance(kw, str):
                normalized = _normalize_keyword(kw)
                if normalized:
                    candidates.append(normalized)

    terms = sorted(set(candidates))
    return terms[:max_terms]


def _build_opcode_plan(normalized_request: Dict[str, Any]) -> List[Dict[str, Any]]:
    constraints = normalized_request.get("constraints", {})
    allowed = constraints.get("allowed_opcodes") or []
    max_steps = constraints.get("max_steps", len(DEFAULT_OPCODES))
    if allowed:
        allowed_set = {op.upper() for op in allowed}
        selected = [op for op in DEFAULT_OPCODES if op in allowed_set]
    else:
        selected = list(DEFAULT_OPCODES)
    selected = selected[:max_steps]
    return [{"op": op, "args": {}} for op in selected]


def _collect_forbidden_keys(data: Any, forbidden: set, path: str = "") -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        for key, value in data.items():
            next_path = f"{path}/{key}"
            if key in forbidden:
                hits.append(
                    _make_error(
                        "E_FORBIDDEN",
                        f"forbidden key in compiled output: {key}",
                        path=next_path,
                        hint="adjust constraints or request",
                    )
                )
            hits.extend(_collect_forbidden_keys(value, forbidden, next_path))
    elif isinstance(data, list):
        for i, value in enumerate(data):
            hits.extend(_collect_forbidden_keys(value, forbidden, f"{path}/{i}"))
    return hits


def render_compile_prompt(normalized_request: Dict[str, Any]) -> str:
    constraints = normalized_request["constraints"]
    artifact_lines = []
    for pointer in normalized_request["artifact_pointers"]:
        if "sha256" in pointer:
            artifact_lines.append(f"- {pointer['path']}#{pointer['sha256']}")
        else:
            artifact_lines.append(f"- {pointer['path']}")
    if not artifact_lines:
        artifact_lines.append("- (none)")

    lines = [
        "SYSTEM: compile natural language request into deterministic IL JSON",
        f"REQUEST_TEXT: {normalized_request['request_text']}",
        f"ALLOWED_OPCODES: {','.join(constraints['allowed_opcodes']) or '(default)'}",
        f"FORBIDDEN_KEYS: {','.join(constraints['forbidden_keys']) or '(none)'}",
        f"MAX_STEPS: {constraints['max_steps']}",
        "ARTIFACT_POINTERS:",
        *artifact_lines,
        f"CONTEXT_JSON: {json.dumps(normalized_request['context'], ensure_ascii=False, sort_keys=True, separators=(',', ':'))}",
        f"DETERMINISM_JSON: {json.dumps(normalized_request['determinism'], ensure_ascii=False, sort_keys=True, separators=(',', ':'))}",
        "OUTPUT: JSON object with il/meta/evidence only; no errors key on success",
    ]
    return "\n".join(lines) + "\n"


def compile_request_bundle(
    raw_request: Any,
    model: str = DEFAULT_MODEL,
    seed_override: Optional[int] = None,
) -> Dict[str, Any]:
    normalized, errors = normalize_compile_request(raw_request, seed_override=seed_override)
    bundle: Dict[str, Any] = {
        "status": "ERROR",
        "normalized_request": normalized or {},
        "prompt_text": "",
        "raw_response_text": "",
        "compiled_output": None,
        "canonical_bytes": None,
        "errors": list(errors),
        "report": {},
    }

    determinism = (
        normalized["determinism"] if normalized else dict(DEFAULT_DETERMINISM)
    )
    if seed_override is not None:
        determinism["seed"] = seed_override

    if normalized:
        bundle["prompt_text"] = render_compile_prompt(normalized)
    else:
        bundle["prompt_text"] = "SYSTEM: compile request failed before normalization\n"

    if not bundle["errors"] and normalized:
        terms = extract_search_terms(normalized)
        if not terms:
            bundle["errors"].append(
                _make_error(
                    "E_INPUT",
                    "could not derive search terms from request_text/context",
                    path="/request_text",
                    hint="add concrete domain keywords",
                )
            )
        opcodes = _build_opcode_plan(normalized)
        if not opcodes:
            bundle["errors"].append(
                _make_error(
                    "E_UNSUPPORTED",
                    "no executable opcodes after constraints filtering",
                    path="/constraints/allowed_opcodes",
                )
            )

        if not bundle["errors"]:
            compiled = {
                "il": {
                    "opcodes": opcodes,
                    "search_terms": terms,
                },
                "meta": {
                    "version": "il_contract_v1",
                    "generator": model,
                },
                "evidence": {
                    "notes": "compiled via il_compile_contract_v1 rule-based planner",
                    "compile_contract": "il_compile_contract_v1",
                    "prompt_template_id": PROMPT_TEMPLATE_ID,
                },
            }

            forbidden = set(normalized["constraints"]["forbidden_keys"])
            if forbidden:
                bundle["errors"].extend(_collect_forbidden_keys(compiled, forbidden))

            if not bundle["errors"]:
                validator = ILValidator()
                valid, val_errors = validator.validate(compiled)
                if not valid:
                    for err in val_errors:
                        bundle["errors"].append(
                            _make_error(
                                "E_VALIDATE",
                                err.get("message", "validator error"),
                                path=err.get("path", ""),
                                hint=err.get("hint", ""),
                            )
                        )
                else:
                    try:
                        canonical_bytes = ILCanonicalizer.canonicalize(compiled)
                        bundle["compiled_output"] = compiled
                        bundle["canonical_bytes"] = canonical_bytes
                        bundle["raw_response_text"] = json.dumps(
                            compiled,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        )
                    except Exception as exc:
                        bundle["errors"].append(
                            _make_error(
                                "E_VALIDATE",
                                f"canonicalization failed: {exc}",
                                path="/",
                            )
                        )

    if not bundle["raw_response_text"]:
        bundle["raw_response_text"] = "RULE_BASED_COMPILER: no IL output"

    status = "OK" if not bundle["errors"] and bundle["compiled_output"] is not None else "ERROR"
    bundle["status"] = status
    report: Dict[str, Any] = {
        "schema": "IL_COMPILE_REPORT_v1",
        "status": status,
        "error_count": len(bundle["errors"]),
        "determinism": determinism,
        "prompt_template_id": PROMPT_TEMPLATE_ID,
        "model": model,
    }
    if bundle["canonical_bytes"] is not None:
        report["canonical_sha256"] = hashlib.sha256(bundle["canonical_bytes"]).hexdigest()
    bundle["report"] = report
    return bundle
