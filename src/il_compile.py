import hashlib
import json
import os
import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.il_model_backend import (
    ModelBackendAdapter,
    ModelBackendRequest,
    resolve_model_backend_adapter,
    resolve_requested_model_backend,
)
from src.il_validator import ILCanonicalizer, ILValidator


DEFAULT_PROMPT_PROFILE = "v1"
AUTO_PROMPT_PROFILE = "auto"
PROMPT_TEMPLATE_IDS = {
    "v1": "il_compile_prompt_v1",
    "strict_json_v2": "il_compile_prompt_strict_json_v2",
    "contract_json_v3": "il_compile_prompt_contract_json_v3",
}
DEFAULT_MODEL = "rule_based_v1"
DEFAULT_PROVIDER = "rule_based"
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
_CODE_FENCE_RX = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
_MAX_REPAIR_CLOSE_DEPTH = 6


def is_auto_prompt_profile(prompt_profile: Optional[str]) -> bool:
    text = str(prompt_profile or "").strip().lower()
    return text in {"", AUTO_PROMPT_PROFILE}


def normalize_prompt_profile(prompt_profile: str) -> str:
    profile = (prompt_profile or DEFAULT_PROMPT_PROFILE).strip()
    if profile in PROMPT_TEMPLATE_IDS:
        return profile
    return DEFAULT_PROMPT_PROFILE


def normalize_prompt_profile_input(prompt_profile: Optional[str]) -> str:
    if is_auto_prompt_profile(prompt_profile):
        return AUTO_PROMPT_PROFILE
    return normalize_prompt_profile(str(prompt_profile or DEFAULT_PROMPT_PROFILE))


def resolve_prompt_template_id(prompt_profile: str) -> str:
    normalized = normalize_prompt_profile(prompt_profile)
    return PROMPT_TEMPLATE_IDS.get(normalized, PROMPT_TEMPLATE_IDS[DEFAULT_PROMPT_PROFILE])


def select_prompt_profile(
    normalized_request: Dict[str, Any],
    requested_prompt_profile: Optional[str],
    provider_requested: str,
) -> Tuple[str, str, str]:
    requested = str(requested_prompt_profile or "").strip()
    if not is_auto_prompt_profile(requested):
        normalized = normalize_prompt_profile(requested)
        selected_by = "manual" if requested in PROMPT_TEMPLATE_IDS else "manual_fallback_default"
        reason = (
            f"requested={requested}"
            if selected_by == "manual"
            else f"requested={requested} unsupported -> fallback={normalized}"
        )
        return normalized, selected_by, reason

    request_text = str(normalized_request.get("request_text", "") or "")
    constraints = dict(normalized_request.get("constraints", {}) or {})
    artifact_pointers = list(normalized_request.get("artifact_pointers", []) or [])
    forbidden_keys = list(constraints.get("forbidden_keys", []) or [])
    max_steps = int(constraints.get("max_steps", len(DEFAULT_OPCODES)))

    request_len = len(request_text)
    artifact_count = len(artifact_pointers)
    forbidden_count = len(forbidden_keys)

    if forbidden_count > 0 or artifact_count >= 4 or request_len >= 260 or max_steps >= 6:
        reason = (
            f"auto_high_complexity(request_len={request_len}, artifact_count={artifact_count}, "
            f"forbidden_count={forbidden_count}, max_steps={max_steps})"
        )
        return "contract_json_v3", "auto", reason

    if provider_requested == "local_llm" or artifact_count >= 2 or request_len >= 140 or max_steps >= 5:
        reason = (
            f"auto_medium_complexity(request_len={request_len}, artifact_count={artifact_count}, "
            f"provider={provider_requested}, max_steps={max_steps})"
        )
        return "strict_json_v2", "auto", reason

    reason = (
        f"auto_low_complexity(request_len={request_len}, artifact_count={artifact_count}, "
        f"provider={provider_requested}, max_steps={max_steps})"
    )
    return "v1", "auto", reason


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _resolve_confidence_threshold(override: Optional[float] = None) -> float:
    if override is not None:
        try:
            return _clamp01(float(override))
        except Exception:
            return 0.60

    raw = os.environ.get("IL_COMPILE_CONFIDENCE_WARN_BELOW", "0.60")
    try:
        return _clamp01(float(raw))
    except Exception:
        return 0.60


