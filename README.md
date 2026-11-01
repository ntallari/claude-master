# claude-master — personal Claude Code orchestration repo

A "chief of staff" repo for Claude Code. It describes **your role, priorities and active repos**, holds a **task queue**, and runs tasks across those repos with headless `claude -p` (Sonnet) — nightly via cron/systemd or on demand. Every run works on a branch, gets a skeptical reviewer pass, and writes a report; a morning rollup gives you one readout.

It does **not** replace each repo's own `CLAUDE.md` / memory / learnings docs. Workers run *inside* the target repo, so Claude Code loads that repo's `CLAUDE.md` automatically, and the prompt points it at the memory docs listed in `repos.yaml`.

## Quick start
```bash
pip install pyyaml            # optional; a fallback parser is built in
claude --help                 # verify flags for YOUR installed version (see docs/GUIDE.md)
# 1. edit CLAUDE.md (role, priorities) and repos.yaml (replace <REPO_PATH> placeholders)
# 2. copy tasks/_TEMPLATE.md -> tasks/<id>.md, set status: queued
python3 scripts/run_tasks.py --dry-run          # see what would run
python3 scripts/run_tasks.py --task <id>        # run one task for real
python3 scripts/review_task.py --task <id>      # reviewer pass (run_tasks does this automatically unless --no-review)
python3 scripts/morning_rollup.py               # yesterday's reports -> reports/rollup-YYYY-MM-DD.md
```

## Layout
```
CLAUDE.md                 master orchestrator instructions + guardrails
repos.yaml                registry of active repos
tasks/_TEMPLATE.md        task template (frontmatter + body)
tasks/*.md                queued / running / review / done / failed / blocked tasks
scripts/run_tasks.py      runner: pick tasks, lock repo, branch, claude -p, report
scripts/review_task.py    reviewer: second claude -p session on diff + tests -> PASS/FAIL
scripts/morning_rollup.py combine yesterday's reports
scripts/common.py         shared helpers (frontmatter, yaml fallback, git)
.claude/agents/*.md       subagents: reviewer, sim-analyst, test-triage
.claude/settings.json     conservative permissions + hook example
cron/                     crontab example + systemd service/timer
docs/GUIDE.md             full usage guide, tuning, pitfalls, rollout plan
reports/YYYY-MM-DD/       per-task reports;   logs/  raw run logs;   locks/  per-repo locks
```
Copy `.claude/agents/` and the relevant parts of `.claude/settings.json` into target repos (or `~/.claude/`) so workers have them too.
