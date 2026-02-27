#!/usr/bin/env python3
"""
S26-02 medium dataset eval wall.

Goal:
- Fix medium dataset schema and case distribution contract.
- Emit stopless evidence (JSON/Markdown) for repeatable checks.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import tomllib  # py3.11+
except Exception:  # pragma: no cover
    tomllib = None

from scripts.ops.obs_contract import DEFAULT_OBS_ROOT, emit, git_out, make_run_context, write_events, write_summary


DEFAULT_CONFIG = "docs/ops/S26-02_MEDIUM_EVAL_WALL.toml"
DEFAULT_OUT_DIR = "docs/evidence/s26-02"
DEFAULT_SEED_MINI_CASES = "data/eval/datasets/rag-eval-wall-v1__seed-mini__v0001/cases.jsonl"

REASON_CONFIG_INVALID = "CONFIG_INVALID"
REASON_CASE_SCHEMA_INVALID = "CASE_SCHEMA_INVALID"
REASON_CONTRACT_VIOLATION = "CONTRACT_VIOLATION"


def _read_toml(path: Path) -> Dict[str, Any]:
    if tomllib is None:
        raise RuntimeError("tomllib unavailable")
    return tomllib.loads(path.read_text(encoding="utf-8"))


def to_repo_rel(repo_root: Path, value: str | Path) -> str:
    p = Path(value).resolve()
    root = repo_root.resolve()
    try:
        rel = p.relative_to(root)
    except ValueError:
        return ""
    rel_text = rel.as_posix()
    if ".." in Path(rel_text).parts:
        return ""
    return rel_text


def validate_config(cfg: Dict[str, Any]) -> Tuple[bool, str]:
    if str(cfg.get("schema_version") or "") != "s26-medium-eval-wall-v1":
        return False, "schema_version mismatch"
    for key in ("dataset_id", "cases_path", "meta_path"):
        if not str(cfg.get(key) or "").strip():
            return False, f"{key} missing"

    contract = cfg.get("contract")
    if not isinstance(contract, dict):
        return False, "contract missing"
    for key in ("min_cases", "max_cases", "min_must_answer_true", "min_must_answer_false", "min_must_cite_true"):
        try:
            if int(contract.get(key)) < 0:
                return False, f"contract.{key} must be >= 0"
        except Exception:
            return False, f"contract.{key} invalid"
    if int(contract.get("max_cases", 0)) <= 0:
        return False, "contract.max_cases must be > 0"

    tag_min = cfg.get("tag_min_counts")
    if not isinstance(tag_min, dict) or not tag_min:
        return False, "tag_min_counts missing"
    for key, value in tag_min.items():
        if not str(key).strip():
            return False, "tag_min_counts key invalid"
        try:
            if int(value) < 0:
                return False, f"tag_min_counts.{key} must be >= 0"
        except Exception:
            return False, f"tag_min_counts.{key} invalid"
    return True, ""


def load_cases(cases_path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for idx, raw in enumerate(cases_path.read_text(encoding="utf-8").splitlines(), start=1):
        text = raw.strip()
        if not text:
            continue
        item = json.loads(text)
        if not isinstance(item, dict):
            raise ValueError(f"line {idx}: json object required")
        rows.append(item)
    return rows


def validate_case_schema(cases: List[Dict[str, Any]]) -> List[str]:
    errs: List[str] = []
    if not cases:
        errs.append("cases empty")
        return errs
    seen = set()
    for idx, case in enumerate(cases, start=1):
        cid = str(case.get("case_id") or "").strip()
        query = str(case.get("query") or "").strip()
        if not cid:
            errs.append(f"cases[{idx}].case_id missing")
            continue
        if cid in seen:
            errs.append(f"cases[{idx}].case_id duplicated")
        seen.add(cid)
        if not query:
            errs.append(f"cases[{idx}].query missing")

        expectation = case.get("expectation")
        if not isinstance(expectation, dict):
            errs.append(f"cases[{idx}].expectation missing")
            continue
        for key in ("must_answer", "must_cite"):
            if key not in expectation:
                errs.append(f"cases[{idx}].expectation.{key} missing")
            elif not isinstance(expectation.get(key), bool):
                errs.append(f"cases[{idx}].expectation.{key} invalid")

        tags = case.get("tags")
        if not isinstance(tags, list) or not tags:
            errs.append(f"cases[{idx}].tags missing")
        else:
            for tag in tags:
                if not str(tag).strip():
                    errs.append(f"cases[{idx}].tags has blank entry")
    return errs


def compute_distribution(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    tag_counts: Dict[str, int] = {}
    must_answer_true = 0
    must_answer_false = 0
    must_cite_true = 0

    for case in cases:
        exp = dict(case.get("expectation") or {})
        if bool(exp.get("must_answer")):
            must_answer_true += 1
        else:
            must_answer_false += 1
        if bool(exp.get("must_cite")):
            must_cite_true += 1

        # Count each tag at most once per case to avoid inflated coverage.
        seen_tags = set()
        for tag in list(case.get("tags") or []):
            name = str(tag).strip()
            if not name:
                continue
            if name in seen_tags:
                continue
            seen_tags.add(name)
            tag_counts[name] = int(tag_counts.get(name, 0)) + 1

    return {
        "total_cases": len(cases),
        "must_answer_true": must_answer_true,
        "must_answer_false": must_answer_false,
        "must_cite_true": must_cite_true,
        "tag_counts": dict(sorted(tag_counts.items(), key=lambda x: x[0])),
    }


def validate_contract(
    dist: Dict[str, Any],
    contract: Dict[str, Any],
    tag_min_counts: Dict[str, Any],
) -> List[str]:
    errs: List[str] = []
    total = int(dist.get("total_cases", 0))
    if total < int(contract.get("min_cases", 0)):
        errs.append(f"total_cases below min: {total}")
    if total > int(contract.get("max_cases", 0)):
        errs.append(f"total_cases over max: {total}")
    if int(dist.get("must_answer_true", 0)) < int(contract.get("min_must_answer_true", 0)):
        errs.append("must_answer_true below min")
    if int(dist.get("must_answer_false", 0)) < int(contract.get("min_must_answer_false", 0)):
        errs.append("must_answer_false below min")
    if int(dist.get("must_cite_true", 0)) < int(contract.get("min_must_cite_true", 0)):
        errs.append("must_cite_true below min")

    got_tags = dict(dist.get("tag_counts", {}))
    for tag, min_count_raw in dict(tag_min_counts).items():
        min_count = int(min_count_raw)
        have = int(got_tags.get(str(tag), 0))
        if have < min_count:
            errs.append(f"tag {tag} below min: {have} < {min_count}")
    return errs


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    dist = payload.get("distribution", {})
    delta = payload.get("delta_vs_seed_mini", {})
    lines: List[str] = []
    lines.append("# S26-02 Medium Eval Wall (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload.get('captured_at_utc', '')}`")
    lines.append(f"- Branch: `{payload.get('git', {}).get('branch', '')}`")
    lines.append(f"- HeadSHA: `{payload.get('git', {}).get('head', '')}`")
    lines.append(f"- DatasetID: `{payload.get('dataset_id', '')}`")
    lines.append(f"- Config: `{payload.get('config_path', '')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- overall_status: `{summary.get('status', '')}`")
    lines.append(f"- reason_code: `{summary.get('reason_code', '')}`")
    lines.append(f"- total_cases: `{dist.get('total_cases', 0)}`")
    lines.append(f"- must_answer_true: `{dist.get('must_answer_true', 0)}`")
    lines.append(f"- must_answer_false: `{dist.get('must_answer_false', 0)}`")
    lines.append(f"- must_cite_true: `{dist.get('must_cite_true', 0)}`")
    lines.append(f"- delta_total_vs_seed_mini: `{delta.get('total_cases_delta', 0)}`")
    lines.append("")
    lines.append("## Tag Distribution")
    lines.append("")
    for tag, count in dict(dist.get("tag_counts", {})).items():
        lines.append(f"- {tag}: `{count}`")
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S26-02 Medium Eval Wall")
    lines.append(f"- status: {summary.get('status', '')}")
    lines.append(f"- reason_code: {summary.get('reason_code', '')}")
    lines.append(f"- total_cases: {dist.get('total_cases', 0)}")
    lines.append(f"- must_answer_true_false: {dist.get('must_answer_true', 0)}/{dist.get('must_answer_false', 0)}")
    lines.append(f"- must_cite_true: {dist.get('must_cite_true', 0)}")
    lines.append(f"- delta_total_vs_seed_mini: {delta.get('total_cases_delta', 0)}")
    lines.append(f"- artifact: docs/evidence/s26-02/{payload.get('artifact_names', {}).get('json', '')}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def write_failure_artifacts(
    *,
    repo_root: Path,
    out_dir: Path,
    config_path: Path,
    reason_code: str,
    errors: List[str],
) -> None:
    payload: Dict[str, Any] = {
        "schema_version": "s26-medium-eval-wall-result-v1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "dataset_id": "",
        "config_path": to_repo_rel(repo_root, config_path),
        "cases_path": "",
        "meta_path": "",
        "meta_snapshot": {},
        "distribution": {
            "total_cases": 0,
            "must_answer_true": 0,
            "must_answer_false": 0,
            "must_cite_true": 0,
            "tag_counts": {},
        },
        "delta_vs_seed_mini": {
            "seed_mini_cases_path": "",
            "seed_mini_total_cases": 0,
            "total_cases_delta": 0,
        },
        "contract": {},
        "tag_min_counts": {},
        "summary": {
            "status": "FAIL",
            "reason_code": reason_code,
            "errors": list(errors),
        },
        "artifact_names": {"json": "medium_eval_wall_latest.json", "md": "medium_eval_wall_latest.md"},
    }
    json_path = out_dir / "medium_eval_wall_latest.json"
    md_path = out_dir / "medium_eval_wall_latest.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(build_markdown(payload), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="s26-medium-eval-wall", obs_root=args.obs_root)

    config_path = (repo_root / args.config).resolve()
    if not config_path.exists():
        emit("ERROR", f"config missing path={config_path}", events)
        write_failure_artifacts(
            repo_root=repo_root,
            out_dir=out_dir,
            config_path=config_path,
            reason_code=REASON_CONFIG_INVALID,
            errors=[f"config missing path={config_path}"],
        )
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"stop": 1, "reason_code": REASON_CONFIG_INVALID})
        return 1

    try:
        cfg = _read_toml(config_path)
    except Exception as exc:
        emit("ERROR", f"config parse failed err={exc}", events)
        write_failure_artifacts(
            repo_root=repo_root,
            out_dir=out_dir,
            config_path=config_path,
            reason_code=REASON_CONFIG_INVALID,
            errors=[f"config parse failed err={exc}"],
        )
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"stop": 1, "reason_code": REASON_CONFIG_INVALID})
        return 1
    ok, why = validate_config(cfg)
    if not ok:
        emit("ERROR", f"config invalid reason={why}", events)
        write_failure_artifacts(
            repo_root=repo_root,
            out_dir=out_dir,
            config_path=config_path,
            reason_code=REASON_CONFIG_INVALID,
            errors=[f"config invalid reason={why}"],
        )
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"stop": 1, "reason_code": REASON_CONFIG_INVALID})
        return 1
    emit("OK", f"config={config_path}", events)

    cases_path = (repo_root / str(cfg.get("cases_path") or "")).resolve()
    meta_path = (repo_root / str(cfg.get("meta_path") or "")).resolve()
    if not cases_path.exists():
        emit("ERROR", f"cases missing path={cases_path}", events)
        write_failure_artifacts(
            repo_root=repo_root,
            out_dir=out_dir,
            config_path=config_path,
            reason_code=REASON_CONFIG_INVALID,
            errors=[f"cases missing path={cases_path}"],
        )
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"stop": 1, "reason_code": REASON_CONFIG_INVALID})
        return 1
    if not meta_path.exists():
        emit("ERROR", f"meta missing path={meta_path}", events)
        write_failure_artifacts(
            repo_root=repo_root,
            out_dir=out_dir,
            config_path=config_path,
            reason_code=REASON_CONFIG_INVALID,
            errors=[f"meta missing path={meta_path}"],
        )
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"stop": 1, "reason_code": REASON_CONFIG_INVALID})
        return 1

    try:
        cases = load_cases(cases_path)
    except Exception as exc:
        emit("ERROR", f"cases parse failed err={exc}", events)
        write_failure_artifacts(
            repo_root=repo_root,
            out_dir=out_dir,
            config_path=config_path,
            reason_code=REASON_CASE_SCHEMA_INVALID,
            errors=[f"cases parse failed err={exc}"],
        )
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"stop": 1, "reason_code": REASON_CASE_SCHEMA_INVALID})
        return 1

    schema_errs = validate_case_schema(cases)
    if schema_errs:
        for item in schema_errs:
            emit("ERROR", item, events)
        write_failure_artifacts(
            repo_root=repo_root,
            out_dir=out_dir,
            config_path=config_path,
            reason_code=REASON_CASE_SCHEMA_INVALID,
            errors=list(schema_errs),
        )
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"stop": 1, "reason_code": REASON_CASE_SCHEMA_INVALID})
        return 1

    dist = compute_distribution(cases)
    seed_mini_dist: Dict[str, Any] = {}
    seed_mini_cases_path = (repo_root / DEFAULT_SEED_MINI_CASES).resolve()
    if seed_mini_cases_path.exists():
        try:
            seed_mini_cases = load_cases(seed_mini_cases_path)
            if not validate_case_schema(seed_mini_cases):
                seed_mini_dist = compute_distribution(seed_mini_cases)
        except Exception as exc:
            emit("WARN", f"seed-mini parse failed err={exc}", events)
    delta_vs_seed_mini = {
        "seed_mini_cases_path": to_repo_rel(repo_root, seed_mini_cases_path),
        "seed_mini_total_cases": int(seed_mini_dist.get("total_cases", 0)),
        "total_cases_delta": int(dist.get("total_cases", 0)) - int(seed_mini_dist.get("total_cases", 0)),
    }
    contract = dict(cfg.get("contract", {}))
    tag_min_counts = dict(cfg.get("tag_min_counts", {}))
    contract_errs = validate_contract(dist, contract, tag_min_counts)
    for item in contract_errs:
        emit("ERROR", item, events)

    status = "PASS" if not contract_errs else "FAIL"
    reason_code = "" if not contract_errs else REASON_CONTRACT_VIOLATION
    if status == "PASS":
        emit("OK", f"dataset contract passed total_cases={dist.get('total_cases', 0)}", events)

    meta_json: Dict[str, Any] = {}
    try:
        meta_json = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as exc:
        emit("WARN", f"dataset.meta parse failed err={exc}", events)

    payload: Dict[str, Any] = {
        "schema_version": "s26-medium-eval-wall-result-v1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {
            "branch": git_out(repo_root, ["branch", "--show-current"]),
            "head": git_out(repo_root, ["rev-parse", "HEAD"]),
        },
        "dataset_id": str(cfg.get("dataset_id") or ""),
        "config_path": to_repo_rel(repo_root, config_path),
        "cases_path": to_repo_rel(repo_root, cases_path),
        "meta_path": to_repo_rel(repo_root, meta_path),
        "meta_snapshot": meta_json,
        "distribution": dist,
        "delta_vs_seed_mini": delta_vs_seed_mini,
        "contract": contract,
        "tag_min_counts": tag_min_counts,
        "summary": {
            "status": status,
            "reason_code": reason_code,
            "errors": contract_errs,
        },
        "artifact_names": {"json": "medium_eval_wall_latest.json", "md": "medium_eval_wall_latest.md"},
    }

    json_path = out_dir / "medium_eval_wall_latest.json"
    md_path = out_dir / "medium_eval_wall_latest.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={json_path}", events)
    emit("OK", f"artifact_md={md_path}", events)

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"status": status, "reason_code": reason_code})
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
