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


def resolve_requested_model_backend(explicit: Optional[str] = None) -> str:
    candidates = [
        explicit,
        os.environ.get("IL_COMPILE_MODEL_BACKEND"),
        os.environ.get("LOCAL_MODEL_BACKEND"),
    ]
    for raw in candidates:
        text = str(raw or "").strip().lower()
        if text:
            return text
    return DEFAULT_MODEL_BACKEND


def normalize_model_backend_id(raw: Optional[str]) -> Optional[str]:
    text = str(raw or "").strip().lower()
    if not text:
        return DEFAULT_MODEL_BACKEND
    if text in SUPPORTED_MODEL_BACKENDS:
        return text
    return None


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
        self.timeout_s = int(
            timeout_s
            if timeout_s is not None
            else os.environ.get("IL_COMPILE_LLM_TIMEOUT_S", "60")
        )
        self.max_tokens = int(
            max_tokens
            if max_tokens is not None
            else os.environ.get("IL_COMPILE_LLM_MAX_TOKENS", "1024")
        )

    def invoke(self, request: ModelBackendRequest) -> ModelBackendResponse:
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
        except Exception:
            pass

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
                resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout_s)
                if resp.status_code == 404:
                    attempts.append(f"{url}:404")
                    continue
                resp.raise_for_status()
                data = resp.json()
                return ModelBackendResponse(
                    raw_text=data["choices"][0]["message"]["content"],
                    backend_id=self.backend_id,
                    target=url,
                )
            raise RuntimeError(
                f"openai-compatible endpoint not found for api_base={self.api_base}; attempts={', '.join(attempts) or 'none'}"
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
                )
            except urllib_error.HTTPError as exc:
                if exc.code == 404:
                    continue
                detail = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"openai-compatible http_error status={exc.code} body={detail[:200]}"
                ) from exc
        raise RuntimeError(f"openai-compatible endpoint not found for api_base={self.api_base}")


def _parse_json_object(raw: str) -> Dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        return {}
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("expected JSON object")
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
            self.gemma_root = Path(root_override).expanduser()
        else:
            self.gemma_root = repo_root().parent / "gemma-lab"

        python_override = (
            str(python_path or "").strip()
            or os.environ.get("IL_COMPILE_GEMMA_LAB_PYTHON", "").strip()
            or os.environ.get("GEMMA_LAB_PYTHON", "").strip()
        )
        if python_override:
            self.python_path = str(Path(python_override).expanduser())
        else:
            self.python_path = str(self.gemma_root / ".venv" / "bin" / "python")

        self.bridge_script = (
            str(bridge_script or "").strip()
            or str(repo_root() / "scripts" / "gemma_lab_bridge.py")
        )
        self.timeout_s = int(
            timeout_s
            if timeout_s is not None
            else os.environ.get("IL_COMPILE_GEMMA_LAB_TIMEOUT_S", "600")
        )

    def invoke(self, request: ModelBackendRequest) -> ModelBackendResponse:
        if not self.gemma_root.exists():
            raise RuntimeError(f"gemma-lab root not found: {self.gemma_root}")
        if os.sep in self.python_path and not Path(self.python_path).exists():
            raise RuntimeError(f"gemma-lab python not found: {self.python_path}")
        if not Path(self.bridge_script).exists():
            raise RuntimeError(f"gemma bridge script not found: {self.bridge_script}")

        proc = subprocess.run(
            [
                self.python_path,
                self.bridge_script,
                "--mode",
                "chat",
                "--gemma-root",
                str(self.gemma_root),
                "--model-id",
                request.model,
            ],
            cwd=str(repo_root()),
            input=json.dumps(
                {
                    "model_id": request.model,
                    "messages": [{"role": "user", "content": request.prompt_text}],
                },
                ensure_ascii=False,
            ),
            text=True,
            capture_output=True,
            timeout=self.timeout_s,
        )
        payload = _parse_json_object(proc.stdout) if proc.stdout.strip() else {}
        if proc.returncode != 0:
            detail = str(payload.get("error") or proc.stderr or proc.stdout).strip()
            raise RuntimeError(detail or f"gemma-lab bridge failed with exit code {proc.returncode}")
        if str(payload.get("status") or "").strip().lower() != "ok":
            detail = str(payload.get("error") or proc.stderr or proc.stdout).strip()
            raise RuntimeError(detail or "gemma-lab bridge did not return ok status")
        content = str(payload.get("output_text") or "").strip()
        if not content:
            raise RuntimeError("gemma-lab returned empty content")
        return ModelBackendResponse(
            raw_text=content,
            backend_id=self.backend_id,
            target=str(self.gemma_root),
            metadata={"model_id": str(payload.get("model_id") or request.model)},
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
