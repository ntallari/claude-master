"""Shared helpers for claude-master scripts. Python 3.8+ stdlib; PyYAML used if installed."""
import os, re, subprocess, datetime, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS = ROOT / "tasks"; REPORTS = ROOT / "reports"; LOGS = ROOT / "logs"; LOCKS = ROOT / "locks"

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None

def _strip_comment(line):
    out, q = [], None
    for i, ch in enumerate(line):
        if ch in "'\"" and q is None: q = ch
        elif ch == q: q = None
        elif ch == "#" and q is None and (i == 0 or line[i-1].isspace()): break
        out.append(ch)
    return "".join(out).rstrip()

def _scalar(v):
    v = v.strip()
    if v == "" : return ""
    if v[0] in "'\"" and v[-1] == v[0]: return v[1:-1]
    if v.startswith("[") and v.endswith("]"):
        return [_scalar(x) for x in v[1:-1].split(",") if x.strip()]
    if v.lower() in ("true", "yes"): return True
    if v.lower() in ("false", "no"): return False
    if re.fullmatch(r"-?\d+", v): return int(v)
    return v

def _mini_yaml(text):
    """Tiny fallback YAML subset parser: nested maps, '- item' lists, inline [a, b], scalars."""
    lines = [(len(l) - len(l.lstrip()), l.strip()) for l in
             (_strip_comment(x) for x in text.splitlines()) if l.strip() and l.strip() != "---"]
    def parse(i, indent):
        if i < len(lines) and lines[i][1].startswith("- "):
            res = []
            while i < len(lines) and lines[i][0] == indent and lines[i][1].startswith("- "):
                res.append(_scalar(lines[i][1][2:])); i += 1
            return res, i
        res = {}
        while i < len(lines) and lines[i][0] == indent:
            key, _, val = lines[i][1].partition(":")
            i += 1
            if val.strip() == "" and i < len(lines) and lines[i][0] > indent:
                res[key.strip()], i = parse(i, lines[i][0])
            elif val.strip() == "" and i < len(lines) and lines[i][0] == indent and lines[i][1].startswith("- "):
                res[key.strip()], i = parse(i, indent)
            else:
                res[key.strip()] = _scalar(val)
        return res, i
    return parse(0, lines[0][0])[0] if lines else {}

def load_yaml(text):
    return (yaml.safe_load(text) if yaml else _mini_yaml(text)) or {}

def load_registry():
    data = load_yaml((ROOT / "repos.yaml").read_text())
    return data.get("defaults", {}) or {}, data.get("repos", {}) or {}

def read_task(path):
    text = Path(path).read_text()
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m: raise ValueError(f"{path}: missing YAML frontmatter")
    return load_yaml(m.group(1)), m.group(2)

def set_fields(path, **fields):
    """Update frontmatter keys in place, preserving everything else (comments included)."""
    text = Path(path).read_text()
    head, sep, body = text[4:].partition("\n---")
    for k, v in fields.items():
        pat = re.compile(rf"^({re.escape(k)}:\s*)([^#\n]*?)(\s*#.*)?$", re.M)
        if pat.search(head): head = pat.sub(lambda m: f"{m.group(1)}{v}{m.group(3) or ''}", head, count=1)
        else: head += f"\n{k}: {v}"
    Path(path).write_text("---\n" + head + sep + body)

def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and r.returncode: raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout.strip()

def today(): return datetime.date.today().isoformat()

_SECRET = re.compile(r"(?i)(api[_-]?key|token|secret|password|bearer)(\s*[:=]\s*|\s+)([^\s'\"]{8,})")
def redact(text): return _SECRET.sub(lambda m: m.group(1) + m.group(2) + "***REDACTED***", text)

def run_claude(prompt, cwd, model, max_turns, timeout_min, allowed_tools=None, log_path=None, extra=None):
    """Run headless `claude -p`. Returns (exit_code, result_text, raw). Verify flags with `claude --help`."""
    cmd = [os.environ.get("CLAUDE_BIN", "claude"), "-p", prompt, "--output-format", "json",
           "--max-turns", str(max_turns)]
    if model: cmd += ["--model", str(model)]
    if allowed_tools: cmd += ["--allowedTools", allowed_tools]
    cmd += extra or []
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=int(timeout_min) * 60)
        code, raw, err = r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired as e:
        code, raw, err = 124, (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or ""), f"TIMEOUT after {timeout_min} min"
    except FileNotFoundError:
        code, raw, err = 127, "", "claude CLI not found on PATH (cron PATH? set CLAUDE_BIN)"
    result = raw
    try:
        j = json.loads(raw); result = j.get("result", raw)
        if j.get("is_error"): code = code or 1
    except (json.JSONDecodeError, AttributeError):
        pass
    if log_path:
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        Path(log_path).write_text(redact(f"$ {' '.join(cmd[:2])} <prompt> {' '.join(cmd[3:])}\nexit={code}\n--- stdout ---\n{raw}\n--- stderr ---\n{err}\n"))
    return code, redact(result or ""), err
