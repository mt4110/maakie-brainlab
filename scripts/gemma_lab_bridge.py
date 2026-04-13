#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bridge Maakie Brainlab local-model calls into the sibling gemma-lab runtime."
    )
    parser.add_argument(
        "--mode",
        choices=("probe", "chat"),
        default="chat",
        help="`probe` reports gemma-lab availability, `chat` runs a text generation request.",
    )
    parser.add_argument(
        "--gemma-root",
        default=os.environ.get("GEMMA_LAB_ROOT", ""),
        help="Optional gemma-lab repository root. Defaults to ../gemma-lab from this repo.",
    )
    parser.add_argument(
        "--model-id",
        default=os.environ.get("GEMMA_MODEL_ID", ""),
        help="Optional model id override. Defaults to GEMMA_MODEL_ID or gemma-lab's default.",
    )
    return parser.parse_args()


def resolve_gemma_root(raw: str) -> Path:
    text = (raw or "").strip()
    if text:
        return Path(text).expanduser().resolve()
    return (repo_root().parent / "gemma-lab").resolve()


def load_payload_from_stdin() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("stdin payload must be a JSON object")
    return parsed


def normalize_messages(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        raise ValueError("messages must be a list")
    normalized: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("each message must be an object")
        role = str(item.get("role") or "").strip()
        content = str(item.get("content") or "").strip()
        if not role or not content:
            raise ValueError("each message must include non-empty role/content")
        normalized.append({"role": role, "content": content})
    if not normalized:
        raise ValueError("messages must not be empty")
    return normalized


def add_gemma_paths(root: Path) -> None:
    scripts_dir = root / "scripts"
    if not scripts_dir.exists():
        raise FileNotFoundError(f"gemma-lab scripts directory not found: {scripts_dir}")
    sys.path.insert(0, str(scripts_dir))


def sanitize_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): sanitize_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_json_value(item) for item in value]
    return str(value)


def run_probe(root: Path, model_id_override: str | None) -> dict[str, Any]:
    add_gemma_paths(root)
    from gemma_runtime import model_cache_dir, resolve_model_id

    model_id = (model_id_override or "").strip() or resolve_model_id()
    cache_dir = model_cache_dir(model_id)
    python_path = root / ".venv" / "bin" / "python"
    return {
        "status": "ok",
        "model_id": model_id,
        "cache_dir": str(cache_dir),
        "cache_exists": cache_dir.exists(),
        "root": str(root),
        "python": str(python_path if python_path.exists() else sys.executable),
    }


def run_chat(root: Path, model_id_override: str | None) -> dict[str, Any]:
    add_gemma_paths(root)
    from gemma_runtime import resolve_model_id
    from text_service import run_text_task

    payload = load_payload_from_stdin()
    payload_model_id = str(payload.get("model_id") or "").strip()
    model_id = (model_id_override or payload_model_id).strip() or resolve_model_id()
    messages = normalize_messages(payload.get("messages"))
    result = run_text_task(
        task="chat",
        prompt=payload.get("prompt"),
        system_prompt=payload.get("system_prompt"),
        messages=messages,
        model_id=model_id,
    )
    return {
        "status": "ok",
        "model_id": str(result.get("model_id") or model_id),
        "elapsed_seconds": result.get("elapsed_seconds"),
        "device_info": sanitize_json_value(result.get("device_info")),
        "output_text": str(result.get("output_text") or "").strip(),
    }


def emit(payload: dict[str, Any], exit_code: int = 0) -> int:
    print(json.dumps(payload, ensure_ascii=False))
    return exit_code


def main() -> int:
    args = parse_args()
    root = resolve_gemma_root(args.gemma_root)
    if not root.exists():
        return emit(
            {
                "status": "error",
                "error": f"gemma-lab root not found: {root}",
            },
            exit_code=1,
        )

    try:
        if args.mode == "probe":
            return emit(run_probe(root, args.model_id))
        return emit(run_chat(root, args.model_id))
    except Exception as exc:
        return emit(
            {
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
            },
            exit_code=1,
        )


if __name__ == "__main__":
    raise SystemExit(main())
