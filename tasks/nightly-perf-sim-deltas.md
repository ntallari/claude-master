---
id: nightly-perf-sim-deltas
repo: ad-perf-sim
status: queued
priority: 1
schedule: nightly
max_turns: 25
timeout: 60
model: sonnet
agent: sim-analyst
last_run: ""
---
# Goal
Rerun the baseline performance simulation on the current default branch and summarize deltas versus the last accepted baseline.

# Context / pointers
- Sim command: see `sim_command` in repos.yaml for ad-perf-sim.
- Last accepted baseline: `<BASELINE_RESULTS_PATH e.g. results/accepted/latest/>`
- Tolerances: `<TOLERANCE_FILE e.g. configs/tolerances.yaml>`

# Steps (suggested)
1. Run the reduced nightly config of the sim.
2. Compare key metrics (Pk, time-to-engage, track latency, leakers) against baseline.
3. Flag anything outside tolerance and list commits since the baseline that might explain it (`git log`).

# Definition of done
- [ ] Sim completed (or failure captured with the error tail)
- [ ] Delta table: metric | baseline | new | delta | within tolerance?
- [ ] Out-of-tolerance items listed with candidate commits
- [ ] No source changes committed (analysis only); results summary may be committed under `reports/` in the repo only if that repo's CLAUDE.md allows

# Out of scope
- Changing model parameters or tolerances.
