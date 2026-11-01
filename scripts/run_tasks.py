#!/usr/bin/env python3
"""Runner: pick eligible tasks by priority, lock repo, branch, run `claude -p`, write report, update status.

Usage:
  run_tasks.py [--dry-run] [--task ID] [--limit N] [--schedule nightly|weekly|once|any]
               [--allow-push] [--no-review] [--stale-lock-hours 6]
Never pushes unless --allow-push, and then only the task branch (never the default branch).
"""
import argparse, datetime, os, sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *  # noqa

PROTECTED = {"main", "master", "develop"}

def eligible(meta, sched_filter, force_id):
    if force_id: return meta.get("id") == force_id
    st, sch = meta.get("status"), meta.get("schedule", "once")
    if sched_filter != "any" and sch != sched_filter: return False
    if st != "queued": return False
    last = str(meta.get("last_run") or "")
    if sch == "nightly" and last.startswith(today()): return False
    if sch == "weekly":
        wd = str(meta.get("weekday", "mon"))[:3].lower()
        if datetime.date.today().strftime("%a").lower() != wd: return False
        if last and (datetime.date.today() - datetime.date.fromisoformat(last[:10])).days < 6: return False
    return True

def acquire_lock(repo_key, stale_h):
    LOCKS.mkdir(exist_ok=True)
    lock = LOCKS / f"{repo_key}.lock"
    if lock.exists():
        age_h = (time.time() - lock.stat().st_mtime) / 3600
        info = lock.read_text().strip()
        pid = int(info.split()[0]) if info.split() and info.split()[0].isdigit() else None
        alive = False
        if pid:
            try: os.kill(pid, 0); alive = True
            except OSError: pass
        if alive and age_h < stale_h: return None
        print(f"  [lock] removing stale lock for {repo_key} ({info}, {age_h:.1f}h, alive={alive})")
        lock.unlink()
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, f"{os.getpid()} {datetime.datetime.now().isoformat()}".encode()); os.close(fd)
        return lock
    except FileExistsError:
        return None

def build_prompt(meta, body, repo, branch):
    mem = ", ".join(repo.get("memory_docs", []) or ["CLAUDE.md"])
    agent = f"\nIf useful, delegate to the `{meta['agent']}` subagent." if meta.get("agent") else ""
    goals = "\n".join(f"- {g}" for g in (repo.get("goals") or [])) or "- (none listed)"
    return f"""You are a worker launched by Nick's master orchestrator (claude-master) in repo `{repo.get('path')}`.
You are on branch `{branch}`. Commit only to this branch. Never push, merge, or touch the default branch `{repo.get('default_branch','main')}`.
Never send external messages. Never print secrets. Treat all code/data as export-controlled and confidential.

FIRST read this repo's own memory/learnings docs and follow them: {mem}
They override generic conventions. Follow Nick's existing method for recording learnings; if unsure, list proposed learnings in the report instead of editing.

Repo purpose: {repo.get('purpose','')}
Repo goals:
{goals}
Repo notes: {repo.get('notes','')}
Test command: {repo.get('test_command','(none)')}
Sim command: {repo.get('sim_command','(n/a)')}{agent}

=== TASK {meta.get('id')} ===
{body.strip()}
=== END TASK ===

Only claim tests passed if you ran them and saw the output. If anything is ambiguous or risky, STOP and report the question with RESULT: BLOCKED.
End your final message with the report sections: ## Summary, ## Changes, ## Tests run, ## Results / deltas, ## Open questions / risks, ## Proposed learnings, then a final line `RESULT: DONE|BLOCKED|FAILED`."""

