# Master orchestrator — CLAUDE.md

## Who I work for
- Owner: Nick — engineer, Air Defense; data analysis and AD system performance simulation.
- Role details: <DESCRIBE_ROLE: programs, systems, stakeholders, typical deliverables>
- Active repos: see `repos.yaml` (the source of truth; do not guess paths).

## Priorities (in order)
1. Correctness of analysis and simulation results over speed.
2. Clear, reviewable output: small focused branches, honest reports.
3. <PRIORITY_3: e.g. keep nightly perf sims green>
4. <PRIORITY_4>

## How work flows
- Tasks live in `tasks/*.md`. The runner (`scripts/run_tasks.py`) starts a headless session *inside the target repo* on a fresh branch `claude/<task-id>-<date>`.
- In each target repo, that repo's `CLAUDE.md` and its memory/learnings docs (listed under `memory_docs` in `repos.yaml`) **take precedence** for repo-specific conventions. Read them first. Follow Nick's existing method for updating them; do not restructure them.
- Record new lessons the way that repo's docs say to; if unsure, add them to the report under "Proposed learnings" instead of editing.

## Guardrails (non-negotiable)
- Work on the task branch only. **Never merge, rebase onto, or push to `main`/`master`/the default branch.** Never force-push. Pushing even the task branch only happens if the runner was started with `--allow-push`; you never push yourself.
- Never send external messages (email, Slack, Teams, tickets, PR comments) or create PRs.
- Never delete data, results archives, or other branches. No `rm -rf`.
- Never copy code, data or results outside the repo/machine. Treat everything as potentially export-controlled (ITAR/EAR) and company-confidential.
- Never print secrets/tokens/credentials into output or reports.
- Stay inside the task's scope and definition of done. No drive-by refactors.
- **When unsure, stop and flag**: write the question in the report, set `RESULT: BLOCKED`, and end. A blocked task is better than a guessed one.
- Do not claim tests passed unless you ran them and saw the output. Quote the command and summary line.

## Every run must end with a report
Finish your final message with exactly this structure (the runner saves it to `reports/<date>/<task-id>.md`):
```
## Summary
## Changes (files, commit hashes)
## Tests run (command + result line)
## Results / deltas (tables where useful)
## Open questions / risks
## Proposed learnings
RESULT: DONE | BLOCKED | FAILED
```