def _compute_compile_confidence(
    *,
    status: str,
    normalized_request: Optional[Dict[str, Any]],
    provider_selected: str,
    fallback_used: bool,
    prompt_profile_selected: str,
) -> Tuple[float, List[Dict[str, Any]]]:
    factors: List[Dict[str, Any]] = []
    if status != "OK" or not isinstance(normalized_request, dict):
        factors.append({"id": "compile_not_ok", "delta": -1.0, "detail": "compile status is not OK"})
        return 0.0, factors

    score = 0.80
    factors.append({"id": "base", "delta": 0.80, "detail": "base confidence for deterministic compile path"})

    constraints = dict(normalized_request.get("constraints", {}) or {})
    artifact_pointers = list(normalized_request.get("artifact_pointers", []) or [])
    terms = extract_search_terms(normalized_request)

    artifact_count = len(artifact_pointers)
    if artifact_count == 0:
        score -= 0.15
        factors.append({"id": "artifact_context_missing", "delta": -0.15, "detail": "no artifact pointers"})
    else:
        bonus = min(0.10, artifact_count * 0.03)
        score += bonus
        factors.append({"id": "artifact_context_present", "delta": round(bonus, 3), "detail": f"artifact_count={artifact_count}"})

    term_count = len(terms)
    if term_count < 2:
        score -= 0.10
        factors.append({"id": "few_terms", "delta": -0.10, "detail": f"term_count={term_count}"})
    else:
        bonus = min(0.10, term_count * 0.02)
        score += bonus
        factors.append({"id": "enough_terms", "delta": round(bonus, 3), "detail": f"term_count={term_count}"})

    max_steps = int(constraints.get("max_steps", len(DEFAULT_OPCODES)))
    if max_steps >= 6:
        score -= 0.05
        factors.append({"id": "high_step_budget", "delta": -0.05, "detail": f"max_steps={max_steps}"})

    if provider_selected == "rule_based":
        score += 0.03
        factors.append({"id": "provider_rule_based", "delta": 0.03, "detail": "deterministic provider"})
    else:
        score -= 0.02
        factors.append({"id": "provider_local_llm", "delta": -0.02, "detail": "model variance risk"})

    if fallback_used:
        score -= 0.25
        factors.append({"id": "fallback_used", "delta": -0.25, "detail": "provider fallback indicates instability"})

    if prompt_profile_selected == "contract_json_v3":
        score += 0.05
        factors.append({"id": "profile_contract_json_v3", "delta": 0.05, "detail": "strict profile bonus"})
    elif prompt_profile_selected == "strict_json_v2":
        score += 0.03
        factors.append({"id": "profile_strict_json_v2", "delta": 0.03, "detail": "strict profile bonus"})

    final_score = round(_clamp01(score), 6)
    return final_score, factors


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
    normalized = path.replace("\\", "/")
    if normalized.startswith("/") or normalized.startswith("//") or _WIN_ABS_RE.match(path):
        return "absolute path is forbidden"
    if "://" in path or path.startswith("file:"):
        return "URI form is forbidden"
    parts = normalized.split("/")
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


