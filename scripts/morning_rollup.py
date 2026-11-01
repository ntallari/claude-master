#!/usr/bin/env python3
"""Combine a day's reports (default: yesterday) into reports/rollup-YYYY-MM-DD.md.
Usage: morning_rollup.py [--date YYYY-MM-DD]   (date = the day the reports were written)
"""
import argparse, datetime, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *  # noqa

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=(datetime.date.today() - datetime.timedelta(days=1)).isoformat())
    a = ap.parse_args()
    d = REPORTS / a.date
    files = sorted(d.glob("*.md")) if d.exists() else []
    rows, sections = [], []
    for f in files:
        t = f.read_text()
        res = (re.findall(r"RESULT:\s*(\w+)", t) or ["?"])[-1]
        rev = (re.findall(r"## Review\n\*\*(\w+)\*\*", t) or ["-"])[-1]
        br = (re.findall(r"branch: `([^`]+)`", t) or ["-"])[0]
        summ = re.search(r"## Summary\s*\n(.*?)(\n## |\Z)", t, re.S)
        rows.append(f"| {f.stem} | {res} | {rev} | `{br}` |")
        sections.append(f"### {f.stem}\n{(summ.group(1).strip() if summ else '(no summary)')[:1500]}\n\n[full report]({a.date}/{f.name})\n")
    blocked = [r for r in rows if "BLOCKED" in r or "FAIL" in r]
    queue = []
    for p in sorted(TASKS.glob("*.md")):
        if p.name.startswith("_"): continue
        try: m, _ = read_task(p); queue.append(f"- {m.get('id')}: {m.get('status')} ({m.get('schedule')}, p{m.get('priority')})")
        except Exception: pass
    out = REPORTS / f"rollup-{today()}.md"
    out.write_text(f"# Morning rollup {today()} (runs from {a.date})\n\n"
                   f"{len(files)} task report(s); {len(blocked)} need attention.\n\n"
                   "| task | result | review | branch |\n|---|---|---|---|\n" + "\n".join(rows or ["| (no runs) | | | |"]) +
                   "\n\n## Summaries\n" + ("\n".join(sections) or "_Nothing ran._\n") +
                   "\n## Queue status\n" + "\n".join(queue) + "\n")
    print(f"wrote {out.relative_to(ROOT)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
