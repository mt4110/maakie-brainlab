#!/usr/bin/env python3
"""
S27-02 medium eval wall v2.

Goal:
- Expand medium wall with operations-oriented taxonomy.
- Emit taxonomy-v2 metrics with unknown ratio monitoring.
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


DEFAULT_CONFIG = "docs/ops/S27-02_MEDIUM_EVAL_WALL_V2.toml"
DEFAULT_OUT_DIR = "docs/evidence/s27-02"

REASON_CONFIG_INVALID = "CONFIG_INVALID"
REASON_CASE_SCHEMA_INVALID = "CASE_SCHEMA_INVALID"
REASON_CONTRACT_VIOLATION = "CONTRACT_VIOLATION"
REASON_UNKNOWN_RATIO_HIGH = "UNKNOWN_RATIO_HIGH"


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
    text = rel.as_posix()
    if ".." in Path(text).parts:
        return ""
    return text


def validate_config(cfg: Dict[str, Any]) -> Tuple[bool, str]:
    if str(cfg.get("schema_version") or "") != "s27-medium-eval-wall-v2":
        return False, "schema_version mismatch"
    for key in ("dataset_id", "cases_path", "meta_path", "baseline_cases_path"):
        if not str(cfg.get(key) or "").strip():
            return False, f"{key} missing"

    contract = cfg.get("contract")
    if not isinstance(contract, dict):
        return False, "contract missing"
    for key in ("min_cases", "max_cases", "min_must_answer_true", "min_must_answer_false", "min_must_cite_true"):
        try:
            if int(contract.get(key)) < 0:
                return False, f"contract.{key} must be >=0"
        except Exception:
            return False, f"contract.{key} invalid"
    try:
        unknown_warn = float(contract.get("max_unknown_ratio_warn", 0.2))
        if unknown_warn < 0 or unknown_warn > 1:
            return False, "contract.max_unknown_ratio_warn must be in [0,1]"
    except Exception:
        return False, "contract.max_unknown_ratio_warn invalid"

    tag_min = cfg.get("tag_min_counts")
    if not isinstance(tag_min, dict) or not tag_min:
        return False, "tag_min_counts missing"

    taxonomy_map = cfg.get("taxonomy_map")
    if not isinstance(taxonomy_map, dict) or not taxonomy_map:
        return False, "taxonomy_map missing"
    for key, value in taxonomy_map.items():
        if not str(key).strip():
            return False, "taxonomy_map key invalid"
        if not isinstance(value, list) or not value:
            return False, f"taxonomy_map.{key} invalid"
    return True, ""


def load_cases(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        item = json.loads(line)
        if not isinstance(item, dict):
            raise ValueError(f"line {i}: json object required")
        out.append(item)
    return out


def validate_case_schema(cases: List[Dict[str, Any]]) -> List[str]:
    errs: List[str] = []
    if not cases:
        return ["cases empty"]
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
        exp = case.get("expectation")
        if not isinstance(exp, dict):
            errs.append(f"cases[{idx}].expectation missing")
            continue
        for key in ("must_answer", "must_cite"):
            if key not in exp or not isinstance(exp.get(key), bool):
                errs.append(f"cases[{idx}].expectation.{key} invalid")
        tags = case.get("tags")
        if not isinstance(tags, list) or not tags:
            errs.append(f"cases[{idx}].tags missing")
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

        seen_tags = set()
        for tag in list(case.get("tags") or []):
            name = str(tag).strip()
            if not name or name in seen_tags:
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


def classify_taxonomy(case_tags: List[str], taxonomy_map: Dict[str, List[str]]) -> str:
    tag_set = {str(x).strip().lower() for x in case_tags if str(x).strip()}
    for taxonomy, tag_keys in taxonomy_map.items():
        keys = {str(x).strip().lower() for x in tag_keys if str(x).strip()}
        if tag_set & keys:
            return str(taxonomy)
    return "unknown"


def compute_taxonomy(cases: List[Dict[str, Any]], taxonomy_map: Dict[str, List[str]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {str(k): 0 for k in taxonomy_map.keys()}
    counts["unknown"] = 0
    for case in cases:
        tags = list(case.get("tags") or [])
        name = classify_taxonomy(tags, taxonomy_map)
        counts[name] = int(counts.get(name, 0)) + 1
    total = len(cases)
    unknown = int(counts.get("unknown", 0))
    ratio = 0.0 if total == 0 else round(unknown / float(total), 4)
    return {
        "counts": dict(sorted(counts.items(), key=lambda x: x[0])),
        "unknown_ratio": ratio,
        "total_cases": total,
    }


def validate_contract(dist: Dict[str, Any], contract: Dict[str, Any], tag_min_counts: Dict[str, Any]) -> List[str]:
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
    summary = dict(payload.get("summary", {}))
    dist = dict(payload.get("distribution", {}))
    taxonomy = dict(payload.get("taxonomy", {}))
    lines: List[str] = []
    lines.append("# S27-02 Medium Eval Wall v2 (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload.get('captured_at_utc', '')}`")
    lines.append(f"- Branch: `{payload.get('git', {}).get('branch', '')}`")
    lines.append(f"- HeadSHA: `{payload.get('git', {}).get('head', '')}`")
    lines.append(f"- DatasetID: `{payload.get('dataset_id', '')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- status: `{summary.get('status', '')}`")
    lines.append(f"- reason_code: `{summary.get('reason_code', '')}`")
    lines.append(f"- total_cases: `{dist.get('total_cases', 0)}`")
    lines.append(f"- unknown_ratio: `{taxonomy.get('unknown_ratio', 0.0)}`")
    lines.append("")
    lines.append("## Taxonomy")
    lines.append("")
    for key, value in dict(taxonomy.get("counts", {})).items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S27-02 Medium Eval Wall v2")
    lines.append(f"- status: {summary.get('status', '')}")
    lines.append(f"- reason_code: {summary.get('reason_code', '')}")
    lines.append(f"- total_cases: {dist.get('total_cases', 0)}")
    lines.append(f"- unknown_ratio: {taxonomy.get('unknown_ratio', 0.0)}")
    lines.append(f"- taxonomy_counts: {taxonomy.get('counts', {})}")
    lines.append(f"- artifact: docs/evidence/s27-02/{payload.get('artifact_names', {}).get('json', '')}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def write_failure(repo_root: Path, out_dir: Path, config_path: Path, reason: str, errors: List[str]) -> None:
    payload: Dict[str, Any] = {
        "schema_version": "s27-medium-eval-wall-v2-result-v1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {"branch": git_out(repo_root, ["branch", "--show-current"]), "head": git_out(repo_root, ["rev-parse", "HEAD"])},
        "dataset_id": "",
        "config_path": to_repo_rel(repo_root, config_path),
        "distribution": {"total_cases": 0, "must_answer_true": 0, "must_answer_false": 0, "must_cite_true": 0, "tag_counts": {}},
        "taxonomy": {"counts": {}, "unknown_ratio": 0.0, "total_cases": 0},
        "summary": {"status": "FAIL", "reason_code": reason, "errors": list(errors)},
        "artifact_names": {"json": "medium_eval_wall_v2_latest.json", "md": "medium_eval_wall_v2_latest.md"},
    }
    out_json = out_dir / "medium_eval_wall_v2_latest.json"
    out_md = out_dir / "medium_eval_wall_v2_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="s27-medium-eval-wall-v2", obs_root=args.obs_root)

    config_path = (repo_root / args.config).resolve()
    if not config_path.exists():
        emit("ERROR", f"config missing path={config_path}", events)
        write_failure(repo_root, out_dir, config_path, REASON_CONFIG_INVALID, [f"config missing path={config_path}"])
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"status": "FAIL", "reason_code": REASON_CONFIG_INVALID})
        return 1

    try:
        cfg = _read_toml(config_path)
    except Exception as exc:
        emit("ERROR", f"config parse failed err={exc}", events)
        write_failure(repo_root, out_dir, config_path, REASON_CONFIG_INVALID, [f"config parse failed err={exc}"])
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"status": "FAIL", "reason_code": REASON_CONFIG_INVALID})
        return 1

    ok, reason = validate_config(cfg)
    if not ok:
        emit("ERROR", f"config invalid reason={reason}", events)
        write_failure(repo_root, out_dir, config_path, REASON_CONFIG_INVALID, [reason])
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"status": "FAIL", "reason_code": REASON_CONFIG_INVALID})
        return 1

    cases_path = (repo_root / str(cfg.get("cases_path") or "")).resolve()
    meta_path = (repo_root / str(cfg.get("meta_path") or "")).resolve()
    baseline_path = (repo_root / str(cfg.get("baseline_cases_path") or "")).resolve()
    if not cases_path.exists() or not meta_path.exists():
        msg = f"dataset files missing cases={cases_path.exists()} meta={meta_path.exists()}"
        emit("ERROR", msg, events)
        write_failure(repo_root, out_dir, config_path, REASON_CONFIG_INVALID, [msg])
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"status": "FAIL", "reason_code": REASON_CONFIG_INVALID})
        return 1

    try:
        cases = load_cases(cases_path)
    except Exception as exc:
        emit("ERROR", f"cases parse failed err={exc}", events)
        write_failure(repo_root, out_dir, config_path, REASON_CASE_SCHEMA_INVALID, [f"cases parse failed err={exc}"])
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"status": "FAIL", "reason_code": REASON_CASE_SCHEMA_INVALID})
        return 1

    schema_errs = validate_case_schema(cases)
    if schema_errs:
        for e in schema_errs:
            emit("ERROR", e, events)
        write_failure(repo_root, out_dir, config_path, REASON_CASE_SCHEMA_INVALID, schema_errs)
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"status": "FAIL", "reason_code": REASON_CASE_SCHEMA_INVALID})
        return 1

    dist = compute_distribution(cases)
    taxonomy_map = {str(k): [str(x) for x in list(v)] for k, v in dict(cfg.get("taxonomy_map") or {}).items()}
    taxonomy = compute_taxonomy(cases, taxonomy_map)
    contract = dict(cfg.get("contract") or {})
    tag_min_counts = dict(cfg.get("tag_min_counts") or {})
    contract_errs = validate_contract(dist, contract, tag_min_counts)

    baseline_total = 0
    if baseline_path.exists():
        try:
            baseline_cases = load_cases(baseline_path)
            baseline_total = len(baseline_cases)
        except Exception as exc:
            emit("WARN", f"baseline parse failed err={exc}", events)

    status = "PASS"
    reason_code = ""
    if contract_errs:
        status = "FAIL"
        reason_code = REASON_CONTRACT_VIOLATION
    else:
        unknown_ratio = float(taxonomy.get("unknown_ratio", 0.0))
        max_unknown_warn = float(contract.get("max_unknown_ratio_warn", 0.2))
        if unknown_ratio > max_unknown_warn:
            status = "WARN"
            reason_code = REASON_UNKNOWN_RATIO_HIGH

    if status == "FAIL":
        emit("ERROR", f"medium eval v2 FAIL reason={reason_code}", events)
    elif status == "WARN":
        emit("WARN", f"medium eval v2 WARN reason={reason_code}", events)
    else:
        emit("OK", f"medium eval v2 PASS total_cases={dist.get('total_cases', 0)}", events)

    meta_snapshot: Dict[str, Any] = {}
    try:
        meta_snapshot = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as exc:
        emit("WARN", f"meta parse failed err={exc}", events)

    payload: Dict[str, Any] = {
        "schema_version": "s27-medium-eval-wall-v2-result-v1",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {"branch": git_out(repo_root, ["branch", "--show-current"]), "head": git_out(repo_root, ["rev-parse", "HEAD"])} ,
        "dataset_id": str(cfg.get("dataset_id") or ""),
        "config_path": to_repo_rel(repo_root, config_path),
        "cases_path": to_repo_rel(repo_root, cases_path),
        "meta_path": to_repo_rel(repo_root, meta_path),
        "meta_snapshot": meta_snapshot,
        "distribution": dist,
        "taxonomy": taxonomy,
        "delta_vs_v1": {
            "baseline_cases_path": to_repo_rel(repo_root, baseline_path),
            "baseline_total_cases": baseline_total,
            "total_cases_delta": int(dist.get("total_cases", 0)) - int(baseline_total),
        },
        "contract": contract,
        "tag_min_counts": tag_min_counts,
        "summary": {"status": status, "reason_code": reason_code, "errors": contract_errs},
        "artifact_names": {"json": "medium_eval_wall_v2_latest.json", "md": "medium_eval_wall_v2_latest.md"},
    }

    out_json = out_dir / "medium_eval_wall_v2_latest.json"
    out_md = out_dir / "medium_eval_wall_v2_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={out_json}", events)
    emit("OK", f"artifact_md={out_md}", events)

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"status": status, "reason_code": reason_code, "unknown_ratio": taxonomy.get("unknown_ratio", 0.0)})
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
