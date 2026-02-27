#!/usr/bin/env python3
"""
S29-02 taxonomy feedback pipeline integration v2.

Goal:
- Reduce taxonomy unknown by extracting candidate cases and concrete collection actions.
- Export integration-ready records for data generation pipeline consumption.
- Assign owner/action metadata for triage and execution.
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


DEFAULT_CONFIG = "docs/ops/S29-02_TAXONOMY_PIPELINE_INTEGRATION.toml"
DEFAULT_OUT_DIR = "docs/evidence/s29-02"
DEFAULT_MEDIUM_JSON = "docs/evidence/s27-02/medium_eval_wall_v2_latest.json"
DEFAULT_PIPELINE_JSONL = "docs/evidence/s29-02/taxonomy_pipeline_candidates_latest.jsonl"

REASON_CONFIG_INVALID = "CONFIG_INVALID"
REASON_INPUT_MISSING = "INPUT_MISSING"
REASON_UNKNOWN_RATIO_ABOVE_TARGET = "UNKNOWN_RATIO_ABOVE_TARGET"
REASON_PIPELINE_WRITE_FAILED = "PIPELINE_WRITE_FAILED"

DEFAULT_OWNER_BY_TAXONOMY = {
    "provider": "ml-platform",
    "network": "sre-network",
    "schema": "data-platform",
    "timeout": "runtime-core",
    "unknown": "ops-triage",
}


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


def read_json_if_exists(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def load_cases(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        obj = json.loads(line)
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def suggest_taxonomy(tags: List[str], query: str) -> str:
    low_tags = {str(x).strip().lower() for x in tags if str(x).strip()}
    if "provider" in low_tags:
        return "provider"
    if "network" in low_tags:
        return "network"
    if "schema" in low_tags:
        return "schema"
    if "timeout" in low_tags:
        return "timeout"

    q = str(query or "").lower()
    if "timeout" in q or "slow" in q:
        return "timeout"
    if "http" in q or "network" in q or "dns" in q:
        return "network"
    if "schema" in q or "json" in q or "field" in q:
        return "schema"
    if "provider" in q or "model" in q or "api key" in q:
        return "provider"
    return "unknown"


def build_collection_actions(candidates: List[Dict[str, Any]], max_actions: int) -> List[str]:
    grouped: Dict[str, int] = {}
    for row in candidates:
        tax = str(row.get("suggested_taxonomy") or "unknown")
        grouped[tax] = int(grouped.get(tax, 0)) + 1
    actions: List[str] = []
    for tax, cnt in sorted(grouped.items(), key=lambda x: (-x[1], x[0])):
        actions.append(f"Collect at least {cnt} additional labeled cases for taxonomy '{tax}'.")
    if candidates:
        actions.append("Promote top unknown candidates to incident triage backlog and assign owner.")
    return actions[: max(1, int(max_actions))]


def assign_owner(taxonomy: str, owner_map: Dict[str, str]) -> str:
    key = str(taxonomy or "unknown").strip().lower() or "unknown"
    return str(owner_map.get(key, owner_map.get("unknown", "ops-triage")))


def build_structured_actions(candidates: List[Dict[str, Any]], owner_map: Dict[str, str], max_actions: int) -> List[Dict[str, Any]]:
    grouped: Dict[str, int] = {}
    for row in candidates:
        tax = str(row.get("suggested_taxonomy") or "unknown")
        grouped[tax] = int(grouped.get(tax, 0)) + 1
    out: List[Dict[str, Any]] = []
    for tax, cnt in sorted(grouped.items(), key=lambda x: (-x[1], x[0])):
        out.append(
            {
                "taxonomy": tax,
                "owner": assign_owner(tax, owner_map),
                "action": "collect_labeled_cases",
                "target_cases": cnt,
            }
        )
        if len(out) >= max(1, int(max_actions)):
            break
    return out


def candidate_priority(row: Dict[str, Any], known_tags: set[str]) -> Tuple[int, int, str]:
    tags = [str(x).strip().lower() for x in list(row.get("tags") or []) if str(x).strip()]
    unknown_tag_count = sum(1 for t in tags if t not in known_tags and t != "unknown")
    query_len = len(str(row.get("query") or ""))
    case_id = str(row.get("case_id") or "")
    return (unknown_tag_count, query_len, case_id)


def dedupe_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for row in candidates:
        cid = str(row.get("case_id") or "").strip()
        key = cid or json.dumps(row, sort_keys=True, ensure_ascii=False)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def build_pipeline_records(candidates: List[Dict[str, Any]], limit: int, owner_map: Dict[str, str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for idx, row in enumerate(candidates[: max(0, int(limit))]):
        tax = str(row.get("suggested_taxonomy") or "unknown")
        out.append(
            {
                "record_id": f"s29-taxonomy-{idx+1:04d}",
                "source_thread": "S29-02",
                "case_id": str(row.get("case_id") or ""),
                "query": str(row.get("query") or ""),
                "suggested_taxonomy": tax,
                "tags": list(row.get("tags") or []),
                "owner": assign_owner(tax, owner_map),
                "next_action": "collect_labeled_cases",
            }
        )
    return out


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(row, ensure_ascii=False) for row in rows]
    text = ("\n".join(lines) + "\n") if lines else ""
    path.write_text(text, encoding="utf-8")


def validate_config(cfg: Dict[str, Any]) -> Tuple[bool, str]:
    schema_version = str(cfg.get("schema_version") or "")
    if schema_version not in {"s29-taxonomy-pipeline-integration-v1", "s29-taxonomy-pipeline-integration-v2"}:
        return False, "schema_version mismatch"
    if not str(cfg.get("cases_path") or "").strip():
        return False, "cases_path missing"
    if not isinstance(cfg.get("known_tags"), list) or not list(cfg.get("known_tags") or []):
        return False, "known_tags missing"
    try:
        target = float(cfg.get("unknown_ratio_target", 0.1))
        if target < 0 or target > 1:
            return False, "unknown_ratio_target must be in [0,1]"
    except Exception:
        return False, "unknown_ratio_target invalid"
    return True, ""


def build_markdown(payload: Dict[str, Any]) -> str:
    summary = dict(payload.get("summary", {}))
    metrics = dict(payload.get("metrics", {}))
    pipeline = dict(payload.get("pipeline", {}))
    lines: List[str] = []
    lines.append("# S29-02 Taxonomy Pipeline Integration v2 (Latest)")
    lines.append("")
    lines.append(f"- CapturedAtUTC: `{payload.get('captured_at_utc', '')}`")
    lines.append(f"- Branch: `{payload.get('git', {}).get('branch', '')}`")
    lines.append(f"- HeadSHA: `{payload.get('git', {}).get('head', '')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- status: `{summary.get('status', '')}`")
    lines.append(f"- reason_code: `{summary.get('reason_code', '')}`")
    lines.append(f"- unknown_ratio: `{metrics.get('unknown_ratio', 0.0)}`")
    lines.append(f"- candidate_count: `{metrics.get('candidate_count', 0)}`")
    lines.append(f"- pipeline_records: `{pipeline.get('record_count', 0)}`")
    lines.append(f"- action_count: `{len(list(payload.get('collection_actions_v2', [])))}`")
    lines.append(f"- pipeline_jsonl: `{pipeline.get('jsonl', '')}`")
    lines.append("")
    lines.append("## Collection Actions")
    lines.append("")
    for item in list(payload.get("collection_actions", [])):
        lines.append(f"- {item}")
    if not payload.get("collection_actions"):
        lines.append("- none")
    lines.append("")
    lines.append("## PR Body Snippet")
    lines.append("")
    lines.append("```md")
    lines.append("### S29-02 Taxonomy Pipeline Integration v2")
    lines.append(f"- status: {summary.get('status', '')}")
    lines.append(f"- reason_code: {summary.get('reason_code', '')}")
    lines.append(f"- unknown_ratio: {metrics.get('unknown_ratio', 0.0)}")
    lines.append(f"- candidate_count: {metrics.get('candidate_count', 0)}")
    lines.append(f"- pipeline_records: {pipeline.get('record_count', 0)}")
    lines.append(f"- action_count: {len(list(payload.get('collection_actions_v2', [])))}")
    lines.append(f"- artifact: docs/evidence/s29-02/{payload.get('artifact_names', {}).get('json', '')}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--obs-root", default=DEFAULT_OBS_ROOT)
    parser.add_argument("--medium-json", default=DEFAULT_MEDIUM_JSON)
    parser.add_argument("--pipeline-jsonl", default=DEFAULT_PIPELINE_JSONL)
    args = parser.parse_args()

    repo_root = Path(git_out(Path.cwd(), ["rev-parse", "--show-toplevel"]) or Path.cwd()).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir, meta, events = make_run_context(repo_root, tool="s29-taxonomy-pipeline-integration", obs_root=args.obs_root)

    config_path = (repo_root / str(args.config)).resolve()
    if not config_path.exists():
        emit("ERROR", f"config missing path={config_path}", events)
        payload = {
            "schema_version": "s29-taxonomy-pipeline-integration-v1",
            "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "git": {"branch": git_out(repo_root, ["branch", "--show-current"]), "head": git_out(repo_root, ["rev-parse", "HEAD"])},
            "summary": {"status": "FAIL", "reason_code": REASON_CONFIG_INVALID},
            "metrics": {"unknown_ratio": 0.0, "candidate_count": 0},
            "collection_actions": [],
            "artifact_names": {"json": "taxonomy_pipeline_integration_latest.json", "md": "taxonomy_pipeline_integration_latest.md"},
        }
        out_json = out_dir / "taxonomy_pipeline_integration_latest.json"
        out_md = out_dir / "taxonomy_pipeline_integration_latest.md"
        out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        out_md.write_text(build_markdown(payload), encoding="utf-8")
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"status": "FAIL", "reason_code": REASON_CONFIG_INVALID})
        return 1

    try:
        cfg = _read_toml(config_path)
    except Exception as exc:
        emit("ERROR", f"config parse failed err={exc}", events)
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"status": "FAIL", "reason_code": REASON_CONFIG_INVALID})
        return 1

    ok, reason = validate_config(cfg)
    if not ok:
        emit("ERROR", f"config invalid reason={reason}", events)
        write_events(run_dir, events)
        write_summary(run_dir, meta, events, extra={"status": "FAIL", "reason_code": REASON_CONFIG_INVALID})
        return 1

    medium_path = (repo_root / str(args.medium_json)).resolve()
    cases_path = (repo_root / str(cfg.get("cases_path") or "")).resolve()
    medium = read_json_if_exists(medium_path)

    missing_inputs: List[str] = []
    if not medium:
        missing_inputs.append("medium_json")
    if not cases_path.exists():
        missing_inputs.append("cases_path")

    unknown_ratio = 0.0
    if medium:
        unknown_ratio = float(dict(medium.get("taxonomy", {})).get("unknown_ratio", 0.0) or 0.0)

    cases: List[Dict[str, Any]] = []
    if cases_path.exists():
        try:
            cases = load_cases(cases_path)
        except Exception as exc:
            emit("WARN", f"cases parse failed err={exc}", events)

    known_tags = {str(x).strip().lower() for x in list(cfg.get("known_tags") or []) if str(x).strip()}
    owner_map_cfg = cfg.get("owner_by_taxonomy")
    owner_map: Dict[str, str] = dict(DEFAULT_OWNER_BY_TAXONOMY)
    if isinstance(owner_map_cfg, dict):
        for key, value in owner_map_cfg.items():
            k = str(key or "").strip().lower()
            v = str(value or "").strip()
            if k and v:
                owner_map[k] = v

    max_candidates = int(cfg.get("max_candidates", 12) or 12)
    candidates: List[Dict[str, Any]] = []
    unknown_like_count = 0
    for row in cases:
        tags = [str(x).strip() for x in list(row.get("tags") or []) if str(x).strip()]
        low_tags = {t.lower() for t in tags}
        unknown_like = "unknown" in low_tags or bool(low_tags - known_tags)
        if not unknown_like:
            continue
        unknown_like_count += 1
        candidates.append(
            {
                "case_id": str(row.get("case_id") or ""),
                "tags": tags,
                "query": str(row.get("query") or "")[:220],
                "suggested_taxonomy": suggest_taxonomy(tags, str(row.get("query") or "")),
            }
        )
    candidates = dedupe_candidates(candidates)
    candidates = sorted(candidates, key=lambda r: candidate_priority(r, known_tags), reverse=True)
    if len(candidates) > max_candidates:
        candidates = candidates[:max_candidates]

    collection_actions = build_collection_actions(candidates, int(cfg.get("max_actions", 5) or 5))
    collection_actions_v2 = build_structured_actions(candidates, owner_map, int(cfg.get("max_actions", 5) or 5))
    pipeline_path = (repo_root / str(cfg.get("pipeline_jsonl", args.pipeline_jsonl) or args.pipeline_jsonl)).resolve()
    pipeline_records = build_pipeline_records(
        candidates,
        int(cfg.get("pipeline_max_records", max_candidates) or max_candidates),
        owner_map=owner_map,
    )
    pipeline_written = False

    target = float(cfg.get("unknown_ratio_target", 0.1) or 0.1)
    case_unknown_ratio = 0.0 if not cases else round(float(unknown_like_count) / float(len(cases)), 4)
    unknown_ratio_effective = round(max(float(unknown_ratio), float(case_unknown_ratio)), 4)
    status = "PASS"
    reason_code = ""
    if missing_inputs:
        status = "WARN"
        reason_code = REASON_INPUT_MISSING
        for name in missing_inputs:
            emit("WARN", f"missing input={name}", events)
    elif unknown_ratio_effective > target:
        status = "WARN"
        reason_code = REASON_UNKNOWN_RATIO_ABOVE_TARGET
        emit(
            "WARN",
            f"unknown ratio above target upstream={unknown_ratio} cases={case_unknown_ratio} effective={unknown_ratio_effective} target={target}",
            events,
        )
    else:
        emit("OK", f"taxonomy feedback PASS effective_ratio={unknown_ratio_effective}", events)

    try:
        write_jsonl(pipeline_path, pipeline_records)
        pipeline_written = True
        emit("OK", f"pipeline jsonl written path={pipeline_path} records={len(pipeline_records)}", events)
    except Exception as exc:
        emit("WARN", f"pipeline jsonl write failed err={exc}", events)
        if status == "PASS":
            status = "WARN"
            reason_code = REASON_PIPELINE_WRITE_FAILED

    exit_conditions: List[str] = []
    if reason_code == REASON_INPUT_MISSING:
        exit_conditions.append("Restore medium/cases inputs and rerun S29-02.")
    if reason_code == REASON_UNKNOWN_RATIO_ABOVE_TARGET:
        exit_conditions.append(f"Reduce unknown_ratio to <= {target:.2f} with additional labeled samples.")
    if reason_code == REASON_PIPELINE_WRITE_FAILED:
        exit_conditions.append("Fix pipeline JSONL write path/permission and rerun S29-02.")

    payload: Dict[str, Any] = {
        "schema_version": "s29-taxonomy-pipeline-integration-v2",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {"branch": git_out(repo_root, ["branch", "--show-current"]), "head": git_out(repo_root, ["rev-parse", "HEAD"])} ,
        "inputs": {
            "config": to_repo_rel(repo_root, config_path),
            "medium_json": to_repo_rel(repo_root, medium_path),
            "cases_path": to_repo_rel(repo_root, cases_path),
            "pipeline_jsonl": to_repo_rel(repo_root, pipeline_path),
            "known_tags": sorted(known_tags),
            "owner_by_taxonomy": owner_map,
            "unknown_ratio_target": target,
        },
        "metrics": {
            "unknown_ratio": unknown_ratio_effective,
            "unknown_ratio_upstream": round(unknown_ratio, 4),
            "unknown_ratio_cases": case_unknown_ratio,
            "candidate_count": len(candidates),
            "total_cases_scanned": len(cases),
            "unknown_like_cases": unknown_like_count,
            "pipeline_records": len(pipeline_records),
            "pipeline_written": pipeline_written,
        },
        "candidates": candidates,
        "collection_actions": collection_actions,
        "collection_actions_v2": collection_actions_v2,
        "pipeline": {
            "jsonl": to_repo_rel(repo_root, pipeline_path),
            "record_count": len(pipeline_records),
            "written": pipeline_written,
            "records_preview": pipeline_records[:3],
        },
        "constraints": {
            "exit_conditions": exit_conditions,
        },
        "summary": {
            "status": status,
            "reason_code": reason_code,
            "missing_inputs": len(missing_inputs),
            "exit_condition_count": len(exit_conditions),
        },
        "artifact_names": {
            "json": "taxonomy_pipeline_integration_latest.json",
            "md": "taxonomy_pipeline_integration_latest.md",
            "jsonl": "taxonomy_pipeline_candidates_latest.jsonl",
        },
    }

    out_json = out_dir / "taxonomy_pipeline_integration_latest.json"
    out_md = out_dir / "taxonomy_pipeline_integration_latest.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text(build_markdown(payload), encoding="utf-8")
    emit("OK", f"artifact_json={out_json}", events)
    emit("OK", f"artifact_md={out_md}", events)

    write_events(run_dir, events)
    write_summary(run_dir, meta, events, extra={"status": status, "reason_code": reason_code, "unknown_ratio": round(unknown_ratio, 4)})
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
