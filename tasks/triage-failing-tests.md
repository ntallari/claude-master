---
id: triage-failing-tests
repo: flight-data-analysis
status: queued
priority: 2
schedule: once
max_turns: 30
timeout: 45
model: sonnet
agent: test-triage
last_run: ""
---
# Goal
Triage currently failing tests: classify each failure and fix the clear-cut ones on the task branch.

# Context / pointers
- Test command: `pytest -q` (see repos.yaml)
- Known flaky tests: `<LIST_OR_NONE>`

# Steps (suggested)
1. Run the suite; capture failures.
2. Classify each: real bug / test bug / environment / flaky (rerun up to 2x to check).
3. Fix only obvious, local failures with a minimal commit each. Leave the rest documented.

# Definition of done
- [ ] Table: test | category | root cause | action (fixed in <hash> / needs Nick)
- [ ] Suite re-run after fixes; result line quoted
- [ ] No test deleted or skipped to make it pass

# Out of scope
- Refactors, dependency upgrades.
