---
id: <short-kebab-id>            # unique; also the filename without .md
repo: <repo key from repos.yaml>
status: queued                  # queued | running | review | done | failed | blocked
priority: 2                     # 1 = highest
schedule: once                  # once | nightly | weekly  (recurring tasks return to queued after done)
weekday: mon                    # only for weekly
max_turns: 30
timeout: 45                     # minutes
model: sonnet                   # optional override
agent: ""                       # optional subagent hint, e.g. sim-analyst
last_run: ""                    # filled by runner
---
# Goal
<What should be accomplished and why.>

# Context / pointers
- <Files, configs, prior reports, tickets (by ID only, no external access)>

# Steps (suggested)
1. ...

# Definition of done
- [ ] <Concrete, checkable outcome>
- [ ] Tests pass (`<test_command>`) or failures explained
- [ ] Report written with RESULT line

# Out of scope
- <Things not to touch>
