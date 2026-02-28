#!/usr/bin/env python3
"""
S31-03: IL formatter CLI.

Modes:
- --check: verify files already match canonical JSON bytes
- --write: rewrite files to canonical JSON bytes
"""

import json
import glob
import re
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple


repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.il_validator import ILCanonicalizer


_GLOB_META_RE = re.compile(r"[*?\[\]]")


def usage() -> str:
    return (
        "python3 scripts/il_fmt.py --check <path_or_glob> [<path_or_glob> ...] "
        "| --write <path_or_glob> [<path_or_glob> ...]"
    )


def parse_args(args: List[str]) -> Tuple[str, List[str], List[str], bool]:
    mode = ""
    patterns: List[str] = []
    errors: List[str] = []

    if "--help" in args or "-h" in args:
        return mode, patterns, errors, True

    i = 0
    while i < len(args):
        token = args[i]
        if token == "--check":
            if mode:
                errors.append("mode already selected")
                i += 1
                continue
            mode = "check"
            i += 1
            while i < len(args) and not args[i].startswith("-"):
                patterns.append(args[i])
                i += 1
        elif token == "--write":
            if mode:
                errors.append("mode already selected")
                i += 1
                continue
            mode = "write"
            i += 1
            while i < len(args) and not args[i].startswith("-"):
                patterns.append(args[i])
                i += 1
        elif token.startswith("-"):
            errors.append(f"unknown option: {token}")
            i += 1
        else:
            errors.append(f"unexpected positional arg: {token}")
            i += 1

    if not mode:
        errors.append("missing required mode (--check or --write)")
    if mode and not patterns:
        errors.append(f"missing paths for --{mode}")

    return mode, patterns, errors, False


def _resolve_path(text: str) -> Path:
    p = Path(text).expanduser()
    if p.is_absolute():
        return p
    return (repo_root / p).resolve()


def _is_glob_pattern(text: str) -> bool:
    return bool(_GLOB_META_RE.search(text))


def _iter_json_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return
    if path.is_dir():
        for item in sorted(path.rglob("*.json")):
            if item.is_file():
                yield item


def resolve_targets(patterns: List[str]) -> List[Path]:
    seen: Set[Path] = set()
    files: List[Path] = []

    for pattern in patterns:
        if _is_glob_pattern(pattern):
            glob_pattern = pattern
            if not Path(pattern).expanduser().is_absolute():
                glob_pattern = str((repo_root / pattern).resolve())
            for match in sorted(glob.glob(glob_pattern, recursive=True)):
                item = Path(match)
                resolved = item.resolve()
                for file_path in _iter_json_files(resolved):
                    rp = file_path.resolve()
                    if rp not in seen:
                        seen.add(rp)
                        files.append(rp)
            continue

        target = _resolve_path(pattern)
        for file_path in _iter_json_files(target):
            rp = file_path.resolve()
            if rp not in seen:
                seen.add(rp)
                files.append(rp)

    return sorted(files)


def _read_json(path: Path) -> Tuple[Optional[object], Optional[str], bytes]:
    try:
        raw_bytes = path.read_bytes()
    except Exception as exc:
        return None, f"read_failed: {exc}", b""

    try:
        text = raw_bytes.decode("utf-8")
    except Exception as exc:
        return None, f"utf8_decode_failed: {exc}", raw_bytes

    try:
        parsed = json.loads(text)
    except Exception as exc:
        return None, f"json_parse_failed: {exc}", raw_bytes

    return parsed, None, raw_bytes


def run(mode: str, patterns: List[str]) -> int:
    targets = resolve_targets(patterns)
    if not targets:
        print("ERROR: no target files found")
        return 1

    changed_count = 0
    failed_count = 0

    for path in targets:
        parsed, read_err, current_bytes = _read_json(path)
        if read_err:
            print(f"ERROR: path={path} reason={read_err}")
            failed_count += 1
            continue
        assert parsed is not None

        try:
            canonical_bytes = ILCanonicalizer.canonicalize(parsed)
        except Exception as exc:
            print(f"ERROR: path={path} reason=canonicalize_failed:{exc}")
            failed_count += 1
            continue

        is_same = current_bytes == canonical_bytes

        if mode == "check":
            if is_same:
                print(f"OK: canonical path={path}")
            else:
                print(f"ERROR: non_canonical path={path}")
                failed_count += 1
            continue

        if is_same:
            print(f"OK: unchanged path={path}")
            continue

        try:
            path.write_bytes(canonical_bytes)
            changed_count += 1
            print(f"OK: formatted path={path}")
        except Exception as exc:
            print(f"ERROR: path={path} reason=write_failed:{exc}")
            failed_count += 1

    print(
        f"OK: il_fmt_summary mode={mode} total={len(targets)} changed={changed_count} failed={failed_count}"
    )
    return 0 if failed_count == 0 else 1


def main(argv: List[str]) -> int:
    mode, patterns, errors, show_help = parse_args(argv)
    if show_help:
        print(f"OK: usage: {usage()}")
        return 0
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        print(f"OK: usage: {usage()}")
        return 1
    return run(mode=mode, patterns=patterns)


if __name__ == "__main__":
    rc = main(sys.argv[1:])
    sys.exit(rc)
