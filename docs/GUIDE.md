# claude-master — Usage Guide

> **Verify CLI flags first.** Flags used here (`-p`, `--output-format json`, `--max-turns`, `--model`, `--allowedTools`) match recent Claude Code releases, but they change. Run `claude --help` on your installed version and adjust `run_claude()` in `scripts/common.py` if anything differs. Same for `.claude/settings.json` keys and hook syntax.

> **Security first.** Before pointing this at any work repo, confirm with your security / export-control team that Claude Code (and the model endpoint it uses) is approved for that code and data. See "ITAR / export control" below.

## 1. Concept
- **Master repo (this one)** = chief of staff. Knows your role (`CLAUDE.md`), your repos (`repos.yaml`), and the work queue (`tasks/`).
- **Workers** = headless `claude -p` sessions launched *inside each target repo* on a fresh branch. They auto-load that repo's `CLAUDE.md`; the prompt also points them at your memory/learnings docs (`memory_docs`). Your existing memory method stays the source of truth.
- **Reviewer** = a second, skeptical session that reruns tests and checks the diff; PASS → done, FAIL → stays in `review` for you.
- **Rollup** = one morning markdown readout of everything that ran.

## 2. Setup
1. `git init` this folder (keep it private/internal). Optional: `pip install pyyaml` (a fallback parser handles the simple YAML used here).
2. Confirm `claude` works non-interactively: `cd <some repo> && claude -p "say ok" --output-format json --max-turns 1`.
3. Edit `CLAUDE.md`: fill `<DESCRIBE_ROLE>` and priorities.
4. Edit `repos.yaml`: real absolute paths, test/sim commands, `memory_docs` that match your existing files, `enabled`.
5. Copy `.claude/agents/*.md` and `.claude/settings.json` into each target repo's `.claude/` (or into `~/.claude/` for all repos). Merge with anything already there.
6. `python3 scripts/run_tasks.py --dry-run` — confirm the expected tasks are picked.
7. Run one task for real while watching: `python3 scripts/run_tasks.py --task triage-failing-tests`.
8. Install the schedule (`cron/crontab.example` or the systemd units) only after a week of manual runs.

## 3. Adding a repo
Add a block under `repos:` with `path`, `purpose`, `default_branch`, `test_command`, optional `sim_command`, `memory_docs`, `goals`, `notes`, `enabled`. Key = the name tasks use in `repo:`. Keep `notes` short and operational ("use reduced MC config", "never touch data/raw").

## 4. Adding a task
`cp tasks/_TEMPLATE.md tasks/<id>.md`; `id` must equal the filename. Good tasks have: one goal, pointers to files, a **checkable definition of done**, and an explicit out-of-scope list.
- `schedule: once` → runs once; ends `done`/`review`/`blocked`/`failed`.
- `nightly` → at most once per day; returns to `queued` after a PASS.
- `weekly` + `weekday: mon` → once a week.
- Status lifecycle: `queued → running → review → done` (or `blocked`/`failed`). To retry, set `status: queued` by hand.

## 5. Daily workflow
1. Read `reports/rollup-<today>.md` (06:00).
2. For each `review`/PASS item: inspect the branch (below), then merge it yourself through your normal PR process.
3. For `blocked`: answer the question in the task file body, set `status: queued`.
4. For `failed`: check `logs/<date>/<id>.log`; fix the cause (often env), requeue.
5. Fold real lessons into the repo's memory docs using your existing method (workers list them under "Proposed learnings").
6. Queue new tasks for tonight.

## 6. Reviewing branches
```bash
cd <repo>
git log --oneline main..claude/<id>-<date>
git diff main...claude/<id>-<date>
git switch claude/<id>-<date> && <test_command>
# accept: open a PR / merge via your normal process.  reject: git branch -D claude/<id>-<date>
```
Rerun a review manually: `python3 scripts/review_task.py --task <id> --date <date>`.
Prune old branches periodically: `git branch --list 'claude/*'`.

## 7. Adjustments & tuning
- **Schedules**: edit crontab/timer times; use `--schedule` and `--limit` to split nightly vs. one-off work.
- **Max turns / timeout**: per task in frontmatter; defaults in `repos.yaml`. Analysis tasks ~15–25 turns; fix tasks 30–50. Long sims: raise `timeout` and run the sim via a script that writes results to disk so the agent only reads summaries.
- **Concurrency**: the runner is sequential and locks per repo. For parallelism, run several runner instances with different `--schedule`/`--task` — locks prevent two runs in one repo. Or use `git worktree` per task (advanced; edit the branch step).
- **Model choice**: `defaults.model` / per-task `model`. Sonnet for most; a stronger model for the reviewer or tricky debugging if available; verify allowed model names with `claude --help` / your org's settings.
- **Prompt tweaks**: `build_prompt()` in `run_tasks.py` (worker) and `review()` in `review_task.py`. Keep the guardrails and the RESULT line contract.
- **Tool permissions**: `defaults.allowed_tools` (passed as `--allowedTools`) + `.claude/settings.json` deny list. Widen gradually; never allow push/merge.
- **Subagents**: add `.claude/agents/<name>.md` (frontmatter `name`, `description`, `tools`), reference it via `agent:` in a task.
- **MCP connectors** (Jira, Confluence, DBs): configure via `claude mcp add` or `.mcp.json` *only if IT approves*; add read-only scopes first; pass `--mcp-config` in `run_claude()` extras if needed.
- **Push**: `--allow-push` pushes only `claude/*` branches. Leave it off until you trust the flow.
- **Rollup delivery**: it's a file. If you want it emailed/Slacked, add that yourself via an approved internal channel.