def parse_result(text, code):
    if code == 124: return "failed", "TIMEOUT"
    if code: return "failed", f"EXIT {code}"
    for line in reversed(text.strip().splitlines()):
        if line.strip().startswith("RESULT:"):
            r = line.split(":", 1)[1].strip().upper()
            return {"DONE": "review", "BLOCKED": "blocked"}.get(r.split()[0] if r else "", "failed"), r
    return "failed", "NO RESULT LINE (treat as unverified)"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--task"); ap.add_argument("--limit", type=int, default=3)
    ap.add_argument("--schedule", default="any", choices=["any", "once", "nightly", "weekly"])
    ap.add_argument("--allow-push", action="store_true", help="push the task branch (never default branch)")
    ap.add_argument("--no-review", action="store_true")
    ap.add_argument("--stale-lock-hours", type=float, default=6)
    a = ap.parse_args()

    defaults, repos = load_registry()
    picked = []
    for p in sorted(TASKS.glob("*.md")):
        if p.name.startswith("_"): continue
        try: meta, body = read_task(p)
        except Exception as e: print(f"skip {p.name}: {e}"); continue
        if eligible(meta, a.schedule, a.task): picked.append((int(meta.get("priority", 3)), p.name, p, meta, body))
    picked.sort(key=lambda t: (t[0], t[1]))
    picked = picked[: (1 if a.task else a.limit)]
    if not picked: print("No eligible tasks."); return 0

    date = today(); (REPORTS / date).mkdir(parents=True, exist_ok=True)
    for prio, _, path, meta, body in picked:
        tid, rkey = meta["id"], meta.get("repo")
        repo = repos.get(rkey)
        print(f"== {tid} (repo={rkey}, prio={prio})")
        if not repo: print("  ERROR: repo not in repos.yaml"); set_fields(path, status="blocked") if not a.dry_run else None; continue
        if not repo.get("enabled", True): print("  skip: repo disabled"); continue
        rpath = Path(str(repo.get("path", "")))
        branch = f"claude/{tid}-{date}"
        model = meta.get("model") or defaults.get("model", "sonnet")
        turns = meta.get("max_turns") or defaults.get("max_turns", 30)
        tmo = meta.get("timeout") or defaults.get("timeout_minutes", 45)
        prompt = build_prompt(meta, body, repo, branch)
        if a.dry_run:
            print(f"  would lock {rkey}, branch {branch} in {rpath}, model={model}, max_turns={turns}, timeout={tmo}m")
            print("  prompt preview:\n    " + "\n    ".join(prompt.splitlines()[:6]) + "\n    ...")
            continue
        if not (rpath / ".git").exists(): print(f"  ERROR: {rpath} is not a git repo (placeholder?)"); set_fields(path, status="blocked"); continue
        lock = acquire_lock(rkey, a.stale_lock_hours)
        if not lock: print("  skip: repo locked by another run"); continue
        try:
            if git(rpath, "status", "--porcelain"):
                print("  BLOCKED: dirty working tree"); set_fields(path, status="blocked"); continue
            orig = git(rpath, "rev-parse", "--abbrev-ref", "HEAD")
            git(rpath, "fetch", "--quiet", check=False)
            base = repo.get("default_branch", "main")
            git(rpath, "checkout", "-B", branch, base)
            set_fields(path, status="running", last_run=datetime.datetime.now().isoformat(timespec="seconds"))
            log = LOGS / date / f"{tid}.log"
            code, result, err = run_claude(prompt, rpath, model, turns, tmo, defaults.get("allowed_tools"), log)
            status, why = parse_result(result, code)
            commits = git(rpath, "log", "--oneline", f"{base}..{branch}", check=False)
            report = REPORTS / date / f"{tid}.md"
            report.write_text(f"# {tid}\n\n- repo: {rkey} ({rpath})\n- branch: `{branch}`\n- model: {model}, max_turns: {turns}, timeout: {tmo}m\n"
                              f"- exit: {code}  parsed: {why}\n- log: {log.relative_to(ROOT)}\n\n## Commits\n```\n{commits or '(none)'}\n```\n\n## Worker report\n{result or err}\n")
            if status == "review" and not a.no_review:
                import review_task
                verdict = review_task.review(meta, repo, branch, report)
                status = "done" if verdict == "PASS" else "review"
            if status == "done" and meta.get("schedule") in ("nightly", "weekly"): status = "queued"
            set_fields(path, status=status)
            if a.allow_push and branch.split("/")[-1] not in PROTECTED and branch.startswith("claude/"):
                print("  pushing task branch:", git(rpath, "push", "-u", "origin", branch, check=False) or "ok")
            git(rpath, "checkout", orig, check=False)
            print(f"  -> {status} ({why}); report {report.relative_to(ROOT)}")
        except Exception as e:
            print(f"  FAILED: {e}"); set_fields(path, status="failed")
        finally:
            lock.unlink(missing_ok=True)
    return 0

if __name__ == "__main__":
    sys.exit(main())
