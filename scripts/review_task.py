#!/usr/bin/env python3
"""Reviewer pass: a second, skeptical `claude -p` session reviews the branch diff + reruns tests.
Appends a '## Review' section with PASS/FAIL and reasons to the task report.

Usage: review_task.py --task ID [--date YYYY-MM-DD]
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *  # noqa

REVIEW_TOOLS = "Read,Grep,Glob,Bash(git diff:*),Bash(git log:*),Bash(git show:*),Bash(pytest:*),Bash(python:*),Bash(make:*)"

def review(meta, repo, branch, report_path):
    rpath = repo["path"]; base = repo.get("default_branch", "main")
    diff = git(rpath, "diff", f"{base}...{branch}", check=False)
    if len(diff) > 60000: diff = diff[:60000] + "\n... [diff truncated; inspect with git diff yourself]"
    worker = Path(report_path).read_text()
    prompt = f"""You are a skeptical reviewer (see the `reviewer` subagent). Do NOT edit files or commit.
Task definition of done and worker report are below. Verify claims independently:
- Re-run the tests: `{repo.get('test_command','(none)')}` and quote the result line.
- Check the diff is in scope, minimal, has no secrets, no deleted/skipped tests, no changes to the default branch.
- Check numbers in the report against actual outputs where possible. Flag any claimed success you cannot verify.
Final line must be exactly `VERDICT: PASS` or `VERDICT: FAIL`, preceded by bullet reasons.

=== WORKER REPORT ===
{worker[-20000:]}
=== DIFF {base}...{branch} ===
{diff or '(empty diff)'}"""
    log = LOGS / today() / f"{meta['id']}.review.log"
    code, out, err = run_claude(prompt, rpath, meta.get("model", "sonnet"), 15, 20, REVIEW_TOOLS, log)
    verdict = "FAIL"
    for line in reversed(out.strip().splitlines()):
        if "VERDICT:" in line: verdict = "PASS" if "PASS" in line.upper() else "FAIL"; break
    if code: verdict = "FAIL"
    with open(report_path, "a") as f:
        f.write(f"\n## Review\n**{verdict}** (reviewer exit {code})\n\n{out or err}\n")
    print(f"  review: {verdict}")
    return verdict

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--task", required=True); ap.add_argument("--date", default=today())
    a = ap.parse_args()
    _, repos = load_registry()
    path = TASKS / f"{a.task}.md"; meta, _ = read_task(path)
    report = REPORTS / a.date / f"{a.task}.md"
    if not report.exists(): sys.exit(f"no report at {report}; run the task first")
    branch = f"claude/{a.task}-{a.date}"
    v = review(meta, repos[meta["repo"]], branch, report)
    if v == "PASS" and meta.get("status") == "review":
        set_fields(path, status="queued" if meta.get("schedule") in ("nightly", "weekly") else "done")
    return 0 if v == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