## 8. Common errors & pitfalls
| Problem | Symptom | Fix |
|---|---|---|
| **Auth/token expiry in cron** | exit≠0, "not logged in"/401 in log | Log in interactively on that machine; if your org uses an API key, provide it via a protected env file read by cron/systemd (`EnvironmentFile=`), never in the repo. Check monthly. |
| **PATH in cron** | exit 127 "claude CLI not found" | Set `PATH` in crontab/unit, or `CLAUDE_BIN=/full/path/claude`. Node version managers (nvm) aren't loaded in cron. |
| **Stale lock files** | "repo locked" every night | Runner auto-clears locks whose PID is dead or older than `--stale-lock-hours`; else `rm locks/<repo>.lock`. |
| **Dirty working tree** | task → blocked "dirty working tree" | Runner refuses to touch uncommitted work. Commit/stash, or keep a dedicated clone for the runner (recommended). |
| **Merge conflicts** | branch diverged from main | Branches are cut from local `default_branch`; pull main before nightly runs, keep tasks small, merge quickly. |
| **Runaway usage/cost** | huge logs, many turns | Lower `max_turns`, `--limit`, timeouts; avoid "continually"; watch your org's usage dashboard. |
| **Flaky tests** | reviewer FAILs randomly | List known flakes in task/repo notes; triage agent reruns 2×; fix flakes as their own tasks. |
| **Permission prompts in headless runs** | run stalls/ends with permission denial | Headless runs can't answer prompts: pre-approve needed tools via `--allowedTools`/settings. Avoid blanket "skip permissions" flags on work code. |
| **Context bloat** | worse answers, turn limit hit | Point to files instead of pasting; keep memory docs tight; summarize sim output to disk; split tasks. |
| **Hallucinated success** | "all tests pass" but they don't | Reviewer reruns tests; runner treats missing RESULT line as failed; always spot-check before merging. |
| **Secrets in logs** | tokens in logs/reports | `redact()` masks common patterns but isn't perfect; keep `.env` denied in settings; `logs/` is gitignored; purge logs periodically. |
| **Placeholders left in repos.yaml** | "not a git repo (placeholder?)" | Replace `<REPO_PATH_...>`. |
| **JSON output shape changes** | report shows raw JSON | Adjust parsing in `run_claude()` for your CLI version. |

### ITAR / export control & company policy
- **Check with security before** pointing this at sensitive code, controlled technical data, or classified/CUI networks. Approval for a tool on one repo isn't approval for all.
- No export of controlled data: workers must not send code/data to non-approved endpoints, web tools, or MCP servers. The settings deny web/network commands by default — keep it that way unless approved.
- Use only the model endpoint/tenant your company has approved (e.g. an enterprise or on-prem/GovCloud deployment if required).
- Don't commit reports containing controlled data to non-approved remotes; this master repo inherits the sensitivity of the most sensitive repo it touches.

## 9. Troubleshooting checklist
1. `python3 scripts/run_tasks.py --dry-run` — is the task even eligible (status `queued`, schedule, weekday, already ran today)?
2. `ls locks/` — stale lock?
3. `logs/<date>/<id>.log` — exit code, stderr.
4. Run the same thing by hand from the repo dir: `claude -p "say ok" --output-format json --max-turns 1`.
5. From cron: `env -i PATH=<cron PATH> HOME=$HOME bash -lc 'which claude'`.
6. `git -C <repo> status` — clean? on which branch?
7. `claude --help` — flags changed?
8. Frontmatter valid? (`---` lines, `key: value`, id = filename.)

## 10. Suggested rollout
- **Week 1 — dry run & manual.** Fill CLAUDE.md/repos.yaml, one repo only, `--dry-run` daily, then 2–3 manual `--task` runs you watch. Read every log.
- **Week 2 — nightly analysis-only.** Enable cron for one read-only task (perf-sim deltas). No code-changing tasks. Read the rollup each morning.
- **Week 3 — small code tasks.** Add test triage/fix tasks with reviewer on. Merge only after your own review.
- **Week 4 — expand.** Add repos, weekly tasks, a stronger reviewer model if useful, maybe `--allow-push` for branches so you can open PRs from anywhere.
- **Ongoing.** Monthly: check auth, prune `claude/*` branches and logs, review usage, fold lessons into memory docs.
