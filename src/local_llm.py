from __future__ import annotations

import requests
from typing import Any, List

from llama_index.core.llms import CustomLLM, LLMMetadata

# ---- LlamaIndex version compatibility (types moved across versions) ----
try:
    from llama_index.core.base.llms.types import (
        ChatMessage,
        ChatResponse,
        MessageRole,
        CompletionResponse,
    )
except Exception:
    from llama_index.core.llms.types import (
        ChatMessage,
        ChatResponse,
        MessageRole,
        CompletionResponse,
    )

# re-export for convenience in quick tests
__all__ = ["LocalLlamaCppLLM", "ChatMessage", "ChatResponse", "MessageRole"]


def _chat_completion_candidates(api_base: str) -> list[str]:
    base = (api_base or "").rstrip("/")
    if not base:
        base = "http://127.0.0.1:11434/v1"
    if base.endswith("/chat/completions"):
        base = base[: -len("/chat/completions")].rstrip("/")

    candidates = [f"{base}/chat/completions"]
    if base.endswith("/v1"):
        root = base[: -len("/v1")].rstrip("/")
        if root:
            candidates.append(f"{root}/chat/completions")
    else:
        candidates.append(f"{base}/v1/chat/completions")

    uniq: list[str] = []
    for item in candidates:
        if item and item not in uniq:
            uniq.append(item)
    return uniq


class LocalLlamaCppLLM(CustomLLM):
    """
    Minimal OpenAI-compatible chat client for llama.cpp server.
    Deterministic & portable. No OpenAI model-name validation.
    """

    # Pydantic fields (important!)
    api_base: str
    model: str
    api_key: str = "dummy"
    temperature: float = 0.0
    context_window: int = 4096
    timeout_s: int = 600

    def __init__(
        self,
        api_base: str,
        model: str,
        api_key: str = "dummy",
        temperature: float = 0.0,
        context_window: int = 4096,
        timeout_s: int = 600,
    ) -> None:
        super().__init__(
            api_base=api_base.rstrip("/"),
            model=model,
            api_key=api_key,
            temperature=temperature,
            context_window=context_window,
            timeout_s=timeout_s,
        )

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            context_window=self.context_window,
            num_output=256,
            model_name=self.model,
            is_chat_model=True,
        )

    def chat(self, messages: List[ChatMessage], **kwargs: Any) -> ChatResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [],
        }

        for m in messages:
            role = getattr(getattr(m, "role", None), "value", None) or getattr(m, "role", None) or "user"
            payload["messages"].append({"role": str(role), "content": m.content})

        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]

        headers = {"Content-Type": "application/json"}
        # llama.cpp は通常認証しないが、クライアント側が要求することがあるのでダミーでも送る
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        attempts: list[str] = []
        for url in _chat_completion_candidates(self.api_base):
            r = requests.post(url, json=payload, headers=headers, timeout=self.timeout_s)
            if r.status_code == 404:
                attempts.append(f"{url}:404")
                continue
            r.raise_for_status()
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            return ChatResponse(message=ChatMessage(role=MessageRole.ASSISTANT, content=content))

        attempts_text = ", ".join(attempts) if attempts else "no_attempts"
        raise RuntimeError(
            f"openai-compatible chat endpoint not found for api_base={self.api_base}; attempts={attempts_text}"
        )

    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        resp = self.chat([ChatMessage(role=MessageRole.USER, content=prompt)], **kwargs)
        return CompletionResponse(text=resp.message.content)

    # required by CustomLLM (even if you don't use streaming)
    def stream_complete(self, prompt: str, **kwargs: Any):
        yield self.complete(prompt, **kwargs)

    def stream_chat(self, messages: List[ChatMessage], **kwargs: Any):
        yield self.chat(messages, **kwargs)