def render_compile_prompt(normalized_request: Dict[str, Any], prompt_profile: str = DEFAULT_PROMPT_PROFILE) -> str:
    constraints = normalized_request["constraints"]
    profile = normalize_prompt_profile(prompt_profile)
    artifact_lines = []
    for pointer in normalized_request["artifact_pointers"]:
        if "sha256" in pointer:
            artifact_lines.append(f"- {pointer['path']}#{pointer['sha256']}")
        else:
            artifact_lines.append(f"- {pointer['path']}")
    if not artifact_lines:
        artifact_lines.append("- (none)")

    common_lines = [
        "SYSTEM: compile natural language request into deterministic IL JSON",
        f"REQUEST_TEXT: {normalized_request['request_text']}",
        f"ALLOWED_OPCODES: {','.join(constraints['allowed_opcodes']) or '(default)'}",
        f"FORBIDDEN_KEYS: {','.join(constraints['forbidden_keys']) or '(none)'}",
        f"MAX_STEPS: {constraints['max_steps']}",
        "ARTIFACT_POINTERS:",
        *artifact_lines,
        f"CONTEXT_JSON: {json.dumps(normalized_request['context'], ensure_ascii=False, sort_keys=True, separators=(',', ':'))}",
        f"DETERMINISM_JSON: {json.dumps(normalized_request['determinism'], ensure_ascii=False, sort_keys=True, separators=(',', ':'))}",
    ]

    if profile == "strict_json_v2":
        profile_lines = [
            "OUTPUT_RULES:",
            "- Return ONLY one JSON object. No markdown. No explanation text.",
            "- Object MUST contain keys: il, meta, evidence.",
            "- Top-level errors key is forbidden on success.",
            "- Keep output deterministic and compact.",
            "JSON_SHAPE_HINT:",
            '{"il":{"opcodes":[{"op":"SEARCH_TERMS","args":{}}],"search_terms":["alpha"]},"meta":{"version":"il_contract_v1","generator":"local_llm"},"evidence":{"notes":"...","compile_contract":"il_compile_contract_v1","prompt_template_id":"%s"}}'
            % resolve_prompt_template_id(profile),
        ]
    elif profile == "contract_json_v3":
        profile_lines = [
            "OUTPUT_RULES:",
            "1) Emit strict JSON object only.",
            "2) Include il/meta/evidence and nothing else at top-level.",
            "3) meta.version MUST be il_contract_v1.",
            "4) il.search_terms MUST be array[str] derived from request/context.",
            "5) il.opcodes MUST follow ALLOWED_OPCODES and MAX_STEPS.",
            "6) Do not emit timestamp/uuid/random/nonce.",
            "7) If uncertain, still emit best deterministic IL object (no prose).",
            "FINAL_CHECK: ensure JSON parse succeeds exactly.",
        ]
    else:
        profile_lines = [
            "OUTPUT: JSON object with il/meta/evidence only; no errors key on success",
        ]
    lines = common_lines + profile_lines
    return "\n".join(lines) + "\n"


LLMAdapter = Callable[[str, str, Dict[str, Any]], str]


def _extract_first_json_object_text(text: str) -> Optional[str]:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _extract_llm_json_candidates(text: str) -> List[str]:
    candidates: List[str] = []
    stripped = (text or "").strip()
    if stripped:
        candidates.append(stripped)

    for match in _CODE_FENCE_RX.finditer(text or ""):
        body = match.group(1).strip()
        if body:
            candidates.append(body)

    extracted = _extract_first_json_object_text(text or "")
    if extracted:
        candidates.append(extracted.strip())

    # Keep deterministic order while removing duplicates.
    unique: List[str] = []
    seen = set()
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique


def _is_success_payload_shape(payload: Any) -> Tuple[bool, List[Dict[str, Any]]]:
    errors: List[Dict[str, Any]] = []
    if not isinstance(payload, dict):
        return False, [_make_error("E_PARSE", "model response must be JSON object", path="/")]
    for key in ("il", "meta", "evidence"):
        if key not in payload:
            errors.append(_make_error("E_PARSE", f"missing key in model JSON: {key}", path=f"/{key}"))
    if "errors" in payload:
        errors.append(_make_error("E_PARSE", "model output must not include top-level errors on success", path="/errors"))
    return len(errors) == 0, errors


