#!/usr/bin/env python3
"""
S22-16 ship helper.

One-command flow (stopless):
1) Run light gates (guard + make verify-il)
2) Commit changes (optional)
3) Gate on ci-self checks (all green required for PR sync)
4) Generate PR body with gate summaries
5) Create/update PR via gh (optional)
5) Optionally run reviewpack verify-only once
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


DEFAULT_COMMIT_MESSAGE = "s22-16: align verify-il entrypoint and reduce guard noise"
FORBIDDEN_BRANCH_RX = re.compile(r"^codex/feat([/-]|$)")


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
        log("SKIP", f"dry_run command skipped: {cmd_text}")
        if log_path is not None:
            try:
                log_path.parent.mkdir(parents=True, exist_ok=True)
                log_path.write_text(f"[dry-run] {cmd_text}\n", encoding="utf-8")
            except Exception as exc:
                log("WARN", f"cannot_write_log path={log_path} err={exc}")
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
        log("ERROR", f"command_exception cmd={cmd_text} err={exc}")
        if log_path is not None:
            try:
                log_path.parent.mkdir(parents=True, exist_ok=True)
                log_path.write_text(msg + "\n", encoding="utf-8")
            except Exception:
                pass
        return False, "", msg, 1


def extract_last_matching_line(text: str, pattern: str) -> str:
    hit = ""
    for line in text.splitlines():
        if pattern in line:
            hit = line.strip()
    return hit


def extract_first_matching_regex(text: str, pattern: str) -> str:
    rx = re.compile(pattern)
    for line in text.splitlines():
        m = rx.search(line)
        if m:
            return m.group(0).strip()
    return ""


def parse_args(argv: List[str]) -> Dict[str, object]:
    opts: Dict[str, object] = {
        "dry_run": False,
        "skip_commit": False,
        "skip_pr": False,
        "with_reviewpack": False,
        "include_untracked": True,
        "commit_message": DEFAULT_COMMIT_MESSAGE,
        "base_branch": "main",
    }
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--dry-run":
            opts["dry_run"] = True
        elif a == "--skip-commit":
            opts["skip_commit"] = True
        elif a == "--skip-pr":
            opts["skip_pr"] = True
        elif a == "--with-reviewpack":
            opts["with_reviewpack"] = True
        elif a == "--no-untracked":
            opts["include_untracked"] = False
        elif a == "--commit-message":
            if i + 1 < len(argv):
                opts["commit_message"] = argv[i + 1]
                i += 1
            else:
                log("WARN", "missing value for --commit-message; using default")
        elif a == "--base":
            if i + 1 < len(argv):
                opts["base_branch"] = argv[i + 1]
                i += 1
            else:
                log("WARN", "missing value for --base; using main")
        else:
            log("WARN", f"unknown_arg={a} ignored")
        i += 1

    # Env overrides for make usage.
    if os.environ.get("DRY_RUN") == "1":
        opts["dry_run"] = True
    if os.environ.get("SKIP_COMMIT") == "1":
        opts["skip_commit"] = True
    if os.environ.get("SKIP_PR") == "1":
        opts["skip_pr"] = True
    if os.environ.get("WITH_REVIEWPACK") == "1":
        opts["with_reviewpack"] = True
    if os.environ.get("INCLUDE_UNTRACKED") == "0":
        opts["include_untracked"] = False
    if os.environ.get("COMMIT_MESSAGE"):
        opts["commit_message"] = os.environ.get("COMMIT_MESSAGE", DEFAULT_COMMIT_MESSAGE)
    if os.environ.get("BASE_BRANCH"):
        opts["base_branch"] = os.environ.get("BASE_BRANCH", "main")
    return opts


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
    # Keep order stable and unique.
    uniq: List[str] = []
    seen = set()
    for p in add_paths:
        if p not in seen:
            uniq.append(p)
            seen.add(p)
    return uniq, skipped


def build_pr_body(
    branch: str,
    head_sha: str,
    guard_summary: str,
    verify_status: str,
    smoke_summary: str,
    selftest_summary: str,
    ci_self_status: str,
    reviewpack_status: str,
    reviewpack_sha: str,
) -> str:
    lines = [
        "# Summary",
        "- S22-16: verify-il entrypoint alignment + guard noise control automation.",
        "- Added one-command ship flow for gate run, commit, and PR body sync.",
        "",
        "# Scope",
        "- Changed: Makefile / ops / scripts / docs/ops",
        "- Added: ops/s22_16_ship.py",
        "- Not changed: il executor behavior, CI workflow definitions",
        "",
        "# Evidence (Gates)",
        f"- guard summary: `{guard_summary or 'N/A'}`",
        f"- make verify-il: `{verify_status or 'N/A'}`",
        f"- smoke summary: `{smoke_summary or 'N/A'}`",
        f"- selftest summary: `{selftest_summary or 'N/A'}`",
        f"- ci-self gate: `{ci_self_status or 'N/A'}`",
        f"- reviewpack submit --mode verify-only: `{reviewpack_status or 'SKIP'}`",
    ]
    if reviewpack_sha:
        lines.append(f"- SHA256: `{reviewpack_sha}`")
    lines.extend(
        [
            "",
            "# Risk",
            "- Auto commit may include unintended files if working tree has unrelated edits.",
            "- The helper skips `.local/` and review bundle tarballs by default.",
            "- Rollback: `git revert <commit>` then rerun helper.",
            "",
            "# Notes",
            f"- Branch: `{branch}`",
            f"- HeadSHA: `{head_sha}`",
            "- Generated by `python3 ops/s22_16_ship.py`",
            "",
            "## Milestone (human reminder; advisory is non-blocking)",
            "",
            "Milestone: set in GitHub UI",
            "",
            "Exception reason: N/A",
            "",
        ]
    )
    return "\n".join(lines)


def ci_self_all_green(output_text: str) -> Tuple[bool, str]:
    text = output_text or ""
    if "Some checks were not successful" in text:
        return False, "Some checks were not successful"

    rx_counts = re.search(
        r"(\d+)\s+cancelled,\s+(\d+)\s+failing,\s+(\d+)\s+successful,\s+(\d+)\s+skipped,\s+and\s+(\d+)\s+pending\s+checks",
        text,
        flags=re.I,
    )
    if rx_counts:
        cancelled = int(rx_counts.group(1))
        failing = int(rx_counts.group(2))
        pending = int(rx_counts.group(5))
        if cancelled == 0 and failing == 0 and pending == 0:
            return True, "all checks green"
        return False, f"counts cancelled={cancelled} failing={failing} pending={pending}"

    if "All checks passed" in text:
        return True, "all checks passed"

    return False, "cannot confirm all-green state from ci-self output"


def main(argv: List[str]) -> None:
    stop = 0
    opts = parse_args(argv)
    dry_run = bool(opts["dry_run"])
    skip_commit = bool(opts["skip_commit"])
    skip_pr = bool(opts["skip_pr"])
    with_reviewpack = bool(opts["with_reviewpack"])
    include_untracked = bool(opts["include_untracked"])
    commit_message = str(opts["commit_message"])
    base_branch = str(opts["base_branch"])

    root = Path(".")
    ok, out, _, _ = run_cmd(["git", "rev-parse", "--show-toplevel"], cwd=root, dry_run=False)
    if ok and out.strip():
        root = Path(out.strip())
        log("OK", f"repo_root={root}")
    else:
        log("ERROR", "not in git repo")
        return

    obs = root / ".local" / "obs" / f"s22-16_ship_{now_utc_stamp()}"
    try:
        obs.mkdir(parents=True, exist_ok=True)
        log("OK", f"obs_dir={obs}")
    except Exception as exc:
        log("ERROR", f"cannot_create_obs err={exc}")
        return

    branch = ""
    ok, out, _, _ = run_cmd(["git", "branch", "--show-current"], cwd=root, dry_run=dry_run, log_path=obs / "00_branch.log")
    if ok:
        branch = out.strip()
        if branch:
            log("OK", f"branch={branch}")
    if not branch:
        log("ERROR", "cannot_resolve_branch")
        stop = 1
    elif branch in ("main", "master"):
        log("ERROR", f"refuse_on_base_branch branch={branch}")
        stop = 1
    elif FORBIDDEN_BRANCH_RX.search(branch):
        log("ERROR", f"forbidden_branch_pattern branch={branch}")
        log("ERROR", "do not continue on codex/feat* branches")
        log("OK", "recreate_branch_example=git switch -c feat/<slug>")
        stop = 1

    guard_summary = ""
    verify_status = ""
    smoke_summary = ""
    selftest_summary = ""
    ci_self_status = "SKIP: not run"
    reviewpack_status = "SKIP: not requested"
    reviewpack_sha = ""

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
            guard_summary = f"ERROR: missing guard_summary rc={rc}"
        if not ok:
            log("ERROR", f"guard_failed rc={rc}")
            stop = 1

    if stop == 0:
        ok, out, err, rc = run_cmd(
            ["make", "verify-il"],
            cwd=root,
            dry_run=dry_run,
            log_path=obs / "20_verify_il.log",
        )
        combined = out + err
        verify_status = "OK" if ok else f"ERROR rc={rc}"
        smoke_summary = extract_last_matching_line(combined, "smoke_summary")
        selftest_summary = extract_last_matching_line(combined, "selftest summary")
        if not smoke_summary:
            smoke_summary = "WARN: smoke_summary not found"
        if not selftest_summary:
            selftest_summary = "WARN: selftest summary not found"
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
            combined = out + err
            pass_line = extract_last_matching_line(combined, "PASS: Verify OK")
            if pass_line:
                reviewpack_status = pass_line
            else:
                reviewpack_status = f"WARN: verify-only pass line not found (rc={rc})"
            sha_line = extract_first_matching_regex(combined, r"(?i)sha256[^a-f0-9]*[a-f0-9]{64}")
            if sha_line:
                m = re.search(r"([a-f0-9]{64})", sha_line, flags=re.I)
                if m:
                    reviewpack_sha = m.group(1)
            else:
                any_sha = extract_first_matching_regex(combined, r"\b[a-f0-9]{64}\b")
                if any_sha:
                    reviewpack_sha = any_sha
            if not ok:
                log("WARN", f"reviewpack_verify_only_rc={rc}")
        else:
            reviewpack_status = "SKIP: STOP=1 before reviewpack"
    else:
        log("SKIP", "reviewpack verify-only is optional; run with --with-reviewpack or WITH_REVIEWPACK=1")

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
        stage_paths: List[str] = []
        skipped_paths: List[str] = []
        if ok:
            stage_paths, skipped_paths = parse_status_paths(out, include_untracked=include_untracked)
            for sp in skipped_paths:
                log("SKIP", f"stage_skipped path={sp}")
        else:
            log("ERROR", "cannot_read_git_status")
            stop = 1

        if stop == 0:
            if not stage_paths:
                log("SKIP", "no_paths_to_stage")
            else:
                for p in stage_paths:
                    ok_add, _, _, rc_add = run_cmd(
                        ["git", "add", "--", p],
                        cwd=root,
                        dry_run=dry_run,
                        log_path=obs / "41_git_add.log",
                    )
                    if not ok_add:
                        log("ERROR", f"git_add_failed path={p} rc={rc_add}")
                        stop = 1
                        break

        if stop == 0:
            ok, out, _, _ = run_cmd(
                ["git", "diff", "--cached", "--name-only"],
                cwd=root,
                dry_run=dry_run,
                log_path=obs / "42_cached_diff.log",
            )
            if not ok:
                log("ERROR", "cannot_check_cached_diff")
                stop = 1
            elif not out.strip():
                log("SKIP", "no_staged_changes_to_commit")
            else:
                ok, _, _, rc = run_cmd(
                    ["git", "commit", "-m", commit_message],
                    cwd=root,
                    dry_run=dry_run,
                    log_path=obs / "43_commit.log",
                )
                if ok:
                    log("OK", f"commit_done msg={commit_message}")
                else:
                    log("ERROR", f"git_commit_failed rc={rc}")
                    stop = 1

    head_sha = ""
    ok, out, _, _ = run_cmd(["git", "rev-parse", "HEAD"], cwd=root, dry_run=dry_run, log_path=obs / "50_head_sha.log")
    if ok and out.strip():
        head_sha = out.strip()

    if skip_pr:
        log("SKIP", "PR step skipped by option")
    elif stop == 1:
        log("SKIP", "PR step skipped because STOP=1")
    else:
        if dry_run:
            ci_self_status = "SKIP: dry_run"
            log("SKIP", "dry_run skips ci-self/PR update")
        else:
            if not shutil_which("gh"):
                log("WARN", "gh not found; cannot create/update PR")
                ci_self_status = "WARN: gh not found"
            else:
                ok_auth, _, _, _ = run_cmd(["gh", "auth", "status"], cwd=root, dry_run=False, log_path=obs / "60_gh_auth.log")
                if not ok_auth:
                    log("WARN", "gh auth not ready; PR update skipped")
                    ci_self_status = "WARN: gh auth not ready"
                else:
                    run_cmd(["git", "push"], cwd=root, dry_run=False, log_path=obs / "61_git_push.log")
                    ci_ok, ci_out, ci_err, ci_rc = run_cmd(
                        [
                            "bash",
                            "-lc",
                            'source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh && cd ~/dev/maakie-brainlab && ci-self up --ref "$(git branch --show-current)"',
                        ],
                        cwd=root,
                        dry_run=False,
                        log_path=obs / "62_ci_self_up.log",
                    )
                    ci_text = (ci_out or "") + (ci_err or "")
                    if not ci_ok:
                        ci_self_status = f"ERROR: ci-self command failed rc={ci_rc}"
                        log("ERROR", ci_self_status)
                        stop = 1
                    else:
                        all_green, reason = ci_self_all_green(ci_text)
                        if all_green:
                            ci_self_status = f"OK: {reason}"
                            log("OK", f"ci_self_gate {reason}")
                        else:
                            ci_self_status = f"ERROR: {reason}"
                            log("ERROR", f"ci_self_gate_blocked reason={reason}")
                            stop = 1

    pr_body = build_pr_body(
        branch=branch or "unknown",
        head_sha=head_sha or "unknown",
        guard_summary=guard_summary,
        verify_status=verify_status,
        smoke_summary=smoke_summary,
        selftest_summary=selftest_summary,
        ci_self_status=ci_self_status,
        reviewpack_status=reviewpack_status,
        reviewpack_sha=reviewpack_sha,
    )
    pr_body_path = root / ".local" / "pr" / "s22-16-auto.md"
    try:
        pr_body_path.parent.mkdir(parents=True, exist_ok=True)
        pr_body_path.write_text(pr_body, encoding="utf-8")
        log("OK", f"pr_body_written={pr_body_path}")
    except Exception as exc:
        log("ERROR", f"cannot_write_pr_body err={exc}")
        stop = 1

    if stop == 0 and (not skip_pr) and (not dry_run):
        # PR sync is allowed only after ci-self all-green gate.
        if not shutil_which("gh"):
            log("WARN", "gh not found; cannot create/update PR")
        else:
            ok_view, out_view, _, _ = run_cmd(
                ["gh", "pr", "view", "--json", "number,url"],
                cwd=root,
                dry_run=False,
                log_path=obs / "63_pr_view.log",
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
                    run_cmd(
                        ["gh", "pr", "edit", pr_number, "--body-file", str(pr_body_path)],
                        cwd=root,
                        dry_run=False,
                        log_path=obs / "64_pr_edit.log",
                    )
                    log("OK", f"pr_updated number={pr_number} url={pr_url}")
                else:
                    log("WARN", "cannot parse existing PR number; skipping edit")
            else:
                title = commit_message
                ok_title, out_title, _, _ = run_cmd(
                    ["git", "log", "-1", "--pretty=%s"],
                    cwd=root,
                    dry_run=False,
                    log_path=obs / "65_pr_title.log",
                )
                if ok_title and out_title.strip():
                    title = out_title.strip()
                run_cmd(
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
                        str(pr_body_path),
                    ],
                    cwd=root,
                    dry_run=False,
                    log_path=obs / "66_pr_create.log",
                )

    if stop == 0:
        log("OK", f"s22_16_ship_done STOP=0 obs_dir={obs}")
    else:
        log("ERROR", f"s22_16_ship_done STOP=1 obs_dir={obs}")


def shutil_which(binary: str) -> Optional[str]:
    try:
        import shutil

        return shutil.which(binary)
    except Exception:
        return None


if __name__ == "__main__":
    try:
        import sys

        main(sys.argv[1:])
    except Exception as exc:
        log("ERROR", f"unexpected_top_level_exception={exc}")
        log("ERROR", "s22_16_ship_done STOP=1")
