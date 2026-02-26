#!/usr/bin/env python3
"""
Generic ship helper for S-phase operations.

Stopless behavior:
- Prints OK/WARN/ERROR/SKIP lines.
- Never raises process-level non-zero intentionally.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple


FORBIDDEN_BRANCH_RX = re.compile(r"^codex/feat")


def log(level: str, message: str) -> None:
    print(f"{level}: {message}", flush=True)


def now_utc_stamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run_cmd(
    args: List[str],
    cwd: Path,
    log_path: Optional[Path] = None,
    dry_run: bool = False,
) -> Tuple[bool, str, str, int]:
    cmd_text = " ".join(shlex.quote(x) for x in args)
    log("OK", f"run_cmd={cmd_text}")
    if dry_run:
        if log_path is not None:
            try:
                log_path.parent.mkdir(parents=True, exist_ok=True)
                log_path.write_text(f"[dry-run] {cmd_text}\n", encoding="utf-8")
            except Exception as exc:
                log("WARN", f"cannot_write_log path={log_path} err={exc}")
        log("SKIP", f"dry_run command skipped: {cmd_text}")
        return True, "", "", 0
    try:
        cp = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, check=False)
        out = cp.stdout or ""
        err = cp.stderr or ""
        rc = cp.returncode
        if out.strip():
            print(out.rstrip())
        if err.strip():
            print(err.rstrip())
        if log_path is not None:
            try:
                log_path.parent.mkdir(parents=True, exist_ok=True)
                log_path.write_text(out + err, encoding="utf-8")
            except Exception as exc:
                log("WARN", f"cannot_write_log path={log_path} err={exc}")
        return rc == 0, out, err, rc
    except Exception as exc:
        msg = f"exception: {exc}"
        if log_path is not None:
            try:
                log_path.parent.mkdir(parents=True, exist_ok=True)
                log_path.write_text(msg + "\n", encoding="utf-8")
            except Exception:
                pass
        log("ERROR", f"command_exception cmd={cmd_text} err={exc}")
        return False, "", msg, 1


def parse_args(argv: List[str]) -> Dict[str, object]:
    opts: Dict[str, object] = {
        "phase": "",
        "dry_run": False,
        "skip_commit": False,
        "skip_pr": False,
        "with_reviewpack": False,
        "base_branch": "main",
        "commit_message": "",
        "include_untracked": True,
    }
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--phase" and i + 1 < len(argv):
            opts["phase"] = argv[i + 1]
            i += 1
        elif a == "--dry-run":
            opts["dry_run"] = True
        elif a == "--skip-commit":
            opts["skip_commit"] = True
        elif a == "--skip-pr":
            opts["skip_pr"] = True
        elif a == "--with-reviewpack":
            opts["with_reviewpack"] = True
        elif a == "--base" and i + 1 < len(argv):
            opts["base_branch"] = argv[i + 1]
            i += 1
        elif a == "--commit-message" and i + 1 < len(argv):
            opts["commit_message"] = argv[i + 1]
            i += 1
        elif a == "--no-untracked":
            opts["include_untracked"] = False
        else:
            log("WARN", f"unknown_arg={a} ignored")
        i += 1

    if os.environ.get("DRY_RUN") == "1":
        opts["dry_run"] = True
    if os.environ.get("SKIP_COMMIT") == "1":
        opts["skip_commit"] = True
    if os.environ.get("SKIP_PR") == "1":
        opts["skip_pr"] = True
    if os.environ.get("WITH_REVIEWPACK") == "1":
        opts["with_reviewpack"] = True
    if os.environ.get("BASE_BRANCH"):
        opts["base_branch"] = os.environ.get("BASE_BRANCH", "main")
    if os.environ.get("PHASE"):
        opts["phase"] = os.environ.get("PHASE", "")
    if os.environ.get("COMMIT_MESSAGE"):
        opts["commit_message"] = os.environ.get("COMMIT_MESSAGE", "")
    if os.environ.get("INCLUDE_UNTRACKED") == "0":
        opts["include_untracked"] = False
    return opts


def infer_phase(branch: str) -> str:
    m = re.search(r"([sS]\d{2}-\d{2})", branch or "")
    if not m:
        return ""
    return m.group(1).upper()


def extract_last_matching_line(text: str, pattern: str) -> str:
    hit = ""
    for line in text.splitlines():
        if pattern in line:
            hit = line.strip()
    return hit


def parse_status_paths(status_text: str, include_untracked: bool) -> Tuple[List[str], List[str]]:
    add_paths: List[str] = []
    skipped: List[str] = []
    skip_name_rx = re.compile(r"^(review_bundle_|review_pack_).+\.tar\.gz$")
    for raw in status_text.splitlines():
        line = raw.rstrip()
        if len(line) < 4:
            continue
        code = line[:2]
        payload = line[3:].strip()
        path = payload
        if " -> " in payload:
            path = payload.split(" -> ", 1)[1].strip()
        if not path:
            continue
        if path.startswith(".local/"):
            skipped.append(path)
            continue
        if skip_name_rx.match(Path(path).name):
            skipped.append(path)
            continue
        if code == "??" and not include_untracked:
            skipped.append(path)
            continue
        add_paths.append(path)
    uniq: List[str] = []
    seen = set()
    for p in add_paths:
        if p not in seen:
            uniq.append(p)
            seen.add(p)
    return uniq, skipped


def ci_self_all_green(output_text: str) -> Tuple[bool, str]:
    text = output_text or ""
    if "Some checks were not successful" in text:
        return False, "Some checks were not successful"
    m = re.search(
        r"(\d+)\s+cancelled,\s+(\d+)\s+failing,\s+(\d+)\s+successful,\s+(\d+)\s+skipped,\s+and\s+(\d+)\s+pending\s+checks",
        text,
        flags=re.I,
    )
    if m:
        cancelled = int(m.group(1))
        failing = int(m.group(2))
        pending = int(m.group(5))
        if cancelled == 0 and failing == 0 and pending == 0:
            return True, "all checks green"
        return False, f"counts cancelled={cancelled} failing={failing} pending={pending}"
    if "All checks passed" in text:
        return True, "all checks passed"

    latest: Dict[str, str] = {}
    known_states = {
        "pass",
        "skipped",
        "skip",
        "pending",
        "fail",
        "failure",
        "failing",
        "cancelled",
        "canceled",
        "error",
        "timed_out",
        "action_required",
        "queued",
        "in_progress",
    }
    for line in text.splitlines():
        if "\t" not in line:
            continue
        cols = [c.strip() for c in line.split("\t")]
        if len(cols) < 2:
            continue
        name = cols[0]
        state = cols[1].lower()
        if state not in known_states:
            continue
        target = cols[3] if len(cols) > 3 else ""
        latest[f"{name}|{target}"] = state
    if latest:
        bad = [v for v in latest.values() if v not in {"pass", "skip", "skipped"}]
        if not bad:
            return True, f"all checks green (final states={len(latest)})"
        return False, f"non-green final statuses: {','.join(sorted(set(bad)))}"
    return False, "cannot confirm all-green state from ci-self output"


def build_pr_body(
    phase: str,
    branch: str,
    head_sha: str,
    guard_summary: str,
    verify_status: str,
    ci_self_status: str,
    reviewpack_status: str,
) -> str:
    lines = [
        "# Summary",
        f"- {phase or 'UNKNOWN'} ship flow update.",
        "- Generated by ops/phase_ship.py.",
        "",
        "# Gate Results",
        f"- guard summary: `{guard_summary or 'N/A'}`",
        f"- make verify-il: `{verify_status or 'N/A'}`",
        f"- ci-self gate: `{ci_self_status or 'N/A'}`",
        f"- reviewpack verify-only: `{reviewpack_status or 'SKIP'}`",
        "",
        "# Notes",
        f"- Branch: `{branch}`",
        f"- HeadSHA: `{head_sha}`",
        f"- Phase: `{phase or 'N/A'}`",
        "",
        "Milestone: set in GitHub UI",
        "",
        "Exception reason: N/A",
        "",
    ]
    return "\n".join(lines)


def main(argv: List[str]) -> None:
    opts = parse_args(argv)
    stop = 0
    dry_run = bool(opts["dry_run"])
    skip_commit = bool(opts["skip_commit"])
    skip_pr = bool(opts["skip_pr"])
    with_reviewpack = bool(opts["with_reviewpack"])
    include_untracked = bool(opts["include_untracked"])
    base_branch = str(opts["base_branch"])

    root = Path(".")
    ok_root, out_root, _, _ = run_cmd(["git", "rev-parse", "--show-toplevel"], cwd=root, dry_run=False)
    if ok_root and out_root.strip():
        root = Path(out_root.strip())
        log("OK", f"repo_root={root}")
    else:
        log("ERROR", "not in git repo")
        return

    obs = root / ".local" / "obs" / f"phase_ship_{now_utc_stamp()}"
    try:
        obs.mkdir(parents=True, exist_ok=True)
        log("OK", f"obs_dir={obs}")
    except Exception as exc:
        log("ERROR", f"cannot_create_obs err={exc}")
        return

    branch = ""
    ok_branch, out_branch, _, _ = run_cmd(
        ["git", "branch", "--show-current"], cwd=root, dry_run=False, log_path=obs / "00_branch.log"
    )
    if ok_branch and out_branch.strip():
        branch = out_branch.strip()
        log("OK", f"branch={branch}")
    else:
        log("ERROR", "cannot_resolve_branch")
        stop = 1

    phase = str(opts["phase"]).strip()
    if not phase:
        phase = infer_phase(branch)
        if phase:
            log("OK", f"phase_inferred={phase}")
    if not phase:
        log("ERROR", "phase missing (pass --phase or use sXX-YY branch)")
        stop = 1
    phase_label = phase or "unknown"
    phase_slug = phase_label.lower()
    commit_message = str(opts["commit_message"]).strip() or f"{phase_slug}: ship updates"

    if branch in ("main", "master"):
        log("ERROR", f"refuse_on_base_branch branch={branch}")
        stop = 1
    if FORBIDDEN_BRANCH_RX.search(branch):
        log("ERROR", f"forbidden_branch_pattern branch={branch}")
        log("ERROR", "do not continue on codex/feat* branches")
        log("OK", "recreate_branch_example=git switch -c feat/<slug>")
        stop = 1

    guard_summary = ""
    verify_status = ""
    ci_self_status = "SKIP: not run"
    reviewpack_status = "SKIP: not requested"

    if stop == 0:
        ok, out, err, rc = run_cmd(
            ["python3", "ops/il_entrypoint_guard.py"],
            cwd=root,
            dry_run=dry_run,
            log_path=obs / "10_guard.log",
        )
        combined = out + err
        guard_summary = extract_last_matching_line(combined, "OK: guard_summary")
        if not guard_summary:
            guard_summary = f"WARN: guard_summary missing rc={rc}"
        if not ok:
            log("ERROR", f"guard_failed rc={rc}")
            stop = 1

    if stop == 0:
        ok, _, _, rc = run_cmd(["make", "verify-il"], cwd=root, dry_run=dry_run, log_path=obs / "20_verify_il.log")
        verify_status = "OK" if ok else f"ERROR rc={rc}"
        if not ok:
            log("ERROR", f"verify_il_failed rc={rc}")
            stop = 1

    if with_reviewpack:
        if stop == 0:
            ok, out, err, rc = run_cmd(
                ["go", "run", "cmd/reviewpack/main.go", "submit", "--mode", "verify-only"],
                cwd=root,
                dry_run=dry_run,
                log_path=obs / "30_reviewpack_verify_only.log",
            )
            line = extract_last_matching_line(out + err, "PASS: Verify OK")
            if line:
                reviewpack_status = line
            elif ok:
                reviewpack_status = "WARN: pass marker missing"
            else:
                reviewpack_status = f"WARN: verify-only rc={rc}"
                log("WARN", reviewpack_status)
        else:
            reviewpack_status = "SKIP: STOP=1 before reviewpack"
    else:
        log("SKIP", "reviewpack verify-only is optional; pass --with-reviewpack")

    if skip_commit:
        log("SKIP", "commit step skipped by option")
    elif stop == 1:
        log("SKIP", "commit step skipped because STOP=1")
    else:
        ok, out, _, _ = run_cmd(
            ["git", "status", "--porcelain=v1", "-uall"],
            cwd=root,
            dry_run=dry_run,
            log_path=obs / "40_git_status.log",
        )
        if not ok:
            log("ERROR", "cannot_read_git_status")
            stop = 1
        else:
            to_add, skipped = parse_status_paths(out, include_untracked=include_untracked)
            for path in skipped:
                log("SKIP", f"stage_skipped path={path}")
            for idx, path in enumerate(to_add, start=1):
                ok_add, _, _, rc_add = run_cmd(
                    ["git", "add", "--", path],
                    cwd=root,
                    dry_run=dry_run,
                    log_path=obs / f"41_git_add_{idx}.log",
                )
                if not ok_add:
                    log("ERROR", f"git_add_failed path={path} rc={rc_add}")
                    stop = 1
                    break
        if stop == 0:
            ok_diff, out_diff, _, _ = run_cmd(
                ["git", "diff", "--cached", "--name-only"],
                cwd=root,
                dry_run=dry_run,
                log_path=obs / "42_cached_diff.log",
            )
            if not ok_diff:
                log("ERROR", "cannot_check_cached_diff")
                stop = 1
            elif not out_diff.strip():
                log("SKIP", "no_staged_changes_to_commit")
            else:
                ok_commit, _, _, rc_commit = run_cmd(
                    ["git", "commit", "-m", commit_message],
                    cwd=root,
                    dry_run=dry_run,
                    log_path=obs / "43_commit.log",
                )
                if not ok_commit:
                    log("ERROR", f"git_commit_failed rc={rc_commit}")
                    stop = 1
                else:
                    log("OK", f"commit_done msg={commit_message}")

    head_sha = ""
    ok_sha, out_sha, _, _ = run_cmd(["git", "rev-parse", "HEAD"], cwd=root, dry_run=dry_run, log_path=obs / "50_head.log")
    if ok_sha and out_sha.strip():
        head_sha = out_sha.strip()
    pr_path = root / ".local" / "pr" / f"{phase_slug}-auto.md"

    if skip_pr:
        log("SKIP", "PR step skipped by option")
    elif stop == 1:
        log("SKIP", "PR step skipped because STOP=1")
    elif dry_run:
        ci_self_status = "SKIP: dry_run"
        log("SKIP", "dry_run skips ci-self/PR sync")
    else:
        ok_push, _, _, rc_push = run_cmd(["git", "push"], cwd=root, dry_run=False, log_path=obs / "60_git_push.log")
        if not ok_push:
            ci_self_status = f"ERROR: git push failed rc={rc_push}"
            log("ERROR", ci_self_status)
            stop = 1
        if stop == 0:
            ci_cmd = (
                "source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh"
                f" && cd {shlex.quote(str(root))}"
                f" && ci-self up --ref {shlex.quote(branch)}"
            )
            ok_ci, out_ci, err_ci, rc_ci = run_cmd(
                ["bash", "-lc", ci_cmd], cwd=root, dry_run=False, log_path=obs / "61_ci_self.log"
            )
            ci_text = (out_ci or "") + (err_ci or "")
            if not ok_ci:
                ci_self_status = f"ERROR: ci-self command failed rc={rc_ci}"
                log("ERROR", ci_self_status)
                stop = 1
            else:
                green, reason = ci_self_all_green(ci_text)
                if green:
                    ci_self_status = f"OK: {reason}"
                    log("OK", f"ci_self_gate {reason}")
                else:
                    ci_self_status = f"ERROR: {reason}"
                    log("ERROR", f"ci_self_gate_blocked reason={reason}")
                    stop = 1

    pr_body = build_pr_body(
        phase=phase_label,
        branch=branch or "unknown",
        head_sha=head_sha or "unknown",
        guard_summary=guard_summary,
        verify_status=verify_status,
        ci_self_status=ci_self_status,
        reviewpack_status=reviewpack_status,
    )
    try:
        pr_path.parent.mkdir(parents=True, exist_ok=True)
        pr_path.write_text(pr_body, encoding="utf-8")
        log("OK", f"pr_body_written={pr_path}")
    except Exception as exc:
        log("ERROR", f"cannot_write_pr_body err={exc}")
        stop = 1

    if stop == 0 and (not skip_pr) and (not dry_run):
        ok_view, out_view, _, _ = run_cmd(
            ["gh", "pr", "view", "--json", "number,url"],
            cwd=root,
            dry_run=False,
            log_path=obs / "62_pr_view.log",
        )
        if ok_view:
            pr_number = ""
            pr_url = ""
            try:
                obj = json.loads(out_view)
                pr_number = str(obj.get("number", ""))
                pr_url = str(obj.get("url", ""))
            except Exception:
                pass
            if pr_number:
                ok_edit, _, _, rc_edit = run_cmd(
                    ["gh", "pr", "edit", pr_number, "--body-file", str(pr_path)],
                    cwd=root,
                    dry_run=False,
                    log_path=obs / "63_pr_edit.log",
                )
                if ok_edit:
                    log("OK", f"pr_updated number={pr_number} url={pr_url}")
                else:
                    log("ERROR", f"pr_update_failed number={pr_number} rc={rc_edit}")
                    stop = 1
        else:
            title = commit_message
            ok_title, out_title, _, _ = run_cmd(
                ["git", "log", "-1", "--pretty=%s"], cwd=root, dry_run=False, log_path=obs / "64_title.log"
            )
            if ok_title and out_title.strip():
                title = out_title.strip()
            ok_create, _, _, rc_create = run_cmd(
                [
                    "gh",
                    "pr",
                    "create",
                    "--base",
                    base_branch,
                    "--head",
                    branch,
                    "--title",
                    title,
                    "--body-file",
                    str(pr_path),
                ],
                cwd=root,
                dry_run=False,
                log_path=obs / "65_pr_create.log",
            )
            if not ok_create:
                log("ERROR", f"pr_create_failed rc={rc_create}")
                stop = 1

    if stop == 0:
        log("OK", f"phase_ship_done STOP=0 phase={phase_label} obs_dir={obs}")
    else:
        log("ERROR", f"phase_ship_done STOP=1 phase={phase_label} obs_dir={obs}")


if __name__ == "__main__":
    try:
        import sys

        main(sys.argv[1:])
    except Exception as exc:
        log("ERROR", f"unexpected_top_level_exception={exc}")
        log("ERROR", "phase_ship_done STOP=1")