def _repair_trailing_commas(text: str) -> Optional[str]:
    # Only remove trailing commas that are outside JSON strings.
    out: List[str] = []
    in_string = False
    escape = False
    changed = False
    i = 0
    while i < len(text):
        ch = text[i]
        if in_string:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue

        if ch == ",":
            j = i + 1
            while j < len(text) and text[j] in {" ", "\t", "\r", "\n"}:
                j += 1
            if j < len(text) and text[j] in {"}", "]"}:
                changed = True
                i += 1
                continue

        out.append(ch)
        i += 1

    if not changed:
        return None
    return "".join(out)


def _repair_missing_closing_braces(text: str) -> Optional[str]:
    # Intentionally only repairs unmatched "}" depth.
    # Unclosed arrays/brackets are left fail-closed to keep repair scope narrow.
    depth = 0
    in_string = False
    escape = False
    for ch in text:
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return None
    if in_string:
        return None
    if depth <= 0 or depth > _MAX_REPAIR_CLOSE_DEPTH:
        return None
    return text + ("}" * depth)


def _repair_missing_object_brace_before_array_close(text: str) -> Optional[str]:
    # Allow a single missing object close immediately before an array close, e.g.
    # {... "args": {...}}] -> {... "args": {...}}}] when the repaired payload parses.
    stripped_end = len(text.rstrip())
    in_string = False
    escape = False
    for idx, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch != "]":
            continue

        left = idx - 1
        while left >= 0 and text[left] in {" ", "\t", "\r", "\n"}:
            left -= 1
        if left < 0 or text[left] != "}":
            continue

        right = idx + 1
        while right < len(text) and text[right] in {" ", "\t", "\r", "\n"}:
            right += 1
        if right >= len(text) or text[right] not in {",", "}", "]"}:
            continue

        candidates = [text[:idx] + "}" + text[idx:]]
        if stripped_end > 0 and text[stripped_end - 1] == "}":
            candidates.append(text[:idx] + "}" + text[idx : stripped_end - 1] + text[stripped_end:])

        for repaired in candidates:
            try:
                json.loads(repaired)
                return repaired
            except Exception:
                continue
    return None


def _parse_candidate_with_repair(candidate: str) -> Tuple[Optional[Any], str, bool, str]:
    try:
        return json.loads(candidate), "", False, ""
    except Exception as exc:
        parse_hint = str(exc)

    # S32-08 bounded repair rules (allowlist only).
    repair_rules = [
        ("R_PARSE_TRAILING_COMMA", _repair_trailing_commas),
        ("R_PARSE_CLOSE_OBJECT_BEFORE_ARRAY_END", _repair_missing_object_brace_before_array_close),
        ("R_PARSE_CLOSE_BRACE", _repair_missing_closing_braces),
    ]
    for rule_id, repair_fn in repair_rules:
        repaired = repair_fn(candidate)
        if repaired is None:
            continue
        try:
            payload = json.loads(repaired)
            return payload, "", True, rule_id
        except Exception as exc:
            parse_hint = str(exc)

    return None, parse_hint, False, ""


def _parse_llm_json_response(raw_response: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], bool, str]:
    candidates = _extract_llm_json_candidates(raw_response)
    if not candidates:
        return None, [
            _make_error(
                "E_PARSE",
                "model response is not valid JSON object text",
                path="/",
                hint="return only JSON object with il/meta/evidence",
            )
        ], False, ""

    parse_errors: List[str] = []
    shape_errors: List[Dict[str, Any]] = []
    for candidate in candidates:
        payload, parse_hint, repair_applied, repair_rule_id = _parse_candidate_with_repair(candidate)
        if payload is None:
            parse_errors.append(parse_hint)
            continue
        ok_shape, errors = _is_success_payload_shape(payload)
        if ok_shape:
            return payload, [], repair_applied, repair_rule_id
        shape_errors = errors

    if shape_errors:
        return None, shape_errors, False, ""
    parse_hint = parse_errors[0] if parse_errors else "unknown parse error"
    return None, [
        _make_error(
            "E_PARSE",
            f"json parse failed: {parse_hint}",
            path="/",
            hint="return strict JSON object",
        )
    ], False, ""


