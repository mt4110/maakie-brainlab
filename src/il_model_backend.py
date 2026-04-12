from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable


DEFAULT_MODEL_BACKEND = "openai_compat"
SUPPORTED_MODEL_BACKENDS = ("openai_compat", "gemma_lab")
DEFAULT_OPENAI_COMPAT_API_BASE = "http://127.0.0.1:11434/v1"
GENERIC_COMPILE_MODEL_IDS = {"rule_based_v1"}


LegacyLLMCallable = Callable[[str, str, Dict[str, Any]], str]


@dataclass(frozen=True)
class ModelBackendRequest:
    prompt_text: str
    model: str
    determinism: Dict[str, Any]


@dataclass(frozen=True)
class ModelBackendResponse:
    raw_text: str
    backend_id: str
    target: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ModelBackendAdapter(Protocol):
    backend_id: str

    def invoke(self, request: ModelBackendRequest) -> ModelBackendResponse:
        ...


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resolve_model_backend_from_candidates(*candidates: Optional[str]) -> str:
    for raw in candidates:
        text = str(raw or "").strip().lower()
        if text:
            return text
    return DEFAULT_MODEL_BACKEND


def resolve_requested_model_backend(explicit: Optional[str] = None) -> str:
    # Compile/runner entrypoints intentionally let the IL-scoped override win.
    return resolve_model_backend_from_candidates(
        explicit,
        os.environ.get("IL_COMPILE_MODEL_BACKEND"),
        os.environ.get("LOCAL_MODEL_BACKEND"),
    )


def resolve_local_ui_requested_model_backend() -> str:
    # Operator/UI paths intentionally let the direct local-model selection win.
    return resolve_model_backend_from_candidates(
        os.environ.get("LOCAL_MODEL_BACKEND"),
        os.environ.get("IL_COMPILE_MODEL_BACKEND"),
    )


def normalize_model_backend_id(raw: Optional[str]) -> Optional[str]:
    text = str(raw or "").strip().lower()
    if not text:
        return DEFAULT_MODEL_BACKEND
    if text in SUPPORTED_MODEL_BACKENDS:
        return text
    return None


def resolve_int_setting(
    *,
    explicit: Optional[int],
    default: int,
    env_names: List[str],
) -> int:
    if explicit is not None:
        return int(explicit)
    for name in env_names:
        raw = os.environ.get(name)
        if raw is None:
            continue
        text = str(raw).strip()
        if not text:
            continue
        try:
            return int(text)
        except ValueError as exc:
            raise ValueError(f"{name} must be an integer, got {raw!r}") from exc
    return default


def _chat_completion_urls(base: str) -> List[str]:
    src = (base or "").rstrip("/")
    if not src:
        src = DEFAULT_OPENAI_COMPAT_API_BASE
    if src.endswith("/chat/completions"):
        src = src[: -len("/chat/completions")].rstrip("/")
    rows = [f"{src}/chat/completions"]
    if src.endswith("/v1"):
        root = src[: -len("/v1")].rstrip("/")
        if root:
            rows.append(f"{root}/chat/completions")
    else:
        rows.append(f"{src}/v1/chat/completions")
    uniq: List[str] = []
    for item in rows:
        if item and item not in uniq:
            uniq.append(item)
    return uniq


class LegacyCallableModelBackendAdapter:
    backend_id = "legacy_callable"

    def __init__(self, adapter: LegacyLLMCallable) -> None:
        self._adapter = adapter

    def invoke(self, request: ModelBackendRequest) -> ModelBackendResponse:
        return ModelBackendResponse(
            raw_text=self._adapter(request.prompt_text, request.model, request.determinism),
            backend_id=self.backend_id,
            target="callable://legacy",
        )


