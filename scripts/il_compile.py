"""
S23-03: Natural language -> IL compile entrypoint (minimal, deterministic).

This script is stopless:
- no sys.exit
- logs with OK:/ERROR:/SKIP:
- writes report/error artifacts for audit
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts.obs_writer import OBSWriter
from src.il_compile import DEFAULT_MODEL, DEFAULT_PROVIDER, compile_request_bundle


def _resolve_out_dir(out_dir: Optional[str]) -> Optional[Path]:
    if not out_dir:
        return None
    candidate = Path(out_dir).expanduser()
    if candidate.is_absolute():
        return candidate
    return (repo_root / candidate).resolve()


def _usage() -> str:
    return (
        "python3 scripts/il_compile.py --request <request_json> --out <out_dir> "
        "[--model <model_name>] [--provider <rule_based|local_llm>] [--seed <int>] [--no-fallback]"
    )


def _parse_args(
    args: List[str],
) -> Tuple[Optional[str], Optional[str], str, str, Optional[int], bool, List[str], bool]:
    request_path: Optional[str] = None
    out_dir: Optional[str] = None
    model = DEFAULT_MODEL
    provider = DEFAULT_PROVIDER
    seed: Optional[int] = None
    allow_fallback = True
    errors: List[str] = []

    if "--help" in args or "-h" in args:
        return request_path, out_dir, model, provider, seed, allow_fallback, errors, True

    i = 0
    while i < len(args):
        token = args[i]
        if token == "--request":
            if i + 1 >= len(args):
                errors.append("missing value for --request")
                i += 1
                continue
            request_path = args[i + 1]
            i += 2
        elif token == "--out":
            if i + 1 >= len(args):
                errors.append("missing value for --out")
                i += 1
                continue
            out_dir = args[i + 1]
            i += 2
        elif token == "--model":
            if i + 1 >= len(args):
                errors.append("missing value for --model")
                i += 1
                continue
            model = args[i + 1]
            i += 2
        elif token == "--provider":
            if i + 1 >= len(args):
                errors.append("missing value for --provider")
                i += 1
                continue
            provider = args[i + 1]
            i += 2
        elif token == "--seed":
            if i + 1 >= len(args):
                errors.append("missing value for --seed")
                i += 1
                continue
            raw = args[i + 1]
            try:
                seed = int(raw)
            except Exception:
                errors.append(f"invalid --seed: {raw}")
            i += 2
        elif token == "--no-fallback":
            allow_fallback = False
            i += 1
        elif token.startswith("-"):
            errors.append(f"unknown option: {token}")
            i += 1
        else:
            errors.append(f"unexpected positional arg: {token}")
            i += 1

    if request_path is None:
        errors.append("missing required --request")
    return request_path, out_dir, model, provider, seed, allow_fallback, errors, False


def _read_json(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), None
    except Exception as exc:
        return None, str(exc)


def _write_text(path: Path, text: str, obs: OBSWriter) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except Exception as exc:
        obs.log("ERROR", phase="write_file", path=str(path), reason=str(exc))


def _write_json(path: Path, data: Dict[str, Any], obs: OBSWriter) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
    except Exception as exc:
        obs.log("ERROR", phase="write_file", path=str(path), reason=str(exc))


def run_il_compile(
    request_path: str,
    out_dir: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    provider: str = DEFAULT_PROVIDER,
    seed: Optional[int] = None,
    allow_fallback: bool = True,
) -> int:
    obs = OBSWriter("il_compile", repo_root=repo_root)
    resolved_out = _resolve_out_dir(out_dir)
    if resolved_out is not None:
        obs.obs_dir = resolved_out

    obs.log("OK", phase="boot", obs_format="v1", obs_dir=str(obs.obs_dir))
    obs.create_dir()

    request_file = Path(request_path)
    request_data: Optional[Dict[str, Any]] = None
    input_errors: List[Dict[str, Any]] = []

    if not request_file.exists():
        obs.log("ERROR", phase="input", reason=f"file_not_found: {request_file}", STOP=1)
        input_errors.append(
            {
                "code": "E_INPUT",
                "message": f"request file not found: {request_file}",
                "path": "/request",
                "retriable": False,
            }
        )
    else:
        request_data, read_err = _read_json(request_file)
        if read_err:
            obs.log("ERROR", phase="input", reason=f"json_load_failed: {read_err}", STOP=1)
            input_errors.append(
                {
                    "code": "E_INPUT",
                    "message": f"failed to read request json: {read_err}",
                    "path": "/request",
                    "retriable": False,
                }
            )

    bundle: Dict[str, Any]
    if request_data is not None and obs.stop == 0:
        obs.log("OK", phase="compile", step="start")
        bundle = compile_request_bundle(
            request_data,
            model=model,
            seed_override=seed,
            provider=provider,
            allow_fallback=allow_fallback,
        )
        if bundle["status"] == "OK":
            obs.log("OK", phase="compile", step="success")
        else:
            obs.log("ERROR", phase="compile", reason=f"errors={len(bundle['errors'])}", STOP=1)
    else:
        bundle = {
            "status": "ERROR",
            "normalized_request": {},
            "prompt_text": "SYSTEM: compile request failed before normalization\n",
            "raw_response_text": "RULE_BASED_COMPILER: no IL output",
            "compiled_output": None,
            "canonical_bytes": None,
            "errors": input_errors,
            "report": {
                "schema": "IL_COMPILE_REPORT_v1",
                "status": "ERROR",
                "error_count": len(input_errors),
                "determinism": {"temperature": 0.0, "top_p": 1.0, "seed": seed if seed is not None else 7, "stream": False},
                "prompt_template_id": "il_compile_prompt_v1",
                "model": model,
                "provider_requested": provider,
                "provider_selected": provider,
                "fallback_used": False,
            },
        }

    # Always emit auditable artifacts.
    _write_json(obs.obs_dir / "il.compile.request.normalized.json", bundle["normalized_request"], obs)
    _write_text(obs.obs_dir / "il.compile.prompt.txt", bundle["prompt_text"], obs)
    _write_text(obs.obs_dir / "il.compile.raw_response.txt", bundle["raw_response_text"], obs)
    _write_json(obs.obs_dir / "il.compile.report.json", bundle["report"], obs)

    if bundle["status"] == "OK" and bundle["compiled_output"] is not None:
        _write_json(obs.obs_dir / "il.compiled.json", bundle["compiled_output"], obs)
        canonical = bundle["canonical_bytes"] or b""
        try:
            with open(obs.obs_dir / "il.compiled.canonical.json", "wb") as f:
                f.write(canonical)
        except Exception as exc:
            obs.log("ERROR", phase="write_file", path="il.compiled.canonical.json", reason=str(exc), STOP=1)
    else:
        _write_json(obs.obs_dir / "il.compile.error.json", {"errors": bundle["errors"]}, obs)

    obs.log("OK", phase="end", STOP=obs.stop)
    return obs.stop


def main(args: List[str]) -> int:
    request_path, out_dir, model, provider, seed, allow_fallback, arg_errors, show_help = _parse_args(args)
    if show_help:
        print(f"OK: usage: {_usage()}")
        return 0
    if arg_errors:
        for err in arg_errors:
            print(f"ERROR: {err}")
        print(f"OK: usage: {_usage()}")
        return 1
    return run_il_compile(
        request_path=request_path or "",
        out_dir=out_dir,
        model=model,
        provider=provider,
        seed=seed,
        allow_fallback=allow_fallback,
    )


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception as exc:
        print(f"ERROR: il_compile unexpected exception: {exc}")