def _compile_rule_based(
    normalized_request: Dict[str, Any],
    model: str,
    prompt_template_id: str,
) -> Tuple[Optional[Dict[str, Any]], str, List[Dict[str, Any]]]:
    terms = extract_search_terms(normalized_request)
    if not terms:
        return None, "RULE_BASED_COMPILER: no IL output", [
            _make_error(
                "E_INPUT",
                "could not derive search terms from request_text/context",
                path="/request_text",
                hint="add concrete domain keywords",
            )
        ]

    opcodes = _build_opcode_plan(normalized_request)
    if not opcodes:
        return None, "RULE_BASED_COMPILER: no IL output", [
            _make_error(
                "E_UNSUPPORTED",
                "no executable opcodes after constraints filtering",
                path="/constraints/allowed_opcodes",
            )
        ]

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
            "prompt_template_id": prompt_template_id,
        },
    }
    raw_response_text = json.dumps(
        compiled,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return compiled, raw_response_text, []


def _compile_local_llm(
    prompt_text: str,
    determinism: Dict[str, Any],
    model: str,
    model_backend: Optional[ModelBackendAdapter] = None,
    model_backend_id: Optional[str] = None,
    llm_adapter: Optional[LLMAdapter] = None,
) -> Tuple[Optional[Dict[str, Any]], str, List[Dict[str, Any]], bool, str, str, str]:
    try:
        adapter = resolve_model_backend_adapter(
            adapter=model_backend or llm_adapter,
            backend_id=model_backend_id,
        )
    except Exception as exc:
        return None, "", [
            _make_error(
                "E_BACKEND",
                f"model backend resolution failed: {exc}",
                path="/model_backend",
                hint="use openai_compat or gemma_lab",
                retriable=True,
            )
        ], False, "", "", ""

    try:
        backend_response = adapter.invoke(
            ModelBackendRequest(
                prompt_text=prompt_text,
                model=model,
                determinism=determinism,
            )
        )
    except Exception as exc:
        return None, "", [
            _make_error(
                "E_MODEL",
                f"local_llm invocation failed: {exc}",
                path="/",
                retriable=True,
            )
        ], False, "", getattr(adapter, "backend_id", ""), ""

    raw_response = backend_response.raw_text

    if not isinstance(raw_response, str) or not raw_response.strip():
        return None, "", [
            _make_error(
                "E_MODEL",
                "local_llm returned empty response",
                path="/",
                retriable=True,
            )
        ], False, "", getattr(adapter, "backend_id", ""), backend_response.target

    parsed, parse_errors, repair_applied, repair_rule_id = _parse_llm_json_response(raw_response)
    if parse_errors:
        return None, raw_response, parse_errors, False, "", getattr(adapter, "backend_id", ""), backend_response.target
    return parsed, raw_response, [], repair_applied, repair_rule_id, getattr(adapter, "backend_id", ""), backend_response.target


def _finalize_compiled_output(
    compiled: Dict[str, Any],
    normalized_request: Dict[str, Any],
) -> Tuple[Optional[bytes], List[Dict[str, Any]]]:
    errors: List[Dict[str, Any]] = []
    forbidden = set(normalized_request["constraints"]["forbidden_keys"])
    if forbidden:
        errors.extend(_collect_forbidden_keys(compiled, forbidden))

    if errors:
        return None, errors

    validator = ILValidator()
    valid, val_errors = validator.validate(compiled)
    if not valid:
        for err in val_errors:
            errors.append(
                _make_error(
                    "E_VALIDATE",
                    err.get("message", "validator error"),
                    path=err.get("path", ""),
                    hint=err.get("hint", ""),
                )
            )
        return None, errors

    try:
        canonical_bytes = ILCanonicalizer.canonicalize(compiled)
    except Exception as exc:
        return None, [_make_error("E_VALIDATE", f"canonicalization failed: {exc}", path="/")]

    return canonical_bytes, []


def compile_request_bundle(
    raw_request: Any,
    model: str = DEFAULT_MODEL,
    seed_override: Optional[int] = None,
    provider: str = DEFAULT_PROVIDER,
    allow_fallback: bool = True,
    prompt_profile: str = AUTO_PROMPT_PROFILE,
    confidence_warn_threshold: Optional[float] = None,
    model_backend_id: Optional[str] = None,
    model_backend: Optional[ModelBackendAdapter] = None,
    llm_adapter: Optional[LLMAdapter] = None,
) -> Dict[str, Any]:
    started = time.perf_counter()
    normalized, errors = normalize_compile_request(raw_request, seed_override=seed_override)
    provider_requested = (provider or DEFAULT_PROVIDER).strip().lower()
    if provider_requested not in {"rule_based", "local_llm"}:
        errors.append(
            _make_error(
                "E_UNSUPPORTED",
                f"unsupported provider: {provider_requested}",
                path="/provider",
                hint="use rule_based or local_llm",
            )
        )
        provider_requested = "rule_based"

    model_backend_requested = ""
    if provider_requested == "local_llm":
        model_backend_requested = (
            getattr(model_backend, "backend_id", "")
            or (getattr(llm_adapter, "backend_id", "") if llm_adapter is not None else "")
            or ("legacy_callable" if llm_adapter is not None else "")
            or resolve_requested_model_backend(model_backend_id)
        )

    prompt_profile_selected = DEFAULT_PROMPT_PROFILE
    prompt_template_id = resolve_prompt_template_id(prompt_profile_selected)
    profile_selected_by = "fallback_default"
    profile_select_reason = "request_normalization_failed"

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

    determinism = normalized["determinism"] if normalized else dict(DEFAULT_DETERMINISM)
    if seed_override is not None:
        determinism["seed"] = seed_override

    if normalized:
        prompt_profile_selected, profile_selected_by, profile_select_reason = select_prompt_profile(
            normalized_request=normalized,
            requested_prompt_profile=prompt_profile,
            provider_requested=provider_requested,
        )
        prompt_template_id = resolve_prompt_template_id(prompt_profile_selected)
        bundle["prompt_text"] = render_compile_prompt(
            normalized,
            prompt_profile=prompt_profile_selected,
        )
    else:
        bundle["prompt_text"] = "SYSTEM: compile request failed before normalization\n"

    if not bundle["errors"] and normalized:
        provider_selected = provider_requested
        fallback_used = False
        fallback_reason = ""
        repair_applied = False
        repair_rule_id = ""
        model_backend_used = ""
        model_backend_target = ""

        if provider_requested == "local_llm":
            (
                compiled,
                raw_response,
                compile_errors,
                repair_applied,
                repair_rule_id,
                model_backend_used,
                model_backend_target,
            ) = _compile_local_llm(
                prompt_text=bundle["prompt_text"],
                determinism=normalized["determinism"],
                model=model,
                model_backend=model_backend,
                model_backend_id=model_backend_id,
                llm_adapter=llm_adapter,
            )
        else:
            compiled, raw_response, compile_errors = _compile_rule_based(
                normalized_request=normalized,
                model=model,
                prompt_template_id=prompt_template_id,
            )
            repair_applied = False
            repair_rule_id = ""
            model_backend_used = ""
            model_backend_target = ""

        bundle["raw_response_text"] = raw_response or "RULE_BASED_COMPILER: no IL output"

        if compile_errors and provider_requested == "local_llm" and allow_fallback:
            fallback_used = True
            fallback_reason = compile_errors[0].get("message", "local_llm compile failed")
            provider_selected = "rule_based"
            compiled, fallback_raw_response, compile_errors = _compile_rule_based(
                normalized_request=normalized,
                model=model,
                prompt_template_id=prompt_template_id,
            )
            bundle["raw_response_text"] = fallback_raw_response
            repair_applied = False
            repair_rule_id = ""

        if compile_errors:
            bundle["errors"].extend(compile_errors)
        elif compiled is not None:
            canonical_bytes, finalize_errors = _finalize_compiled_output(
                compiled=compiled,
                normalized_request=normalized,
            )
            if finalize_errors:
                bundle["errors"].extend(finalize_errors)
            else:
                bundle["compiled_output"] = compiled
                bundle["canonical_bytes"] = canonical_bytes
        else:
            bundle["errors"].append(_make_error("E_INPUT", "no compiled output produced", path="/"))
    else:
        provider_selected = provider_requested
        fallback_used = False
        fallback_reason = ""
        repair_applied = False
        repair_rule_id = ""
        model_backend_used = ""
        model_backend_target = ""

    if not bundle["raw_response_text"]:
        bundle["raw_response_text"] = "RULE_BASED_COMPILER: no IL output"

    bundle["errors"].sort(key=lambda x: (x.get("path", ""), x.get("code", ""), x.get("message", "")))
    status = "OK" if not bundle["errors"] and bundle["compiled_output"] is not None else "ERROR"
    bundle["status"] = status
    report: Dict[str, Any] = {
        "schema": "IL_COMPILE_REPORT_v1",
        "status": status,
        "error_count": len(bundle["errors"]),
        "determinism": determinism,
        "prompt_template_id": prompt_template_id,
        "prompt_profile": prompt_profile_selected,
        "profile_selected_by": profile_selected_by,
        "profile_select_reason": profile_select_reason,
        "model": model,
        "provider_requested": provider_requested,
        "provider_selected": provider_selected,
        "model_backend_requested": model_backend_requested,
        "model_backend_used": model_backend_used,
        "model_backend_target": model_backend_target,
        "fallback_used": fallback_used,
        "repair_applied": repair_applied,
        "repair_rule_id": repair_rule_id,
        "compile_latency_ms": int((time.perf_counter() - started) * 1000),
    }
    if fallback_reason:
        report["fallback_reason"] = fallback_reason
    if bundle["canonical_bytes"] is not None:
        report["canonical_sha256"] = hashlib.sha256(bundle["canonical_bytes"]).hexdigest()
    request_for_hash = normalized if normalized is not None else (raw_request if isinstance(raw_request, dict) else {})
    try:
        request_bytes = json.dumps(
            request_for_hash,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        report["request_sha256"] = hashlib.sha256(request_bytes).hexdigest()
    except Exception:
        report["request_sha256"] = ""
    report["prompt_sha256"] = hashlib.sha256(bundle["prompt_text"].encode("utf-8")).hexdigest()
    report["artifact_pointer_count"] = len((normalized or {}).get("artifact_pointers", []))
    code_hist: Dict[str, int] = {}
    for err in bundle["errors"]:
        code = str(err.get("code", "")).strip()
        if code:
            code_hist[code] = code_hist.get(code, 0) + 1
    if code_hist:
        report["error_codes"] = dict(sorted(code_hist.items(), key=lambda kv: kv[0]))

    confidence, confidence_factors = _compute_compile_confidence(
        status=status,
        normalized_request=normalized,
        provider_selected=provider_selected,
        fallback_used=fallback_used,
        prompt_profile_selected=prompt_profile_selected,
    )
    confidence_warn_threshold = _resolve_confidence_threshold(confidence_warn_threshold)
    report["confidence"] = confidence
    report["confidence_warn_threshold"] = confidence_warn_threshold
    report["confidence_status"] = "OK" if confidence >= confidence_warn_threshold else "LOW"
    report["confidence_factors"] = confidence_factors

    bundle["report"] = report
    return bundle