class OpenAICompatModelBackendAdapter:
    backend_id = "openai_compat"

    def __init__(
        self,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_s: Optional[int] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        self.api_base = (
            str(api_base or "").strip()
            or os.environ.get("IL_COMPILE_LLM_API_BASE", "").strip()
            or os.environ.get("OPENAI_API_BASE", "").strip()
            or DEFAULT_OPENAI_COMPAT_API_BASE
        ).rstrip("/")
        self.api_key = (
            str(api_key or "").strip()
            or os.environ.get("IL_COMPILE_LLM_API_KEY", "").strip()
            or os.environ.get("OPENAI_API_KEY", "").strip()
            or "dummy"
        )
        self.timeout_s = resolve_int_setting(
            explicit=timeout_s,
            default=60,
            env_names=["IL_COMPILE_LLM_TIMEOUT_S"],
        )
        self.max_tokens = resolve_int_setting(
            explicit=max_tokens,
            default=1024,
            env_names=["IL_COMPILE_LLM_MAX_TOKENS"],
        )

    def invoke(self, request: ModelBackendRequest) -> ModelBackendResponse:
        local_llama_error = ""
        try:
            from src.local_llm import LocalLlamaCppLLM

            llm = LocalLlamaCppLLM(
                api_base=self.api_base,
                model=request.model,
                api_key=self.api_key,
                temperature=float(request.determinism["temperature"]),
                timeout_s=self.timeout_s,
            )
            resp = llm.complete(
                request.prompt_text,
                max_tokens=self.max_tokens,
                top_p=float(request.determinism["top_p"]),
            )
            text = getattr(resp, "text", "")
            if isinstance(text, str) and text.strip():
                return ModelBackendResponse(
                    raw_text=text,
                    backend_id=self.backend_id,
                    target=self.api_base,
                )
        except Exception as exc:
            local_llama_error = f"{type(exc).__name__}: {exc}"

        metadata = {"local_llama_error": local_llama_error} if local_llama_error else {}
        local_llama_suffix = f"; local_llama_error={local_llama_error}" if local_llama_error else ""

        payload = {
            "model": request.model,
            "temperature": float(request.determinism["temperature"]),
            "top_p": float(request.determinism["top_p"]),
            "messages": [{"role": "user", "content": request.prompt_text}],
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            import requests  # type: ignore

            attempts: List[str] = []
            for url in _chat_completion_urls(self.api_base):
                try:
                    resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout_s)
                except Exception as exc:
                    raise RuntimeError(
                        f"openai-compatible request failed for url={url}: {exc}{local_llama_suffix}"
                    ) from exc
                if resp.status_code == 404:
                    attempts.append(f"{url}:404")
                    continue
                resp.raise_for_status()
                data = resp.json()
                return ModelBackendResponse(
                    raw_text=data["choices"][0]["message"]["content"],
                    backend_id=self.backend_id,
                    target=url,
                    metadata=metadata,
                )
            raise RuntimeError(
                f"openai-compatible endpoint not found for api_base={self.api_base}; attempts={', '.join(attempts) or 'none'}{local_llama_suffix}"
            )
        except ModuleNotFoundError:
            pass

        from urllib import error as urllib_error
        from urllib import request as urllib_request

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        for url in _chat_completion_urls(self.api_base):
            req = urllib_request.Request(url, data=body, headers=headers, method="POST")
            try:
                with urllib_request.urlopen(req, timeout=self.timeout_s) as resp:  # nosec B310
                    raw = resp.read().decode("utf-8")
                data = json.loads(raw)
                return ModelBackendResponse(
                    raw_text=data["choices"][0]["message"]["content"],
                    backend_id=self.backend_id,
                    target=url,
                    metadata=metadata,
                )
            except urllib_error.HTTPError as exc:
                if exc.code == 404:
                    continue
                detail = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"openai-compatible http_error status={exc.code} body={detail[:200]}{local_llama_suffix}"
                ) from exc
            except urllib_error.URLError as exc:
                raise RuntimeError(
                    f"openai-compatible url_error reason={exc.reason}{local_llama_suffix}"
                ) from exc
        raise RuntimeError(
            f"openai-compatible endpoint not found for api_base={self.api_base}{local_llama_suffix}"
        )


def parse_json_object(raw: str) -> Dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        return {}
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("expected JSON object")
    return parsed


def trim_one_line(value: str, limit: int = 200) -> str:
    text = " ".join(str(value or "").split()).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _looks_like_filesystem_path(text: str) -> bool:
    raw = str(text or "").strip()
    return (
        raw.startswith(".")
        or raw.startswith("~")
        or "/" in raw
        or "\\" in raw
        or bool(Path(raw).anchor)
    )


def resolve_gemma_lab_root_path(raw: Optional[str] = None) -> Path:
    text = str(raw or "").strip()
    if text:
        path = Path(text).expanduser()
        if not path.is_absolute():
            path = repo_root() / path
        return path.resolve()
    return (repo_root().parent / "gemma-lab").resolve()


def resolve_gemma_lab_python_path(
    raw: Optional[str] = None,
    gemma_root: Optional[Path] = None,
) -> str:
    root = (gemma_root or resolve_gemma_lab_root_path()).resolve()
    text = str(raw or "").strip()
    if text:
        if not _looks_like_filesystem_path(text):
            return text
        path = Path(text).expanduser()
        if not path.is_absolute():
            path = root / path
        return str(path.resolve())
    return str(root / ".venv" / "bin" / "python")


def resolve_gemma_lab_model_id(raw: Optional[str] = None) -> str:
    text = str(raw or "").strip()
    if text and text not in GENERIC_COMPILE_MODEL_IDS:
        return text
    return os.environ.get("GEMMA_MODEL_ID", "").strip()


def gemma_lab_bridge_script_path(raw: Optional[str] = None) -> str:
    text = str(raw or "").strip()
    if text:
        return str(Path(text).expanduser())
    return str(repo_root() / "scripts" / "gemma_lab_bridge.py")


def invoke_gemma_lab_bridge(
    *,
    mode: str,
    model_id: str,
    messages: Optional[List[Dict[str, Any]]] = None,
    gemma_root: Path,
    python_path: str,
    bridge_script: str,
    timeout_s: int,
    cwd: Optional[Path] = None,
) -> Dict[str, Any]:
    run_cwd = Path(cwd or repo_root()).resolve()
    resolved_gemma_root = gemma_root.expanduser()
    if not resolved_gemma_root.is_absolute():
        resolved_gemma_root = (run_cwd / resolved_gemma_root).resolve()
    resolved_python_path = python_path
    if _looks_like_filesystem_path(python_path):
        python_candidate = Path(python_path).expanduser()
        if not python_candidate.is_absolute():
            python_candidate = (run_cwd / python_candidate).resolve()
        resolved_python_path = str(python_candidate)
    resolved_bridge_script = Path(bridge_script).expanduser()
    if not resolved_bridge_script.is_absolute():
        resolved_bridge_script = (run_cwd / resolved_bridge_script).resolve()

    if not resolved_gemma_root.exists():
        raise RuntimeError(f"gemma-lab root not found: {resolved_gemma_root}")
    if _looks_like_filesystem_path(resolved_python_path) and not Path(resolved_python_path).exists():
        raise RuntimeError(f"gemma-lab python not found: {resolved_python_path}")
    if not resolved_bridge_script.exists():
        raise RuntimeError(f"gemma bridge script not found: {resolved_bridge_script}")

    payload = {"model_id": model_id}
    if mode == "chat":
        payload["messages"] = list(messages or [])

    proc = subprocess.run(
        [
            resolved_python_path,
            str(resolved_bridge_script),
            "--mode",
            mode,
            "--gemma-root",
            str(resolved_gemma_root),
            "--model-id",
            model_id,
        ],
        cwd=str(run_cwd),
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        timeout=timeout_s,
    )
    parsed: Dict[str, Any] = {}
    if proc.stdout.strip():
        try:
            parsed = parse_json_object(proc.stdout)
        except ValueError as exc:
            if proc.returncode == 0:
                detail = trim_one_line(proc.stderr or proc.stdout or str(exc))
                raise RuntimeError(f"gemma-lab bridge returned invalid JSON: {detail}") from exc
            parsed = {}
    if proc.returncode != 0:
        detail = str(parsed.get("error") or proc.stderr or proc.stdout).strip()
        raise RuntimeError(detail or f"gemma-lab bridge failed with exit code {proc.returncode}")
    return parsed


class GemmaLabModelBackendAdapter:
    backend_id = "gemma_lab"

    def __init__(
        self,
        gemma_root: Optional[str] = None,
        python_path: Optional[str] = None,
        bridge_script: Optional[str] = None,
        timeout_s: Optional[int] = None,
    ) -> None:
        root_override = (
            str(gemma_root or "").strip()
            or os.environ.get("IL_COMPILE_GEMMA_LAB_ROOT", "").strip()
            or os.environ.get("GEMMA_LAB_ROOT", "").strip()
        )
        if root_override:
            self.gemma_root = resolve_gemma_lab_root_path(root_override)
        else:
            self.gemma_root = resolve_gemma_lab_root_path()

        python_override = (
            str(python_path or "").strip()
            or os.environ.get("IL_COMPILE_GEMMA_LAB_PYTHON", "").strip()
            or os.environ.get("GEMMA_LAB_PYTHON", "").strip()
        )
        if python_override:
            self.python_path = resolve_gemma_lab_python_path(python_override, self.gemma_root)
        else:
            self.python_path = resolve_gemma_lab_python_path(None, self.gemma_root)

        self.bridge_script = gemma_lab_bridge_script_path(bridge_script)
        self.timeout_s = resolve_int_setting(
            explicit=timeout_s,
            default=600,
            env_names=["IL_COMPILE_GEMMA_LAB_TIMEOUT_S"],
        )

    def invoke(self, request: ModelBackendRequest) -> ModelBackendResponse:
        model_id = resolve_gemma_lab_model_id(request.model)
        payload = invoke_gemma_lab_bridge(
            mode="chat",
            model_id=model_id,
            messages=[{"role": "user", "content": request.prompt_text}],
            gemma_root=self.gemma_root,
            python_path=self.python_path,
            bridge_script=self.bridge_script,
            timeout_s=self.timeout_s,
        )
        if str(payload.get("status") or "").strip().lower() != "ok":
            detail = str(payload.get("error") or "").strip()
            raise RuntimeError(detail or "gemma-lab bridge did not return ok status")
        content = str(payload.get("output_text") or "").strip()
        if not content:
            raise RuntimeError("gemma-lab returned empty content")
        return ModelBackendResponse(
            raw_text=content,
            backend_id=self.backend_id,
            target=str(self.gemma_root),
            metadata={"model_id": str(payload.get("model_id") or model_id)},
        )


def resolve_model_backend_adapter(
    *,
    adapter: Optional[Any] = None,
    backend_id: Optional[str] = None,
) -> ModelBackendAdapter:
    if adapter is not None:
        if isinstance(adapter, ModelBackendAdapter):
            return adapter
        if callable(adapter):
            return LegacyCallableModelBackendAdapter(adapter)
        raise TypeError("adapter must implement invoke() or be a callable")

    requested = resolve_requested_model_backend(backend_id)
    normalized = normalize_model_backend_id(requested)
    if normalized is None:
        raise ValueError(f"unsupported model backend: {requested}")
    if normalized == "gemma_lab":
        return GemmaLabModelBackendAdapter()
    return OpenAICompatModelBackendAdapter()
